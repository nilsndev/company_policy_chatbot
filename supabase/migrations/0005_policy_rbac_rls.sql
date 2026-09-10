-- Department/role RBAC on policy rows (M4, PRD §6.5) — mirrors the scoping
-- now enforced in app/services/retrieval.py and the Neo4j RBAC graph
-- (app/services/neo4j.py allowed_policy_ids).
--
-- CAVEAT: the FastAPI backend connects via the Supabase session-pooler
-- `postgres.<project-ref>` role (see README "Local development"), which is
-- the table owner and therefore bypasses RLS the same way any Postgres
-- superuser/owner does (`supabase` skill: "Service role bypasses RLS: always
-- add user_id filters in server queries too"). So these policies do not by
-- themselves restrict the backend's own queries today — that enforcement is
-- the explicit department/role WHERE clause in retrieval.py (layer 1) plus
-- the Neo4j graph traversal (layer 2). This migration is still worth having:
-- it is what actually protects these rows if anything ever queries them
-- directly via the anon/authenticated PostgREST role (a future admin UI,
-- supabase-js from the frontend, etc.) instead of through the API.
drop policy if exists policies_read_authenticated on policies;
create policy policies_read_scoped on policies
    for select using (
        department is null
        or department = (select department from profiles where id = auth.uid())
        or (select role from profiles where id = auth.uid()) = 'compliance_officer'
    );

drop policy if exists policy_chunks_read_authenticated on policy_chunks;
create policy policy_chunks_read_scoped on policy_chunks
    for select using (
        exists (
            select 1 from policies p
            where p.id = policy_chunks.policy_id
              and (
                  p.department is null
                  or p.department = (select department from profiles where id = auth.uid())
                  or (select role from profiles where id = auth.uid()) = 'compliance_officer'
              )
        )
    );

-- ingestion_jobs stays authenticated-only (unchanged): job status has no
-- department scoping requirement (PRD §6.2) and isn't part of the chat
-- retrieval leak vector this migration addresses.
