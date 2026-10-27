"""Run the real agent on every demo case in every language and save the results to seed/triage_seed.json.
A fresh deployment loads these on first start, so reviewers see real analyses at once without spending API calls.

    cd backend && python scripts/generate_seed.py        (needs ANTHROPIC_API_KEY in backend/.env)"""
import asyncio
import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.agent import run_triage  # noqa: E402
from app.llm import default_llm  # noqa: E402
from app.mcp_client import McpToolbox  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "seed" / "triage_seed.json"


async def main(only_lang: str | None = None):
    llm = default_llm()
    if llm is None:
        sys.exit("ANTHROPIC_API_KEY is not set")
    rows = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    done = {(r["case_id"], r["lang"]) for r in rows}
    async with AsyncExitStack() as stack:
        tb = McpToolbox()
        await tb.start(stack)
        cases, _ = await tb.call("list_open_cases", {})
        for lang in ([only_lang] if only_lang else ["en", "kn", "hi"]):
            for c in cases["cases"]:
                if (c["id"], lang) in done:
                    continue
                print("analysing", c["id"], lang, flush=True)
                r = await run_triage(c["id"], llm, tb, lang=lang)
                rows.append({"case_id": c["id"], "lang": lang, "triage": r["triage"], "trace": r["trace"], "model": r["model"]})
                OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", len(rows), "analyses to", OUT)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
