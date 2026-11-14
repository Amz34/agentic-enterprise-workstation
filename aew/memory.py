#!/usr/bin/env python3
"""
AEW Enterprise Episodic & Fleet Memory Store.
Supports:
1. Local SQLite file (default per-dev)
2. Remote Central PostgreSQL (via DATABASE_URL or AEW_DATABASE_URL) for cross-team rule sync.
"""

import os
import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


class MemoryStore:
    def __init__(self, db_path: Optional[Path] = None, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("AEW_DATABASE_URL") or os.getenv("DATABASE_URL")
        self.is_postgres = bool(self.database_url and self.database_url.startswith(("postgres://", "postgresql://")))

        if not self.is_postgres:
            if db_path is None:
                db_dir = Path.home() / ".config" / "aew"
                db_dir.mkdir(parents=True, exist_ok=True)
                self.db_path = db_dir / "memory.db"
            else:
                self.db_path = Path(db_path)
                self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_pg_conn(self):
        import psycopg2
        return psycopg2.connect(self.database_url)

    def _init_db(self):
        if self.is_postgres:
            try:
                with self._get_pg_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS missions (
                                id VARCHAR(64) PRIMARY KEY,
                                task_name TEXT NOT NULL,
                                branch TEXT NOT NULL,
                                coder_provider TEXT,
                                reviewer_provider TEXT,
                                status TEXT NOT NULL,
                                created_at DOUBLE PRECISION NOT NULL,
                                completed_at DOUBLE PRECISION
                            );
                            CREATE TABLE IF NOT EXISTS learned_rules (
                                id SERIAL PRIMARY KEY,
                                category TEXT NOT NULL,
                                rule_text TEXT NOT NULL,
                                source_mission TEXT,
                                created_at DOUBLE PRECISION NOT NULL
                            );
                            CREATE TABLE IF NOT EXISTS audit_logs (
                                id SERIAL PRIMARY KEY,
                                mission_id TEXT NOT NULL,
                                event_type TEXT NOT NULL,
                                details TEXT NOT NULL,
                                timestamp DOUBLE PRECISION NOT NULL
                            );
                        """)
                    conn.commit()
            except Exception as e:
                # Fallback to local SQLite if remote postgres is unreachable
                self.is_postgres = False
                db_dir = Path.home() / ".config" / "aew"
                db_dir.mkdir(parents=True, exist_ok=True)
                self.db_path = db_dir / "memory.db"

        if not self.is_postgres:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS learned_rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        rule_text TEXT NOT NULL,
                        source_mission TEXT,
                        created_at REAL NOT NULL
                    )
                """)
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
        if self.is_postgres:
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO missions VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                        (mission_id, task, branch, coder, reviewer, "IN_PROGRESS", time.time(), None)
                    )
                conn.commit()
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO missions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (mission_id, task, branch, coder, reviewer, "IN_PROGRESS", time.time(), None)
                )

    def record_mission_end(self, mission_id: str, status: str):
        if self.is_postgres:
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE missions SET status = %s, completed_at = %s WHERE id = %s",
                        (status, time.time(), mission_id)
                    )
                conn.commit()
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE missions SET status = ?, completed_at = ? WHERE id = ?",
                    (status, time.time(), mission_id)
                )

    def add_rule(self, category: str, rule_text: str, source_mission: Optional[str] = None):
        if self.is_postgres:
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO learned_rules (category, rule_text, source_mission, created_at) VALUES (%s, %s, %s, %s)",
                        (category, rule_text, source_mission, time.time())
                    )
                conn.commit()
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO learned_rules (category, rule_text, source_mission, created_at) VALUES (?, ?, ?, ?)",
                    (category, rule_text, source_mission, time.time())
                )

    def get_rules(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.is_postgres:
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    if category:
                        cur.execute("SELECT id, category, rule_text, source_mission, created_at FROM learned_rules WHERE category = %s ORDER BY id DESC", (category,))
                    else:
                        cur.execute("SELECT id, category, rule_text, source_mission, created_at FROM learned_rules ORDER BY id DESC")
                    rows = cur.fetchall()
                    return [{"id": r[0], "category": r[1], "rule_text": r[2], "source_mission": r[3], "created_at": r[4]} for r in rows]
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                if category:
                    rows = conn.execute("SELECT * FROM learned_rules WHERE category = ? ORDER BY id DESC", (category,)).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM learned_rules ORDER BY id DESC").fetchall()
                return [dict(r) for r in rows]

    def get_recent_missions(self, limit: int = 10) -> List[Dict[str, Any]]:
        if self.is_postgres:
            with self._get_pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, task_name, branch, coder_provider, reviewer_provider, status, created_at, completed_at FROM missions ORDER BY created_at DESC LIMIT %s", (limit,))
                    rows = cur.fetchall()
                    return [{"id": r[0], "task_name": r[1], "branch": r[2], "coder_provider": r[3], "reviewer_provider": r[4], "status": r[5], "created_at": r[6], "completed_at": r[7]} for r in rows]
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT * FROM missions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
                return [dict(r) for r in rows]
