"""SQLite helper functions (stdlib sqlite3 only)."""
import sqlite3, os, json
from contextlib import contextmanager
from config import DB_PATH

@contextmanager
def _conn():
    """Open a connection, commit on success, and ALWAYS close it (avoids locked files on Windows)."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def init_db():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, sentence TEXT NOT NULL, intent TEXT NOT NULL,
            result_json TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

def insert(sentence, intent, result):
    with _conn() as c:
        return c.execute("INSERT INTO history(sentence,intent,result_json) VALUES(?,?,?)",
                         (sentence, intent, json.dumps(result))).lastrowid

def fetch_all(limit=50):
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT id,sentence,intent,created_at FROM history ORDER BY id DESC LIMIT ?", (limit,))]

def count():
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM history").fetchone()[0]

def fetch_one(entry_id):
    with _conn() as c:
        r = c.execute("SELECT * FROM history WHERE id=?", (entry_id,)).fetchone()
        return None if r is None else {**dict(r), "result": json.loads(r["result_json"])}

def clear():
    with _conn() as c:
        c.execute("DELETE FROM history")
