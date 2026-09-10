-- Policy corpus + vector chunks + ingestion job tracking (M2, vector-only).
-- No RBAC/graph filtering yet: any authenticated user can read any policy/chunk.
-- Department/role scoping via the Neo4j RBAC graph lands in M4 (see PRD §6.3, §6.5).
create extension if not exists vector;

create table if not exists policies (
    id uuid primary key default gen_random_uuid(),
    slug text unique not null,
    title text not null,
    department text check (
        department in (
            'Clinical',
            'IT & Security',
            'HR',
            'Compliance & Risk',
            'Finance',
            'Facilities & Operations'
        )
    ), -- null = company-wide
    version int not null default 1,
    supersedes_policy_id uuid references policies (id),
    storage_path text not null,
    content_hash text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Embedding dimension matches the configured Ollama embed model (nomic-embed-text,
-- 768 dims). Changing the embed model requires a new migration + reindex (see `rag` skill).
create table if not exists policy_chunks (
    id uuid primary key default gen_random_uuid(),
    policy_id uuid not null references policies (id) on delete cascade,
    chunk_index int not null,
    section text,
    content text not null,
    embedding vector(768),
    embedding_model text not null,
    content_hash text not null,
    created_at timestamptz not null default now(),
    unique (policy_id, chunk_index)
);

create index if not exists policy_chunks_embedding_idx on policy_chunks
    using hnsw (embedding vector_cosine_ops);

create table if not exists ingestion_jobs (
    id uuid primary key default gen_random_uuid(),
    policy_id uuid not null references policies (id) on delete cascade,
    status text not null check (status in ('queued', 'processing', 'ready', 'failed')),
    error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists ingestion_jobs_policy_id_idx on ingestion_jobs (policy_id, created_at desc);
create index if not exists ingestion_jobs_status_idx on ingestion_jobs (status, created_at);

alter table policies enable row level security;
alter table policy_chunks enable row level security;
alter table ingestion_jobs enable row level security;

-- Any authenticated employee can read policy content today (no department/role
-- scoping yet — that's the Neo4j RBAC graph, M4). Writes go through service_role
-- only (worker + seed script), so no insert/update policy for authenticated users.
drop policy if exists policies_read_authenticated on policies;
create policy policies_read_authenticated on policies
    for select using (auth.uid() is not null);

drop policy if exists policy_chunks_read_authenticated on policy_chunks;
create policy policy_chunks_read_authenticated on policy_chunks
    for select using (auth.uid() is not null);

drop policy if exists ingestion_jobs_read_authenticated on ingestion_jobs;
create policy ingestion_jobs_read_authenticated on ingestion_jobs
    for select using (auth.uid() is not null);
