# Seva Agent

An AI agent that helps a government services desk clear a queue of application files faster, in the applicant's own language. **A person still makes every decision.**

Each case (crop-loss claim, scholarship, ration-card update) arrives with form fields and attached documents. The agent reads the file, checks it against the scheme rules using tools, and hands the officer a recommendation: what's missing, what looks wrong (with evidence), what to do next, and a ready-to-send message to the applicant in Kannada, Hindi or English. The officer edits it if needed and approves, asks for more info, or rejects. Every decision is logged.

> All applicant data in this repo is fictional demo data.

## How it works

```
React + TypeScript UI ──HTTP──▶ FastAPI ──▶ Agent loop ──▶ Claude (tool use)
 (en / हिन्दी / ಕನ್ನಡ)            │             │
                                 │             └──MCP (stdio)──▶ MCP server
                                 ▼                               list_open_cases · get_case
                              SQLite                             get_scheme_requirements
                       triage runs + decision audit              validate_document · check_deadline
```

- **MCP server** (`mcp_server/`): exposes the case data and rule checks as tools. The backend discovers them over MCP at startup, so adding a tool needs no agent changes.
- **Agent loop** (`backend/app/agent.py`): plain tool-calling loop. Claude gathers evidence with the MCP tools, then must call a local `submit_triage` tool with a structured result (validated; bad submissions are bounced back to the model). Tool errors are returned to the model so it can recover. Step cap prevents runaway loops.
- **Human in the loop**: the agent can only *recommend*. Case status changes only through `POST /api/cases/{id}/decision`, which also records whether the officer edited the applicant message.
- **Trace**: the UI shows every tool call the agent made and what came back, so the officer can check the work.
- **LLM boundary** (`backend/app/llm.py`): the agent depends on one `create()` method, so the model is swappable and tests run without network.

## Run it

You need Python 3.11+, Node 18+, and an Anthropic API key.

```powershell
# backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # then put your ANTHROPIC_API_KEY in .env
uvicorn app.main:app --reload --port 8000

# frontend (new terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

macOS/Linux: use `source .venv/bin/activate` and `cp` instead.

Open the UI, pick a case, click **Check with agent**.

## Demo cases (planted problems)

| Case | Language | What the agent should find |
|---|---|---|
| C-1001 | Kannada | Crop photo missing; bank passbook name is abbreviated ("Ramesh G") |
| C-1002 | Hindi | Filed 13 days after the loss; the window is 7 days |
| C-1003 | English | Income certificate expired; marksheet missing |
| C-1004 | Kannada | Clean file: should recommend approve |
| C-1005 | Hindi | Address proof name doesn't match the Aadhaar ("Sunita Kumari" vs "Sunita Devi") |
| C-1006 | English | Household size missing; existing ration card not attached |

## Tests

```powershell
cd backend
pytest
```

11 tests. They run the real agent loop against the real MCP server over stdio, with a **scripted LLM** standing in for Claude, so they verify the plumbing (tool discovery, parallel tool calls, error recovery, schema validation, step cap, the human-decision API) without an API key. They do not measure how well Claude reasons about cases; that needs a live run with a key.

## Known limits

- Case data is a JSON file. A real deployment would point the MCP tools at the department's case system.
- Document checks work on extracted metadata (name, expiry), not on scanned images.
- UI translations (Hindi, Kannada) should be reviewed by a native speaker before real use.
- No auth on the API; add it before exposing this anywhere.
- SQLite via the stdlib is fine for a demo, not for concurrent production load.

## Layout

```
mcp_server/   server.py + data/ (schemes, cases)
backend/      app/ (agent, mcp_client, llm, db, main) + tests/
frontend/     Vite + React + TypeScript
```
