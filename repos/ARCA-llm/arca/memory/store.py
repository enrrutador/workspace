from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from arca.model import Expediente, utc_now


class MemoryStore:
    """Portable SQLite memory for assertions, evidence documents, procedures and episodes."""
    def __init__(self, path: str | Path = "arca.db", max_docs: int = 500, max_episodes: int = 2000) -> None:
        self.path = str(path)
        self.max_docs = max(1, int(max_docs))
        self.max_episodes = max(1, int(max_episodes))
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path); db.row_factory = sqlite3.Row
        try:
            yield db; db.commit()
        finally: db.close()

    def _initialize(self) -> None:
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS assertions(id INTEGER PRIMARY KEY, subject TEXT NOT NULL, predicate TEXT NOT NULL, object TEXT NOT NULL, confidence REAL NOT NULL DEFAULT 1.0, source TEXT NOT NULL, valid_from TEXT NOT NULL, superseded_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_assertion_sp ON assertions(subject,predicate,superseded_at);
            CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL UNIQUE, snippet TEXT NOT NULL, content TEXT NOT NULL, source TEXT NOT NULL, fetched_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS episodes(id TEXT PRIMARY KEY, created_at TEXT NOT NULL, objective TEXT NOT NULL, task_kind TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS procedures(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, triggers TEXT NOT NULL DEFAULT '', steps TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'user', uses INTEGER NOT NULL DEFAULT 0, successes INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS bandit(context TEXT NOT NULL, operator TEXT NOT NULL, trials INTEGER NOT NULL DEFAULT 0, reward REAL NOT NULL DEFAULT 0, PRIMARY KEY(context,operator));
            """)

    def remember(self, subject: str, predicate: str, object_: str, source: str = "user", confidence: float = 1.0) -> int:
        values = (subject.strip().casefold(), predicate.strip().casefold(), object_.strip(), max(0.0, min(1.0, confidence)), source, utc_now())
        if not all(values[:3]): raise ValueError("subject, predicate and object are required")
        with self.connect() as db:
            return int(db.execute("INSERT INTO assertions(subject,predicate,object,confidence,source,valid_from) VALUES(?,?,?,?,?,?)", values).lastrowid)

    def recall(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        tokens = [t.casefold() for t in query.split() if len(t) > 1][:8]
        if not tokens: return []
        clauses, params = [], []
        for token in tokens:
            clauses.append("(subject LIKE ? OR predicate LIKE ? OR object LIKE ?)"); value = f"%{token}%"; params += [value, value, value]
        params.append(limit)
        with self.connect() as db:
            return [dict(row) for row in db.execute(f"SELECT subject,predicate,object,confidence,source,valid_from FROM assertions WHERE superseded_at IS NULL AND ({' OR '.join(clauses)}) ORDER BY confidence DESC,id DESC LIMIT ?", params)]

    def save_document(self, title: str, url: str, snippet: str, content: str, source: str = "web") -> None:
        with self.connect() as db:
            db.execute("""INSERT INTO documents(title,url,snippet,content,source,fetched_at) VALUES(?,?,?,?,?,?)
            ON CONFLICT(url) DO UPDATE SET title=excluded.title,snippet=excluded.snippet,content=excluded.content,source=excluded.source,fetched_at=excluded.fetched_at""", (title, url, snippet, content, source, utc_now()))
            db.execute("""DELETE FROM documents WHERE id NOT IN (SELECT id FROM documents ORDER BY fetched_at DESC, id DESC LIMIT ?)""", (self.max_docs,))

    def search_documents(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        tokens = [t.casefold() for t in query.split() if len(t) > 1][:8]
        if not tokens: return []
        clauses, params = [], []
        for token in tokens:
            clauses.append("(title LIKE ? OR snippet LIKE ? OR content LIKE ?)"); value = f"%{token}%"; params += [value, value, value]
        params.append(limit)
        with self.connect() as db:
            return [dict(row) for row in db.execute(f"SELECT title,url,snippet,content,source,fetched_at FROM documents WHERE {' OR '.join(clauses)} ORDER BY id DESC LIMIT ?", params)]

    def save_episode(self, expediente: Expediente) -> None:
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO episodes VALUES(?,?,?,?,?)", (expediente.id, expediente.created_at, expediente.objective, expediente.task_kind, json.dumps(expediente.to_dict(), ensure_ascii=False)))
            db.execute("DELETE FROM episodes WHERE id NOT IN (SELECT id FROM episodes ORDER BY created_at DESC LIMIT ?)", (self.max_episodes,))

    def save_procedure(self, name: str, triggers: list[str], steps: list[str], source: str = "user") -> int:
        name = name.strip()
        if not name or not steps:
            raise ValueError("procedure requires a name and at least one step")
        clean_steps = [step.strip() for step in steps if step.strip()]
        clean_triggers = ",".join(sorted({trigger.strip().casefold() for trigger in triggers if trigger.strip()}))
        now = utc_now()
        with self.connect() as db:
            cursor = db.execute("""INSERT INTO procedures(name,triggers,steps,source,created_at,updated_at) VALUES(?,?,?,?,?,?)
            ON CONFLICT(name) DO UPDATE SET triggers=excluded.triggers,steps=excluded.steps,source=excluded.source,updated_at=excluded.updated_at""", (name, clean_triggers, json.dumps(clean_steps, ensure_ascii=False), source, now, now))
            return int(cursor.lastrowid)

    def find_procedure(self, query: str) -> dict[str, Any] | None:
        tokens = [t.casefold() for t in query.split() if len(t) > 2][:8]
        if not tokens:
            return None
        clauses, params = [], []
        for token in tokens:
            clauses.append("(name LIKE ? OR triggers LIKE ?)")
            value = f"%{token}%"
            params += [value, value]
        params.append(1)
        with self.connect() as db:
            row = db.execute(f"SELECT * FROM procedures WHERE {' OR '.join(clauses)} ORDER BY uses DESC, updated_at DESC LIMIT ?", params).fetchone()
        if row is None:
            return None
        record = dict(row)
        record["steps"] = json.loads(record["steps"])
        record["trigger_list"] = [item for item in record.pop("triggers").split(",") if item]
        return record

    def record_procedure_use(self, procedure_id: int, success: bool) -> None:
        with self.connect() as db:
            db.execute("UPDATE procedures SET uses=uses+1, successes=successes+? WHERE id=?", (1 if success else 0, procedure_id))

    def list_procedures(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = [dict(row) for row in db.execute("SELECT * FROM procedures ORDER BY updated_at DESC LIMIT ?", (limit,))]
        for record in rows:
            record["steps"] = json.loads(record["steps"])
        return rows

    def ensure_graph_tables(self) -> None:
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS concepts(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, hv BLOB);
            CREATE TABLE IF NOT EXISTS triples(
                id INTEGER PRIMARY KEY,
                subject_id INTEGER NOT NULL REFERENCES concepts(id),
                predicate TEXT NOT NULL,
                object_text TEXT NOT NULL,
                passage TEXT NOT NULL,
                aspect TEXT NOT NULL,
                source_url TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_triples_subj_aspect ON triples(subject_id, aspect);
            """)

    def add_triple(self, subject_id: int, predicate: str, object_text: str, passage: str, aspect: str, source_url: str = "") -> int:
        from arca.model import utc_now

        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO triples(subject_id,predicate,object_text,passage,aspect,source_url,created_at) VALUES(?,?,?,?,?,?,?)",
                (subject_id, predicate, object_text[:160], passage[:600], aspect, source_url, utc_now()))
            return int(cursor.lastrowid)

    def stats(self) -> dict[str, int]:
        with self.connect() as db:
            counts = {table: int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in ("assertions", "documents", "episodes", "procedures")}
        if self.has_table("triples"):
            with self.connect() as db:
                counts["triples"] = int(db.execute("SELECT COUNT(*) FROM triples").fetchone()[0])
        return counts

    def has_table(self, table: str) -> bool:
        with self.connect() as db:
            row = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            return row is not None


    def bandit_rows(self, context: str) -> list[dict[str, Any]]:
        with self.connect() as db: return [dict(row) for row in db.execute("SELECT * FROM bandit WHERE context=?", (context,))]
    def reward(self, context: str, operator: str, value: float) -> None:
        with self.connect() as db: db.execute("""INSERT INTO bandit(context,operator,trials,reward) VALUES(?,?,1,?) ON CONFLICT(context,operator) DO UPDATE SET reward=(bandit.reward*bandit.trials+excluded.reward)/(bandit.trials+1),trials=bandit.trials+1""", (context, operator, value))
