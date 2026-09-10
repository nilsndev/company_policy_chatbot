-- Rolling conversation summary (M5, PRD §6.4, `conversation-memory` skill):
-- once the raw history window exceeds a token budget, older turns get
-- folded into `summary` and `summary_through` marks the created_at of the
-- newest message already folded in, so the working window is always
-- "messages after summary_through" (or all messages if null).
alter table conversations add column if not exists summary text;
alter table conversations add column if not exists summary_through timestamptz;
