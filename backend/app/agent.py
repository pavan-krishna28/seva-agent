"""Triage agent: Claude tool-calling loop over MCP tools + one local `submit_triage` tool.

The agent never approves or rejects anything. It reads a case, checks it with tools,
and submits a structured recommendation that a human reviewer decides on."""
from __future__ import annotations

import json
from typing import Any

from .llm import LLM
from .mcp_client import McpToolbox

LANG_NAMES = {"en": "English", "hi": "Hindi", "kn": "Kannada"}

SYSTEM_PROMPT = """You are a case-triage assistant for a government services desk.
A human officer makes every decision. Your job is to save them time by reading one case,
checking it against the scheme rules with the tools, and recommending a next step.

Rules:
- Gather evidence with the tools before concluding. Start with get_case, then get_scheme_requirements,
  then validate every required document and check_deadline. Do not guess what a document contains.
- Every risk you report must cite concrete evidence from a tool result.
- Never claim a case is approved or rejected. Recommend only: approve, request_more_info, escalate, or reject.
- Prefer request_more_info over reject when the applicant can fix the problem.
- Write message_to_applicant in the applicant's own language (the case file gives it), in short, polite,
  plain words, listing exactly what they need to bring or fix. No jargon.
- The officer reads the interface in {officer_language}. Write summary, reason, every missing_items[].item and .why,
  and every risks[].issue in {officer_language}. Keep risks[].evidence as the exact values found in the tool results.
  message_to_applicant stays in the applicant's own language, whatever the officer's language is.
- When finished, call submit_triage exactly once. Do not write a final answer in plain text."""

SUBMIT_TRIAGE_TOOL = {
    "name": "submit_triage",
    "description": "Submit the final triage recommendation for the case. Call exactly once when the analysis is complete.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "One or two sentences for the officer, in the officer's language."},
            "missing_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"item": {"type": "string"}, "why": {"type": "string"}},
                    "required": ["item", "why"],
                },
            },
            "risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"issue": {"type": "string"}, "evidence": {"type": "string"}},
                    "required": ["issue", "evidence"],
                },
            },
            "recommended_action": {"type": "string", "enum": ["approve", "request_more_info", "escalate", "reject"]},
            "reason": {"type": "string", "description": "Why this action, for the officer, in the officer's language."},
            "message_to_applicant": {"type": "string", "description": "Message to the applicant in their own language."},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "required": ["summary", "missing_items", "risks", "recommended_action", "reason", "message_to_applicant", "confidence"],
    },
}

REQUIRED_KEYS = SUBMIT_TRIAGE_TOOL["input_schema"]["required"]
ACTIONS = SUBMIT_TRIAGE_TOOL["input_schema"]["properties"]["recommended_action"]["enum"]


class AgentError(RuntimeError):
    pass


def _validate_submission(data: dict) -> str | None:
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        return f"submit_triage is missing required fields: {missing}"
    if data["recommended_action"] not in ACTIONS:
        return f"recommended_action must be one of {ACTIONS}"
    if not str(data["message_to_applicant"]).strip():
        return "message_to_applicant must not be empty"
    return None


def _preview(obj: Any, limit: int = 600) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= limit else s[:limit] + "…"


async def run_triage(case_id: str, llm: LLM, toolbox: McpToolbox, max_steps: int = 10, lang: str = "en") -> dict:
    system = SYSTEM_PROMPT.replace("{officer_language}", LANG_NAMES.get(lang, "English"))
    tools = toolbox.tools + [SUBMIT_TRIAGE_TOOL]
    mcp_names = {t["name"] for t in toolbox.tools}
    messages: list[dict] = [
        {"role": "user", "content": f"Triage case {case_id}. Use the tools, then call submit_triage."}
    ]
    trace: list[dict] = []

    for step in range(1, max_steps + 1):
        resp = await llm.create(system, messages, tools)
        messages.append({"role": "assistant", "content": resp["content"]})
        calls = [b for b in resp["content"] if b["type"] == "tool_use"]

        if not calls:
            messages.append({"role": "user", "content": "Continue with the tools, then call submit_triage."})
            continue

        results = []
        triage: dict | None = None
        for call in calls:
            name, args = call["name"], call["input"]
            if name == "submit_triage":
                err = _validate_submission(args)
                trace.append({"step": step, "tool": name, "source": "local", "input": args,
                              "output": err or "accepted", "is_error": bool(err)})
                if err:
                    results.append({"type": "tool_result", "tool_use_id": call["id"], "content": err, "is_error": True})
                else:
                    triage = args
                    results.append({"type": "tool_result", "tool_use_id": call["id"], "content": "accepted"})
            elif name in mcp_names:
                try:
                    out, is_err = await toolbox.call(name, args)
                except Exception as e:  # transport/server failure: let the model see it and recover
                    out, is_err = f"Tool call failed: {e}", True
                trace.append({"step": step, "tool": name, "source": "mcp", "input": args,
                              "output": _preview(out), "is_error": is_err})
                results.append({"type": "tool_result", "tool_use_id": call["id"],
                                "content": out if isinstance(out, str) else json.dumps(out, ensure_ascii=False),
                                "is_error": is_err})
            else:
                msg = f"Unknown tool '{name}'"
                trace.append({"step": step, "tool": name, "source": "none", "input": args, "output": msg, "is_error": True})
                results.append({"type": "tool_result", "tool_use_id": call["id"], "content": msg, "is_error": True})

        if triage is not None:
            return {"triage": triage, "trace": trace, "steps": step, "model": getattr(llm, "model", "unknown")}
        messages.append({"role": "user", "content": results})

    raise AgentError(f"Agent did not submit a triage within {max_steps} steps")
