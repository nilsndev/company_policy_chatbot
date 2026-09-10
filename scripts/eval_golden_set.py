"""M6 golden-set eval (PRD §6.6, G4): runs every case in `eval/golden_set.json`
through the retrieval pipeline twice — `use_graph=False` (vector-only baseline,
the M2 pipeline before the graph layer existed) and `use_graph=True` (the
current M4 hybrid pipeline) — and reports the delta, per the `rag-evaluation`
skill's "retrieval recall before LLM-as-judge" guidance.

Prerequisites: the 4 eval persona accounts must already exist (signed up
through the real app so their `profiles` row satisfies the `auth.users` FK —
see PROGRESS.md M6) with the emails in `eval/golden_set.json`'s `personas`.

For a small representative subset (one case per persona), also generates a
real LLM answer from each mode's context (reusing `app/api/chat.py`'s prompt
plumbing) for a qualitative faithfulness spot-check — cheap because it's a
handful of calls, not the full set (rag-evaluation skill: start with recall,
LLM-as-judge is the expensive/noisy step).

Usage: python scripts/eval_golden_set.py
"""

import asyncio
import json
import sys
from pathlib import Path

import psycopg
import truststore

truststore.inject_into_ssl()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.chat import _SYSTEM_PROMPT, _build_context, _extract_citations  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services import db, retrieval  # noqa: E402
from app.services import neo4j as neo4j_service  # noqa: E402
from app.services.llm import LLMClient  # noqa: E402

GOLDEN_SET_PATH = Path(__file__).resolve().parent.parent / "eval" / "golden_set.json"
REPORT_PATH = Path(__file__).resolve().parent.parent / "eval" / "report.md"

# One representative case per persona for the LLM-answer qualitative check —
# picked to cover superseded + isolation + cross-reference, the categories
# where baseline vs. candidate is expected to diverge most visibly.
QUALITATIVE_CASE_IDS = {"marcus-02", "priya-05", "dana-04", "sam-06"}

MODES = ["baseline", "candidate"]


async def resolve_personas(database_url: str, personas: dict) -> dict:
    async with await psycopg.AsyncConnection.connect(database_url) as conn, conn.cursor() as cur:
        await cur.execute(
            "select u.email, p.id, p.department, p.role from auth.users u "
            "join profiles p on p.id = u.id where u.email = any(%s)",
            ([info["email"] for info in personas.values()],),
        )
        by_email = {
            row[0]: {"id": str(row[1]), "department": row[2], "role": row[3]} for row in await cur.fetchall()
        }

    resolved = {}
    missing = []
    for name, info in personas.items():
        row = by_email.get(info["email"])
        if not row:
            missing.append(info["email"])
            continue
        if row["department"] != info["department"] or row["role"] != info["role"]:
            raise SystemExit(
                f"persona '{name}' ({info['email']}) has department/role "
                f"{row['department']!r}/{row['role']!r} in Postgres, expected "
                f"{info['department']!r}/{info['role']!r} — re-check the signup"
            )
        resolved[name] = row["id"]
    if missing:
        raise SystemExit(
            "missing eval persona account(s), sign up through the running app first: " + ", ".join(missing)
        )
    return resolved


async def resolve_slug_map(pool) -> tuple[dict, dict]:
    policies = await db.list_policies(pool)
    id_to_slug = {p["id"]: p["slug"] for p in policies}
    slug_to_id = {p["slug"]: p["id"] for p in policies}
    return id_to_slug, slug_to_id


def score_case(case: dict, chunks: list, id_to_slug: dict) -> dict:
    result_slugs = [id_to_slug.get(c.policy_id, c.policy_id) for c in chunks]
    related_slugs = [id_to_slug.get(c.policy_id, c.policy_id) for c in chunks if c.supplementary]

    expected = set(case["expected_doc_ids"])
    forbidden = set(case["forbidden_doc_ids"])
    expected_related = set(case["expected_related_ids"])

    return {
        "recall_hit": bool(expected) and bool(expected & set(result_slugs)),
        "no_expected_case": not expected,  # isolation cases: success = nothing forbidden leaked
        "forbidden_violation": bool(forbidden & set(result_slugs)),
        "related_hit": bool(expected_related) and bool(expected_related & set(related_slugs)),
        "result_slugs": result_slugs,
    }


async def generate_answer(settings, chunks: list, question: str) -> tuple[str, list]:
    system_prompt = _SYSTEM_PROMPT.format(context=_build_context(chunks))
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]
    llm = LLMClient(settings)
    parts = []
    async for token in llm.stream_chat(messages):
        parts.append(token)
    text = "".join(parts)
    return text, _extract_citations(text, chunks)


async def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL is not set in .env")
    if not (settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password):
        raise SystemExit("NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD are not set in .env")

    golden = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    k = golden["k"]

    pool = db.create_pool(settings)
    await pool.open()
    driver = neo4j_service.create_driver(settings)
    try:
        employee_ids = await resolve_personas(settings.database_url, golden["personas"])
        id_to_slug, _ = await resolve_slug_map(pool)

        rows = []
        qualitative = []
        for case in golden["cases"]:
            employee_id = employee_ids[case["persona"]]
            per_mode = {}
            for mode in MODES:
                chunks = await retrieval.retrieve_chunks(
                    pool=pool,
                    driver=driver,
                    settings=settings,
                    employee_id=employee_id,
                    query=case["question"],
                    k=k,
                    use_graph=(mode == "candidate"),
                )
                score = score_case(case, chunks, id_to_slug)
                per_mode[mode] = {"chunks": chunks, "score": score}
                print(f"{case['id']:12s} {mode:10s} -> {score['result_slugs']}")

            rows.append({"case": case, "modes": per_mode})

            if case["id"] in QUALITATIVE_CASE_IDS:
                answers = {}
                for mode in MODES:
                    text, citations = await generate_answer(
                        settings, per_mode[mode]["chunks"], case["question"]
                    )
                    answers[mode] = {"text": text, "citations": citations}
                qualitative.append({"case": case, "answers": answers})

        report = render_report(rows, qualitative, k)
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(f"\nwrote {REPORT_PATH}")
    finally:
        await pool.close()
        await driver.close()


def render_report(rows: list, qualitative: list, k: int) -> str:
    lines = [
        "# M6 Eval Report — Golden Set (vector-only baseline vs. hybrid vector+graph)",
        "",
        f"{len(rows)} cases, k={k}. Generated by `scripts/eval_golden_set.py`. "
        "Per `rag-evaluation` skill / CLAUDE.md agent rules: this is the measured basis for any "
        "claim that the graph step helps — see the delta table before trusting the qualitative notes.",
        "",
        "## Retrieval recall by category",
        "",
        "| Category | Cases | Baseline recall | Candidate recall | Baseline isolation violations | "
        "Candidate isolation violations | Candidate reference-enrichment hit |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    by_cat: dict[str, list] = {}
    for row in rows:
        by_cat.setdefault(row["case"]["category"], []).append(row)

    for category, crows in by_cat.items():
        n = len(crows)
        recall_needed = [r for r in crows if not r["modes"]["baseline"]["score"]["no_expected_case"]]
        forbidden_relevant = [r for r in crows if r["case"]["forbidden_doc_ids"]]
        related_relevant = [r for r in crows if r["case"]["expected_related_ids"]]

        def pct(count, total):
            return "n/a" if total == 0 else f"{count}/{total}"

        baseline_recall = sum(r["modes"]["baseline"]["score"]["recall_hit"] for r in recall_needed)
        candidate_recall = sum(r["modes"]["candidate"]["score"]["recall_hit"] for r in recall_needed)
        baseline_violations = sum(
            r["modes"]["baseline"]["score"]["forbidden_violation"] for r in forbidden_relevant
        )
        candidate_violations = sum(
            r["modes"]["candidate"]["score"]["forbidden_violation"] for r in forbidden_relevant
        )
        candidate_related = sum(r["modes"]["candidate"]["score"]["related_hit"] for r in related_relevant)

        lines.append(
            f"| {category} | {n} | {pct(baseline_recall, len(recall_needed))} | "
            f"{pct(candidate_recall, len(recall_needed))} | "
            f"{pct(baseline_violations, len(forbidden_relevant))} | "
            f"{pct(candidate_violations, len(forbidden_relevant))} | "
            f"{pct(candidate_related, len(related_relevant))} |"
        )

    lines += [
        "",
        "## Per-case detail",
        "",
        "| Case | Category | Baseline | Candidate |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        case = row["case"]

        def summarize(mode, row=row, case=case):
            s = row["modes"][mode]["score"]
            bits = []
            if not s["no_expected_case"]:
                bits.append("recall OK" if s["recall_hit"] else "recall MISS")
            if case["forbidden_doc_ids"]:
                bits.append("LEAK" if s["forbidden_violation"] else "isolated OK")
            if case["expected_related_ids"]:
                bits.append("reference OK" if s["related_hit"] else "reference MISS")
            return ", ".join(bits) if bits else "-"

        lines.append(f"| {case['id']} | {case['category']} | {summarize('baseline')} | {summarize('candidate')} |")

    lines += ["", "## Qualitative faithfulness spot-check (subset)", ""]
    for entry in qualitative:
        case = entry["case"]
        lines.append(f"### {case['id']} — {case['question']}")
        for mode in MODES:
            ans = entry["answers"][mode]
            cited = ", ".join(f"[{c['index']}] {c['title']} v{c['version']}" for c in ans["citations"]) or "(none)"
            lines.append(f"\n**{mode}** — citations: {cited}\n\n> {ans['text'].strip()}\n")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    asyncio.run(main())
