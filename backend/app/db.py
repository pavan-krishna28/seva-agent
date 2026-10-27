"""Tiny SQLite store: agent runs (one per case and language), the case status, the human decision audit trail,
and a daily counter that caps live AI calls."""
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
                  case_id TEXT NOT NULL,
                  lang TEXT NOT NULL DEFAULT 'en',
                  triage_json TEXT NOT NULL,
                  trace_json TEXT NOT NULL,
                  model TEXT,
                  created_at TEXT NOT NULL,
                  PRIMARY KEY (case_id, lang)
                );
                CREATE TABLE IF NOT EXISTS case_status (
                  case_id TEXT PRIMARY KEY,
                  status TEXT NOT NULL
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
                CREATE TABLE IF NOT EXISTS usage (day TEXT PRIMARY KEY, n INTEGER NOT NULL);
                """
            )

    # ---- triage -------------------------------------------------------------------------------
    def save_triage(self, case_id: str, result: dict, lang: str = "en") -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO triage(case_id,lang,triage_json,trace_json,model,created_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(case_id,lang) DO UPDATE SET triage_json=excluded.triage_json, "
                "trace_json=excluded.trace_json, model=excluded.model, created_at=excluded.created_at",
                (case_id, lang, json.dumps(result["triage"], ensure_ascii=False),
                 json.dumps(result["trace"], ensure_ascii=False), result.get("model"), _now()),
            )
            # a fresh analysis puts an undecided case in the review queue; it never undoes a decision
            self.conn.execute("INSERT OR IGNORE INTO case_status(case_id,status) VALUES(?, 'awaiting_review')", (case_id,))

    def get_triage(self, case_id: str, lang: str = "en") -> dict | None:
        with self.lock:
            row = self.conn.execute("SELECT * FROM triage WHERE case_id=? AND lang=?", (case_id, lang)).fetchone()
            if row is None:  # fall back to any language so the officer always sees the analysis that exists
                row = self.conn.execute("SELECT * FROM triage WHERE case_id=? ORDER BY created_at DESC", (case_id,)).fetchone()
            status = self.conn.execute("SELECT status FROM case_status WHERE case_id=?", (case_id,)).fetchone()
        if not row:
            return None
        return {"case_id": row["case_id"], "lang": row["lang"], "status": status["status"] if status else "awaiting_review",
                "triage": json.loads(row["triage_json"]), "trace": json.loads(row["trace_json"]),
                "model": row["model"], "created_at": row["created_at"]}

    def statuses(self) -> dict[str, str]:
        with self.lock:
            return {r["case_id"]: r["status"] for r in self.conn.execute("SELECT case_id,status FROM case_status")}

    def has_any_triage(self) -> bool:
        with self.lock:
            return self.conn.execute("SELECT 1 FROM triage LIMIT 1").fetchone() is not None

    def seed(self, rows: list[dict]) -> None:
        """Load pre-computed analyses (made earlier with the real agent) so a fresh deployment is useful at once."""
        for r in rows:
            self.save_triage(r["case_id"], {"triage": r["triage"], "trace": r["trace"], "model": r.get("model")}, r.get("lang", "en"))

    def export(self) -> list[dict]:
        with self.lock:
            rows = self.conn.execute("SELECT * FROM triage ORDER BY case_id, lang").fetchall()
        return [{"case_id": r["case_id"], "lang": r["lang"], "triage": json.loads(r["triage_json"]),
                 "trace": json.loads(r["trace_json"]), "model": r["model"]} for r in rows]

    # ---- decisions ----------------------------------------------------------------------------
    def record_decision(self, case_id: str, decision: str, status: str, final_message: str | None,
                        edited: bool, note: str | None) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO decisions(case_id,decision,final_message,message_edited,note,decided_at) VALUES(?,?,?,?,?,?)",
                (case_id, decision, final_message, int(edited), note, _now()),
            )
            self.conn.execute(
                "INSERT INTO case_status(case_id,status) VALUES(?,?) ON CONFLICT(case_id) DO UPDATE SET status=excluded.status",
                (case_id, status),
            )

    def decisions(self, case_id: str) -> list[dict]:
        with self.lock:
            rows = self.conn.execute("SELECT * FROM decisions WHERE case_id=? ORDER BY id", (case_id,)).fetchall()
        return [dict(r) | {"message_edited": bool(r["message_edited"])} for r in rows]

    # ---- usage cap ----------------------------------------------------------------------------
    def used_today(self) -> int:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.lock:
            row = self.conn.execute("SELECT n FROM usage WHERE day=?", (day,)).fetchone()
        return row["n"] if row else 0

    def count_use(self) -> None:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.lock, self.conn:
            self.conn.execute("INSERT INTO usage(day,n) VALUES(?,1) ON CONFLICT(day) DO UPDATE SET n=n+1", (day,))
