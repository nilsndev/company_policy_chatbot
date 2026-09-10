-- Chat history: no RAG/citation columns yet (M1 loop 1, vector retrieval lands in M2).
create table if not exists conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    title text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists conversations_user_id_idx on conversations (user_id, updated_at desc);

create table if not exists messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references conversations (id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    created_at timestamptz not null default now()
);

create index if not exists messages_conversation_id_idx on messages (conversation_id, created_at);

alter table conversations enable row level security;
alter table messages enable row level security;

drop policy if exists conversations_owner on conversations;
create policy conversations_owner on conversations
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists messages_owner on messages;
create policy messages_owner on messages
    for all using (
        exists (
            select 1 from conversations c
            where c.id = messages.conversation_id and c.user_id = auth.uid()
        )
    ) with check (
        exists (
            select 1 from conversations c
            where c.id = messages.conversation_id and c.user_id = auth.uid()
        )
    );
