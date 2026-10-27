"""FastAPI app. The agent only recommends; only POST /decision changes a case's status."""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth
from .agent import AgentError, run_triage
from .db import Store
from .llm import LLM, default_llm
from .mcp_client import McpToolbox
from .priority import assess

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")

DECISION_STATUS = {"approve": "approved", "reject": "rejected", "request_more_info": "info_requested"}
Lang = Literal["en", "hi", "kn"]


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject", "request_more_info"]
    message: str | None = None  # final message to the applicant, possibly edited by the officer
    note: str | None = None
    lang: Lang = "en"


class LoginIn(BaseModel):
    username: str
    password: str


def create_app(llm: LLM | None = None, db_path: str | None = None, toolbox: McpToolbox | None = None,
               require_login: bool | None = None, seed_path: str | Path | None = None) -> FastAPI:
    """require_login defaults to on; tests and local hacking can pass False or set AUTH_DISABLED=1."""
    login_on = (os.getenv("AUTH_DISABLED") != "1") if require_login is None else require_login
    seed_file = Path(seed_path) if seed_path else ROOT / "backend" / "seed" / "triage_seed.json"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with AsyncExitStack() as stack:
            app.state.toolbox = toolbox or McpToolbox()
            await app.state.toolbox.start(stack)
            app.state.llm = llm if llm is not None else default_llm()
            app.state.store = Store(db_path or os.getenv("DB_PATH", "seva.db"))
            if not app.state.store.has_any_triage() and seed_file.exists():
                app.state.store.seed(json.loads(seed_file.read_text(encoding="utf-8")))
            yield

    app = FastAPI(title="Seva Agent", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def officer(authorization: str | None = Header(default=None)) -> str:
        if not login_on:
            return "officer"
        user = auth.verify_token(authorization.removeprefix("Bearer ").strip()) if authorization else None
        if user is None:
            raise HTTPException(401, "Please sign in")
        return user

    @app.get("/api/health")
    async def health():
        return {"ok": True, "llm_configured": app.state.llm is not None, "login": login_on,
                "mcp_tools": [t["name"] for t in app.state.toolbox.tools]}

    @app.post("/api/login")
    async def login(body: LoginIn):
        if not auth.check_login(body.username, body.password):
            raise HTTPException(401, "Wrong username or password")
        return {"token": auth.make_token(body.username), "user": body.username}

    @app.get("/api/cases")
    async def list_cases(_: str = Depends(officer)):
        data, err = await app.state.toolbox.call("list_open_cases", {})
        if err:
            raise HTTPException(502, str(data))
        statuses = app.state.store.statuses()
        return [c | {"status": statuses.get(c["id"], "new")} for c in data["cases"]]

    @app.get("/api/overview")
    async def overview(lang: Lang = "en", _: str = Depends(officer)):
        """Every case with a transparent priority score and reasons, most urgent first, plus counts."""
        data, err = await app.state.toolbox.call("list_open_cases", {})
        if err:
            raise HTTPException(502, str(data))
        statuses = app.state.store.statuses()
        assessed = await asyncio.gather(*[assess(c["id"], app.state.toolbox) for c in data["cases"]])
        items = []
        for c, a in zip(data["cases"], assessed):
            status = statuses.get(c["id"], "new")
            rec = app.state.store.get_triage(c["id"], lang)
            items.append(c | a | {"status": status,
                                  "agent": {"action": rec["triage"]["recommended_action"], "confidence": rec["triage"]["confidence"]} if rec else None})
        decided = {"approved", "rejected", "info_requested"}
        # undecided cases first, highest score first; decided cases sink to the bottom
        items.sort(key=lambda i: (i["status"] in decided, -i["score"], i["id"]))
        open_items = [i for i in items if i["status"] not in decided]
        return {"counts": {"total": len(items), "open": len(open_items),
                           "attention": sum(1 for i in open_items if i["level"] == "high"),
                           "ready": sum(1 for i in open_items if not i["needs_fix"]),
                           "decided": len(items) - len(open_items)},
                "cases": items}

    @app.get("/api/cases/{case_id}")
    async def get_case(case_id: str, _: str = Depends(officer)):
        data, err = await app.state.toolbox.call("get_case", {"case_id": case_id})
        if err:
            raise HTTPException(404, str(data))
        return data

    @app.post("/api/cases/{case_id}/analyze")
    async def analyze(case_id: str, lang: Lang = "en", _: str = Depends(officer)):
        if app.state.llm is None:
            raise HTTPException(503, "ANTHROPIC_API_KEY is not configured. Copy backend/.env.example to backend/.env and add your key.")
        cap = int(os.getenv("MAX_LIVE_ANALYSES_PER_DAY", "40"))
        if app.state.store.used_today() >= cap:
            raise HTTPException(429, "Today's limit of live AI checks has been reached for this demo. The saved analyses still work.")
        _, err = await app.state.toolbox.call("get_case", {"case_id": case_id})
        if err:
            raise HTTPException(404, f"Unknown case {case_id}")
        try:
            result = await run_triage(case_id, app.state.llm, app.state.toolbox, lang=lang)
        except AgentError as e:
            raise HTTPException(502, str(e))
        app.state.store.count_use()
        app.state.store.save_triage(case_id, result, lang)
        return app.state.store.get_triage(case_id, lang)

    @app.get("/api/cases/{case_id}/triage")
    async def get_triage(case_id: str, lang: Lang = "en", _: str = Depends(officer)):
        t = app.state.store.get_triage(case_id, lang)
        if t is None:
            raise HTTPException(404, "No triage yet for this case")
        return t | {"decisions": app.state.store.decisions(case_id)}

    @app.post("/api/cases/{case_id}/decision")
    async def decide(case_id: str, body: DecisionIn, _: str = Depends(officer)):
        t = app.state.store.get_triage(case_id, body.lang)
        if t is None:
            raise HTTPException(409, "Run the analysis before deciding")
        agent_msg = t["triage"]["message_to_applicant"]
        final = body.message if body.message is not None else agent_msg
        app.state.store.record_decision(case_id, body.decision, DECISION_STATUS[body.decision], final,
                                        final != agent_msg, body.note)
        return {"case_id": case_id, "status": DECISION_STATUS[body.decision],
                "decisions": app.state.store.decisions(case_id)}

    # One container serves the built frontend too, so the live demo is a single deployable.
    dist = ROOT / "frontend" / "dist"
    if (dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            if path.startswith("api/"):
                raise HTTPException(404)
            f = dist / path
            return FileResponse(f if path and f.is_file() else dist / "index.html")

    return app


app = create_app()
