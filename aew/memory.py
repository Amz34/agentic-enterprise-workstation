#!/usr/bin/env python3
"""
AEW Episodic Memory & Vector/Context Store.
Persists past mission decisions, reviewer feedback, architectural rules, and failure learnings.
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


class MemoryStore:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_dir = Path.home() / ".config" / "aew"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = db_dir / "memory.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Missions history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS missions (
                    id TEXT PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    coder_provider TEXT,
                    reviewer_provider TEXT,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    completed_at REAL
                )
            """)
            # Learned rules & feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learned_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    rule_text TEXT NOT NULL,
                    source_mission TEXT,
                    created_at REAL NOT NULL
                )
            """)
            # Worktree logs and audit events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            conn.commit()

    def record_mission_start(self, mission_id: str, task: str, branch: str, coder: str, reviewer: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO missions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (mission_id, task, branch, coder, reviewer, "IN_PROGRESS", time.time(), None)
            )

    def record_mission_end(self, mission_id: str, status: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE missions SET status = ?, completed_at = ? WHERE id = ?",
                (status, time.time(), mission_id)
            )

    def add_rule(self, category: str, rule_text: str, source_mission: Optional[str] = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO learned_rules (category, rule_text, source_mission, created_at) VALUES (?, ?, ?, ?)",
                (category, rule_text, source_mission, time.time())
            )

    def get_rules(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if category:
                rows = conn.execute("SELECT * FROM learned_rules WHERE category = ? ORDER BY id DESC", (category,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM learned_rules ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    def log_audit_event(self, mission_id: str, event_type: str, details: Any):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO audit_logs (mission_id, event_type, details, timestamp) VALUES (?, ?, ?, ?)",
                (mission_id, event_type, json.dumps(details) if not isinstance(details, str) else details, time.time())
            )

    def get_recent_missions(self, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM missions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
