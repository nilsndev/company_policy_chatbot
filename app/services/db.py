from pgvector import Vector
from pgvector.psycopg import register_vector_async
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from app.core.config import Settings
from app.services.chunking import Chunk


def create_pool(settings: Settings) -> AsyncConnectionPool:
    return AsyncConnectionPool(conninfo=settings.database_url, open=False, min_size=1, max_size=5)


async def get_profile(pool: AsyncConnectionPool, user_id: str) -> dict | None:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "select department, role from profiles where id = %s", (user_id,)
        )
        row = await cur.fetchone()
        return {"department": row[0], "role": row[1]} if row else None


async def upsert_profile(pool: AsyncConnectionPool, user_id: str, department: str, role: str) -> dict:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            insert into profiles (id, department, role, updated_at)
            values (%s, %s, %s, now())
            on conflict (id) do update set department = excluded.department, role = excluded.role, updated_at = now()
            returning department, role
            """,
            (user_id, department, role),
        )
        row = await cur.fetchone()
        await conn.commit()
        return {"department": row[0], "role": row[1]}


async def list_conversations(pool: AsyncConnectionPool, user_id: str) -> list[dict]:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            select id, title, created_at, updated_at from conversations
            where user_id = %s order by updated_at desc
            """,
            (user_id,),
        )
        rows = await cur.fetchall()
        return [
            {"id": str(r[0]), "title": r[1], "created_at": r[2].isoformat(), "updated_at": r[3].isoformat()}
            for r in rows
        ]


async def get_conversation(pool: AsyncConnectionPool, user_id: str, conversation_id: str) -> dict | None:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "select id, summary, summary_through from conversations where id = %s and user_id = %s",
            (conversation_id, user_id),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "id": str(row[0]),
            "summary": row[1],
            "summary_through": row[2].isoformat() if row[2] else None,
        }


async def update_conversation_summary(
    pool: AsyncConnectionPool, conversation_id: str, summary: str, summary_through: str
) -> None:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "update conversations set summary = %s, summary_through = %s where id = %s",
            (summary, summary_through, conversation_id),
        )
        await conn.commit()


async def list_messages(pool: AsyncConnectionPool, conversation_id: str) -> list[dict]:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            select id, role, content, created_at, citations from messages
            where conversation_id = %s order by created_at asc
            """,
            (conversation_id,),
        )
        rows = await cur.fetchall()
        return [
            {
                "id": str(r[0]),
                "role": r[1],
                "content": r[2],
                "created_at": r[3].isoformat(),
                "citations": r[4],
            }
            for r in rows
        ]


async def create_conversation(pool: AsyncConnectionPool, user_id: str, title: str) -> str:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "insert into conversations (user_id, title) values (%s, %s) returning id",
            (user_id, title),
        )
        row = await cur.fetchone()
        await conn.commit()
        return str(row[0])


async def append_message(
    pool: AsyncConnectionPool,
    conversation_id: str,
    role: str,
    content: str,
    citations: list[dict] | None = None,
) -> None:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "insert into messages (conversation_id, role, content, citations) values (%s, %s, %s, %s)",
            (conversation_id, role, content, Jsonb(citations or [])),
        )
        await cur.execute(
            "update conversations set updated_at = now() where id = %s", (conversation_id,)
        )
        await conn.commit()


async def list_policies(pool: AsyncConnectionPool) -> list[dict]:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            select p.id, p.slug, p.title, p.department, p.version,
                   coalesce(
                       (select j.status from ingestion_jobs j
                        where j.policy_id = p.id order by j.created_at desc limit 1),
                       'queued'
                   ) as status
            from policies p
            order by p.title, p.version
            """
        )
        rows = await cur.fetchall()
        return [
            {
                "id": str(r[0]),
                "slug": r[1],
                "title": r[2],
                "department": r[3],
                "version": r[4],
                "status": r[5],
            }
            for r in rows
        ]


async def next_queued_ingestion_job(pool: AsyncConnectionPool) -> str | None:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "select id from ingestion_jobs where status = 'queued' order by created_at limit 1"
        )
        row = await cur.fetchone()
        return str(row[0]) if row else None


async def claim_ingestion_job(pool: AsyncConnectionPool, job_id: str) -> str | None:
    """Atomically flip a queued job to processing; returns its policy_id, or None
    if it was already claimed (or isn't queued)."""
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            update ingestion_jobs set status = 'processing', updated_at = now()
            where id = %s and status = 'queued'
            returning policy_id
            """,
            (job_id,),
        )
        row = await cur.fetchone()
        await conn.commit()
        return str(row[0]) if row else None


async def get_policy_source(pool: AsyncConnectionPool, policy_id: str) -> dict | None:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "select storage_path, content_hash from policies where id = %s", (policy_id,)
        )
        row = await cur.fetchone()
        return {"storage_path": row[0], "content_hash": row[1]} if row else None


async def get_latest_chunk_hash(pool: AsyncConnectionPool, policy_id: str) -> str | None:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "select content_hash from policy_chunks where policy_id = %s limit 1", (policy_id,)
        )
        row = await cur.fetchone()
        return row[0] if row else None


async def replace_policy_chunks(
    pool: AsyncConnectionPool,
    policy_id: str,
    chunks: list[Chunk],
    embeddings: list[list[float]],
    embedding_model: str,
    content_hash: str,
) -> None:
    async with pool.connection() as conn:
        await register_vector_async(conn)
        async with conn.cursor() as cur:
            await cur.execute("delete from policy_chunks where policy_id = %s", (policy_id,))
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                await cur.execute(
                    """
                    insert into policy_chunks
                        (policy_id, chunk_index, section, content, embedding, embedding_model, content_hash)
                    values (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        policy_id,
                        chunk.chunk_index,
                        chunk.section,
                        chunk.content,
                        Vector(embedding),
                        embedding_model,
                        content_hash,
                    ),
                )
        await conn.commit()


async def mark_ingestion_job(
    pool: AsyncConnectionPool, job_id: str, status: str, error: str | None = None
) -> None:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "update ingestion_jobs set status = %s, error = %s, updated_at = now() where id = %s",
            (status, error, job_id),
        )
        await conn.commit()
