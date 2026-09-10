-- Persist the citations shown alongside a grounded assistant reply so they
-- survive a conversation history reload (M2 loop 2: vector retrieval + citations).
alter table messages add column if not exists citations jsonb not null default '[]'::jsonb;
