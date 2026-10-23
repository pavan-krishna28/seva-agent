"""Tiny SQLite store: agent runs and the human decision audit trail."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock, self.conn:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS triage (
                  case_id TEXT PRIMARY KEY,
                  status TEXT NOT NULL,
                  triage_json TEXT NOT NULL,
                  trace_json TEXT NOT NULL,
                  model TEXT,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS decisions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  case_id TEXT NOT NULL,
                  decision TEXT NOT NULL,
                  final_message TEXT,
                  message_edited INTEGER NOT NULL DEFAULT 0,
                  note TEXT,
                  decided_at TEXT NOT NULL
                );
                """
            )

    def save_triage(self, case_id: str, result: dict) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO triage(case_id,status,triage_json,trace_json,model,created_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(case_id) DO UPDATE SET status=excluded.status, triage_json=excluded.triage_json, "
                "trace_json=excluded.trace_json, model=excluded.model, created_at=excluded.created_at",
                (case_id, "awaiting_review", json.dumps(result["triage"], ensure_ascii=False),
                 json.dumps(result["trace"], ensure_ascii=False), result.get("model"), _now()),
            )

    def get_triage(self, case_id: str) -> dict | None:
        with self.lock:
            row = self.conn.execute("SELECT * FROM triage WHERE case_id=?", (case_id,)).fetchone()
        if not row:
            return None
        return {"case_id": row["case_id"], "status": row["status"], "triage": json.loads(row["triage_json"]),
                "trace": json.loads(row["trace_json"]), "model": row["model"], "created_at": row["created_at"]}

    def statuses(self) -> dict[str, str]:
        with self.lock:
            return {r["case_id"]: r["status"] for r in self.conn.execute("SELECT case_id,status FROM triage")}

    def record_decision(self, case_id: str, decision: str, status: str, final_message: str | None,
                        edited: bool, note: str | None) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO decisions(case_id,decision,final_message,message_edited,note,decided_at) VALUES(?,?,?,?,?,?)",
                (case_id, decision, final_message, int(edited), note, _now()),
            )
            self.conn.execute("UPDATE triage SET status=? WHERE case_id=?", (status, case_id))

    def decisions(self, case_id: str) -> list[dict]:
        with self.lock:
            rows = self.conn.execute("SELECT * FROM decisions WHERE case_id=? ORDER BY id", (case_id,)).fetchall()
        return [dict(r) | {"message_edited": bool(r["message_edited"])} for r in rows]
