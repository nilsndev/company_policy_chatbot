"""Neo4j graph service: RBAC graph (Employee/Department/Role) and GraphRAG
relationships between policies (SUPERSEDES/REFERENCES) — see `graph` skill.

Policy node ids mirror Postgres `policies.id`; this module never stores chunk
text, only ids that join back to Postgres.
"""

import logging

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.core.config import Settings

logger = logging.getLogger(__name__)

COMPANY_WIDE = "Company-Wide"


def create_driver(settings: Settings) -> AsyncDriver:
    return AsyncGraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))


async def check_neo4j(settings: Settings) -> dict:
    result = {"reachable": False}
    if not (settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password):
        return result

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        connection_timeout=3.0,
    )
    try:
        await driver.verify_connectivity()
        result["reachable"] = True
    except Exception as exc:
        logger.warning("neo4j readiness check failed: %s: %s", type(exc).__name__, exc)
    finally:
        await driver.close()
    return result


async def upsert_employee(driver: AsyncDriver, employee_id: str, department: str, role: str) -> None:
    """RBAC graph write (PRD §6.1): (Employee)-[:MEMBER_OF]->(Department),
    (Employee)-[:HAS_ROLE]->(Role). Re-runnable on profile changes — drops the
    employee's prior department/role edges first so a change doesn't leave a
    stale grant behind."""
    async with driver.session() as session:
        await session.run(
            """
            MERGE (e:Employee {id: $employeeId})
            WITH e
            OPTIONAL MATCH (e)-[m:MEMBER_OF]->(:Department)
            DELETE m
            WITH e
            OPTIONAL MATCH (e)-[h:HAS_ROLE]->(:Role)
            DELETE h
            WITH e
            MERGE (d:Department {name: $department})
            MERGE (r:Role {name: $role})
            MERGE (e)-[:MEMBER_OF]->(d)
            MERGE (e)-[:HAS_ROLE]->(r)
            """,
            employeeId=employee_id,
            department=department,
            role=role,
        )


async def upsert_policy(driver: AsyncDriver, policy_id: str, title: str, version: int, department: str | None) -> None:
    """Policy node + APPLIES_TO edge. `department=None` means company-wide.
    Re-runnable — drops the policy's prior APPLIES_TO edge first so re-seeding
    after a corpus edit doesn't leave a stale department link behind."""
    async with driver.session() as session:
        await session.run(
            """
            MERGE (p:Policy {id: $policyId})
            SET p.title = $title, p.version = $version
            WITH p
            OPTIONAL MATCH (p)-[a:APPLIES_TO]->(:Department)
            DELETE a
            WITH p
            MERGE (d:Department {name: $department})
            MERGE (p)-[:APPLIES_TO]->(d)
            """,
            policyId=policy_id,
            title=title,
            version=version,
            department=department or COMPANY_WIDE,
        )


async def link_supersedes(driver: AsyncDriver, policy_id: str, supersedes_policy_id: str) -> None:
    async with driver.session() as session:
        await session.run(
            """
            MATCH (new:Policy {id: $policyId}), (old:Policy {id: $supersedesId})
            MERGE (new)-[:SUPERSEDES]->(old)
            """,
            policyId=policy_id,
            supersedesId=supersedes_policy_id,
        )


async def link_references(driver: AsyncDriver, policy_id: str, referenced_policy_id: str) -> None:
    async with driver.session() as session:
        await session.run(
            """
            MATCH (p:Policy {id: $policyId}), (ref:Policy {id: $referencedId})
            MERGE (p)-[:REFERENCES]->(ref)
            """,
            policyId=policy_id,
            referencedId=referenced_policy_id,
        )


async def allowed_policy_ids(driver: AsyncDriver, employee_id: str, candidate_ids: list[str]) -> list[str]:
    """RBAC filter (retrieval step 3, PRD §6.3): which of `candidate_ids` this
    employee may see, via department membership (or company-wide policies) or
    the cross-cutting `compliance_officer` role (PRD §6.1). Server-side only —
    never trust a client-supplied department/role; this is the second isolation
    layer alongside the SQL-level department filter in `retrieval.py` (`graph`
    skill). The employee/department/role lookups are `OPTIONAL MATCH`, not
    `MATCH`: a plain `MATCH (e:Employee {id: ...})` would return zero rows
    (denying even company-wide policies) whenever the employee has no graph
    node yet — e.g. profile saved but the best-effort Neo4j sync in
    `app/api/profile.py` hasn't landed. Department/role-scoped policies still
    correctly deny in that case since `d`/`r` are null."""
    if not candidate_ids:
        return []
    async with driver.session() as session:
        result = await session.run(
            """
            OPTIONAL MATCH (e:Employee {id: $employeeId})
            OPTIONAL MATCH (e)-[:MEMBER_OF]->(d:Department)
            OPTIONAL MATCH (e)-[:HAS_ROLE]->(r:Role)
            WITH d, r
            MATCH (p:Policy)-[:APPLIES_TO]->(dept)
            WHERE p.id IN $candidateIds
              AND (dept.name = $companyWide OR dept = d OR r.name = 'compliance_officer')
            RETURN DISTINCT p.id AS id
            """,
            employeeId=employee_id,
            candidateIds=candidate_ids,
            companyWide=COMPANY_WIDE,
        )
        return [record["id"] async for record in result]


async def resolve_current_version(driver: AsyncDriver, policy_id: str) -> str:
    """If `policy_id` was superseded (directly or transitively), return the
    current (non-superseded) version's id; otherwise return `policy_id` as-is."""
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Policy {id: $policyId})
            OPTIONAL MATCH path = (newest:Policy)-[:SUPERSEDES*]->(p)
            WHERE NOT (:Policy)-[:SUPERSEDES]->(newest)
            RETURN coalesce(newest.id, p.id) AS id
            ORDER BY length(path) DESC
            LIMIT 1
            """,
            policyId=policy_id,
        )
        record = await result.single()
        return record["id"] if record else policy_id


async def related_policy_ids(driver: AsyncDriver, policy_id: str, limit: int = 3) -> list[str]:
    """Directly `REFERENCES`-linked policies, capped — supplementary enrichment
    context only, not a second unbounded retrieval (`graph` skill)."""
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Policy {id: $policyId})-[:REFERENCES]->(ref:Policy)
            RETURN ref.id AS id
            LIMIT $limit
            """,
            policyId=policy_id,
            limit=limit,
        )
        return [record["id"] async for record in result]
