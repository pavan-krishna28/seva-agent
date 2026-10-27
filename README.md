# Seva Agent

A case desk for government officers, in Kannada, Hindi and English. An AI agent reads each application, checks it against the scheme rules, and tells the officer what needs attention first and what to do. **The officer always makes the final call.**

> **Live demo:** _add the link here after deploying_ · **Login:** `officer` / `seva-demo-2026` (a demo account; all data in this repo is made up)

## The problem

In a taluk office, a clerk or officer opens one application at a time, finds the scheme rules, checks every attached document by hand, notices (or misses) that the bank passbook says "Ramesh G" while the form says "Ramesh Gowda", and writes a letter to the applicant asking for what is missing. The same few mistakes repeat: a missing photo, an expired income certificate, a name that does not match across documents, a claim filed after the allowed window.

**Who it affects.** Farmers waiting for crop-loss compensation, students waiting for a scholarship, families waiting for a ration-card update, and the officers who clear these queues every day. A slow or confused queue means a farmer or a student waits weeks for something a quick check would have caught on day one.

**What I chose to build.** Three schemes that many people apply to (crop-loss claim, post-matric scholarship, ration-card update), with six sample cases that each contain a realistic, planted problem. The tool is the one I would want as an officer: tell me what is urgent, show me why, check the file for me, draft the message to the applicant in their own language, and let me decide.

## What an officer can do

1. **See what needs attention first.** The home screen shows counts (waiting, urgent, clean files, decided) and every case ranked by a plain, explainable score: filed too late, missing documents, expired or mismatched documents, empty form fields, and how long it has been waiting. Each row says *why* it is ranked there. No AI is needed for this, so it loads instantly and for free.
2. **Get AI help on one case.** "Check with agent" gives a summary, missing items, risks with evidence (the exact values the agent found), a recommended action with reasons, a confidence level, and a ready-to-send message to the applicant in the applicant's own language. The summary and reasons are written in the language the officer chose for the interface (English, हिन्दी or ಕನ್ನಡ).
3. **Decide.** Approve, ask for more information (return), or reject, after editing the message if needed. Every decision is logged with whether the officer changed the agent's message.
4. **Check the agent's work.** "What the agent did" lists every tool call and what came back.

## How it works

```
React + TypeScript UI ──HTTP──▶ FastAPI ──▶ Agent loop ──▶ Claude (tool use)
 (en / हिन्दी / ಕನ್ನಡ)            │   │          │
   login + overview              │   │          └──MCP (stdio)──▶ MCP server
                                 │   └─ priority score (same tools,   list_open_cases · get_case
                                 ▼      no AI)                       get_scheme_requirements
                              SQLite                                 validate_document · check_deadline
                  analyses per language + decision audit
```

### Main technical decisions

- **The agent recommends, a person decides.** The agent has no tool that changes a case. Status changes only through `POST /api/cases/{id}/decision`, which also records edits. This is the central design rule.
- **MCP for the case data and rule checks** (`mcp_server/`). The backend discovers the tools at startup, so a department could point them at its real case system without touching the agent. The same tools feed the priority score and the agent.
- **A plain tool-calling loop** (`backend/app/agent.py`) with a hard step cap. Claude gathers evidence with the tools and must finish by calling a local `submit_triage` tool with a structured, validated result. A bad submission is bounced back to the model; tool errors are returned to the model so it can recover. Every risk must cite evidence from a tool result.
- **Rules first, AI second.** The ranking and the document checks (name matching, expiry, filing window) are deterministic code, so they are testable and explainable. Claude is used where language and judgment help: summarising, weighing what the findings mean, and writing a polite message in the applicant's language.
- **Local language end to end.** Interface labels, case fields, document names, scheme names and the priority reasons are translated; the AI writes its summary in the officer's chosen language and the applicant message in the applicant's. Analyses are stored per language.
- **Safe to leave online.** Login required (signed tokens, no session store), a daily cap on live AI calls (`MAX_LIVE_ANALYSES_PER_DAY`), and saved analyses (`backend/seed/triage_seed.json`) that load on first start so a reviewer sees real results without spending any API calls.
- **The model sits behind one method** (`backend/app/llm.py`), so tests run the real agent loop and the real MCP server with a scripted model and no network.
- **One container.** FastAPI serves the built UI too (`Dockerfile`), so the live demo is a single service.

## Demo cases (planted problems)

| Case | Language | What the agent should find |
|---|---|---|
| C-1001 | Kannada | Crop photo missing; bank passbook name is abbreviated ("Ramesh G") |
| C-1002 | Hindi | Filed 13 days after the loss; the window is 7 days |
| C-1003 | English | Income certificate expired; marksheet missing |
| C-1004 | Kannada | Clean file: should recommend approve |
| C-1005 | Hindi | Address proof name doesn't match the Aadhaar ("Sunita Kumari" vs "Sunita Devi") |
| C-1006 | English | Household size missing; existing ration card not attached |

## Run it locally

You need Python 3.11+, Node 18+, and an Anthropic API key.

```powershell
# backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # put your ANTHROPIC_API_KEY in .env
uvicorn app.main:app --reload --port 8000

# frontend (new terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

macOS/Linux: use `source .venv/bin/activate` and `cp`. Sign in with `officer` / `seva-demo-2026` (change with `OFFICER_USER` / `OFFICER_PASSWORD`; set `AUTH_DISABLED=1` to skip login while developing).

If the API replies that the key "is not scoped to a workspace", also set `ANTHROPIC_WORKSPACE_ID` in `.env`.

To regenerate the saved analyses (needs the key): `cd backend && python scripts/generate_seed.py`.

## Deploy

`Dockerfile` builds everything into one image. On Render, "New > Blueprint" with this repo uses `render.yaml`; add `ANTHROPIC_API_KEY`, `ANTHROPIC_WORKSPACE_ID` (if your key needs it) and `OFFICER_PASSWORD` as secrets. Any host that runs a Docker image works the same way. The SQLite file lives in the container, so decisions reset on redeploy, which is fine for a demo.

## Tests

```powershell
cd backend
pytest
```

16 tests. They run the real agent loop against the real MCP server over stdio with a **scripted model** standing in for Claude, so they verify the plumbing without an API key: tool discovery, parallel tool calls, error recovery, schema validation, the step cap, the human-decision API, login, the priority ranking and its reasons, per-language analyses, the daily cap and the saved-analysis seed. They do not measure how well Claude reasons about a case; that needs a live run, which `scripts/generate_seed.py` performs on all six cases.

## Known limits

- Case data is a JSON file. A real deployment would point the MCP tools at the department's case system.
- Document checks work on extracted metadata (name, expiry), not on scanned images.
- Hindi and Kannada text should be reviewed by a native speaker before real use. Free-text values such as crop names are shown as entered.
- One shared demo login; a real system needs per-officer accounts, roles and an audit of who decided.
- SQLite is fine for a demo, not for concurrent production load.

## Layout

```
mcp_server/   server.py + data/ (schemes, cases)
backend/      app/ (agent, auth, priority, mcp_client, llm, db, main), seed/, scripts/, tests/
frontend/     Vite + React + TypeScript (i18n.ts, i18n2.ts hold the translations)
Dockerfile    one image for the whole app      render.yaml   Render blueprint
```
