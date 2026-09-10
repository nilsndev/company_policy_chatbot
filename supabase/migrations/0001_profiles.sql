-- Profiles: department + role per user, mirrors the Employee node in Neo4j (see `graph` skill).
create extension if not exists pgcrypto;

create table if not exists profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    department text check (
        department in (
            'Clinical',
            'IT & Security',
            'HR',
            'Compliance & Risk',
            'Finance',
            'Facilities & Operations'
        )
    ),
    role text check (role in ('staff', 'manager', 'director', 'compliance_officer')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table profiles enable row level security;

drop policy if exists profiles_select_own on profiles;
create policy profiles_select_own on profiles
    for select using (auth.uid() = id);

drop policy if exists profiles_insert_own on profiles;
create policy profiles_insert_own on profiles
    for insert with check (auth.uid() = id);

drop policy if exists profiles_update_own on profiles;
create policy profiles_update_own on profiles
    for update using (auth.uid() = id);
