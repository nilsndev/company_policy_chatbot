"""Hybrid vector + graph retrieval (M4, PRD §6.3, §6.5).

Pipeline: pgvector similarity search scoped to the asking employee's
department/role (SQL-level filter, layer 1) -> Neo4j RBAC graph filter on the
survivors (layer 2, independent of layer 1 — see `allowed_policy_ids`) ->
supersedes resolution (swap a stale policy's chunk for its current version,
dropping it if no visible current version exists) -> REFERENCES enrichment
(a small number of supplementary chunks from directly related policies).

Neither isolation layer is trusted alone (`graph` skill, CLAUDE.md loop 4):
a chunk only reaches the LLM if both layer 1 (SQL) and layer 2 (graph) allow
its policy.
"""

from dataclasses import dataclass

from neo4j import AsyncDriver
from pgvector import Vector
from pgvector.psycopg import register_vector_async
from psycopg_pool import AsyncConnectionPool

from app.core.config import Settings
from app.services import db
from app.services import neo4j as neo4j_service
from app.services.embeddings import EmbeddingClient

OVERFETCH = 4
RELATED_LIMIT = 2


@dataclass
class RetrievedChunk:
    policy_id: str
    title: str
    version: int
    section: str | None
    content: str
    supplementary: bool = False  # pulled in via REFERENCES, not a direct vector match


async def retrieve_chunks(
    pool: AsyncConnectionPool,
    driver: AsyncDriver,
    settings: Settings,
    employee_id: str,
    query: str,
    k: int = 6,
    use_graph: bool = True,
) -> list[RetrievedChunk]:
    """`use_graph=False` is the M6 eval-only baseline (PRD G4): plain top-k
    vector similarity with none of the scoping/supersedes/references steps
    below, i.e. the M2 pipeline before the M4 graph layer existed. Never used
    by `app/api/chat.py` — production requests always get the full pipeline.
    """
    embedder = EmbeddingClient(settings)
    [query_embedding] = await embedder.embed([query])

    if not use_graph:
        return await _vector_search_unscoped(pool, query_embedding, limit=k)

    profile = await db.get_profile(pool, employee_id)
    department = profile["department"] if profile else None
    role = profile["role"] if profile else None

    candidates = await _vector_search(pool, query_embedding, department, role, limit=k * OVERFETCH)
    if not candidates:
        return []

    allowed_ids = set(
        await neo4j_service.allowed_policy_ids(driver, employee_id, list({c.policy_id for c in candidates}))
    )
    candidates = [c for c in candidates if c.policy_id in allowed_ids]

    primary = await _resolve_superseded(driver, pool, candidates, query_embedding, department, role)
    primary = primary[:k]
    # Recomputed from the truncated list, not the pre-slice one: a policy
    # that _resolve_superseded matched but that lost out to the `k` cutoff
    # is not actually in context, so REFERENCES enrichment must not treat it
    # as "already included" (caught live: a legitimately-missing reference
    # was silently skipped because it happened to also be a truncated primary match).
    seen_policy_ids = {c.policy_id for c in primary}

    supplementary = await _enrich_with_references(
        pool, driver, employee_id, primary, query_embedding, department, role, seen_policy_ids
    )
    return primary + supplementary


async def _vector_search(
    pool: AsyncConnectionPool,
    query_embedding: list[float],
    department: str | None,
    role: str | None,
    limit: int,
) -> list[RetrievedChunk]:
    async with pool.connection() as conn:
        await register_vector_async(conn)
        async with conn.cursor() as cur:
            await cur.execute(
                """
                select p.id, p.title, p.version, c.section, c.content
                from policy_chunks c
                join policies p on p.id = c.policy_id
                where p.department is null or p.department = %s or %s = 'compliance_officer'
                order by c.embedding <=> %s
                limit %s
                """,
                (department, role, Vector(query_embedding), limit),
            )
            rows = await cur.fetchall()
    return [
        RetrievedChunk(policy_id=str(r[0]), title=r[1], version=r[2], section=r[3], content=r[4])
        for r in rows
    ]


async def _vector_search_unscoped(
    pool: AsyncConnectionPool,
    query_embedding: list[float],
    limit: int,
) -> list[RetrievedChunk]:
    """Eval-only baseline: no department/role WHERE clause at all — the "flat
    vector index" PRD §2 describes, unaware of RBAC or policy relationships."""
    async with pool.connection() as conn:
        await register_vector_async(conn)
        async with conn.cursor() as cur:
            await cur.execute(
                """
                select p.id, p.title, p.version, c.section, c.content
                from policy_chunks c
                join policies p on p.id = c.policy_id
                order by c.embedding <=> %s
                limit %s
                """,
                (Vector(query_embedding), limit),
            )
            rows = await cur.fetchall()
    return [
        RetrievedChunk(policy_id=str(r[0]), title=r[1], version=r[2], section=r[3], content=r[4])
        for r in rows
    ]


async def _department_scoped_chunk(
    pool: AsyncConnectionPool,
    policy_id: str,
    query_embedding: list[float],
    department: str | None,
    role: str | None,
) -> RetrievedChunk | None:
    """Best-matching chunk for one specific policy, re-checked against the SQL
    department/role filter — a resolved supersedes target or a REFERENCES
    neighbor can belong to a different department than the original match."""
    async with pool.connection() as conn:
        await register_vector_async(conn)
        async with conn.cursor() as cur:
            await cur.execute(
                """
                select p.id, p.title, p.version, c.section, c.content
                from policy_chunks c
                join policies p on p.id = c.policy_id
                where p.id = %s
                  and (p.department is null or p.department = %s or %s = 'compliance_officer')
                order by c.embedding <=> %s
                limit 1
                """,
                (policy_id, department, role, Vector(query_embedding)),
            )
            row = await cur.fetchone()
    if not row:
        return None
    return RetrievedChunk(policy_id=str(row[0]), title=row[1], version=row[2], section=row[3], content=row[4])


async def _resolve_superseded(
    driver: AsyncDriver,
    pool: AsyncConnectionPool,
    candidates: list[RetrievedChunk],
    query_embedding: list[float],
    department: str | None,
    role: str | None,
) -> list[RetrievedChunk]:
    """Swap any chunk belonging to a superseded policy for its current
    version (PRD §6.3): don't let the model answer from a stale policy.

    Only drops/substitutes genuinely stale chunks — it does NOT collapse
    multiple chunks that already belong to the same non-superseded policy.
    An earlier version deduped to one chunk per policy outright, which
    silently dropped a second relevant section of the *current* policy
    whenever that policy also happened to be the supersedes target (caught
    live: a Remote Work Policy v2 query returned only its domestic-approval
    section because the international-remote-work section, from the same
    v2 policy, got deduped away as a "duplicate")."""
    candidate_policy_ids = {c.policy_id for c in candidates}
    current_id_cache: dict[str, str] = {}
    resolved: list[RetrievedChunk] = []
    substituted: set[str] = set()

    for chunk in candidates:
        if chunk.policy_id not in current_id_cache:
            current_id_cache[chunk.policy_id] = await neo4j_service.resolve_current_version(driver, chunk.policy_id)
        current_id = current_id_cache[chunk.policy_id]

        if current_id == chunk.policy_id:
            resolved.append(chunk)
            continue

        # Stale chunk: its current version either already has its own chunk
        # among the candidates (picked up when that chunk's turn comes, via
        # the branch above) or needs a one-time substitution.
        if current_id in candidate_policy_ids or current_id in substituted:
            continue
        substituted.add(current_id)
        replacement = await _department_scoped_chunk(pool, current_id, query_embedding, department, role)
        if replacement:
            resolved.append(replacement)
        # else: superseded policy dropped — no visible current version to
        # substitute ("where possible", PRD §6.3), rather than citing stale text.
    return resolved


async def _enrich_with_references(
    pool: AsyncConnectionPool,
    driver: AsyncDriver,
    employee_id: str,
    primary: list[RetrievedChunk],
    query_embedding: list[float],
    department: str | None,
    role: str | None,
    seen_policy_ids: set[str],
) -> list[RetrievedChunk]:
    """Pull in directly REFERENCES-linked policies as supplementary context,
    capped (`RELATED_LIMIT`) — enrichment, not a second unbounded retrieval
    (`graph` skill)."""
    supplementary: list[RetrievedChunk] = []
    for chunk in primary:
        if len(supplementary) >= RELATED_LIMIT:
            break
        related_ids = [
            rid
            for rid in await neo4j_service.related_policy_ids(driver, chunk.policy_id, limit=RELATED_LIMIT)
            if rid not in seen_policy_ids
        ]
        if not related_ids:
            continue
        allowed = set(await neo4j_service.allowed_policy_ids(driver, employee_id, related_ids))
        for related_id in related_ids:
            if len(supplementary) >= RELATED_LIMIT:
                break
            if related_id not in allowed:
                continue
            related_chunk = await _department_scoped_chunk(pool, related_id, query_embedding, department, role)
            if related_chunk:
                related_chunk.supplementary = True
                supplementary.append(related_chunk)
                seen_policy_ids.add(related_id)
    return supplementary
