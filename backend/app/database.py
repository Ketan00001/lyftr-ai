import json, os, sqlite3
from datetime import datetime, timezone
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/app.db")

def db_path():
    if DATABASE_URL.startswith("sqlite:///"):
        return DATABASE_URL.replace("sqlite:///", "/", 1)
    raise RuntimeError("Only SQLite DATABASE_URL is supported")

def connect():
    path = Path(db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          session_id TEXT NOT NULL,
          role TEXT NOT NULL,
          content TEXT NOT NULL,
          metadata TEXT,
          created_at TEXT NOT NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)")

def add_message(session_id, role, content, metadata=None):
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages(session_id, role, content, metadata, created_at) VALUES(?,?,?,?,?)",
            (session_id, role, content, json.dumps(metadata) if metadata else None,
             datetime.now(timezone.utc).isoformat())
        )

def get_messages(session_id):
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content, metadata FROM messages WHERE session_id=? ORDER BY id",
            (session_id,)
        ).fetchall()
    return rows

def session_exists(session_id):
    with connect() as conn:
        row = conn.execute("SELECT 1 FROM messages WHERE session_id=? LIMIT 1", (session_id,)).fetchone()
    return row is not None
