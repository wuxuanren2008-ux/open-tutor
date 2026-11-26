"""SQLite 持久化：会话、消息、学习产物版本、复习卡、进度。"""
import os
import sqlite3
from datetime import datetime

import paths

DB_PATH = os.path.join(paths.data_dir(), "tutor.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, title TEXT, subject TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT,
            content TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, kind TEXT,
            title TEXT, content TEXT, version INTEGER, created_at TEXT);
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answer TEXT,
            subject TEXT, reps INTEGER DEFAULT 0, interval INTEGER DEFAULT 0,
            due_at TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS progress (
            key TEXT PRIMARY KEY, value TEXT);
        """)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---- sessions ----
def create_session(title, subject, sid):
    with _conn() as c:
        c.execute("INSERT INTO sessions VALUES (?,?,?,?)", (sid, title, subject, _now()))
    return sid


def list_sessions():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM sessions ORDER BY created_at DESC")]


def delete_session(sid):
    with _conn() as c:
        for t in ("sessions", "messages", "artifacts"):
            c.execute("DELETE FROM %s WHERE session_id=?" % t, (sid,))


def add_message(sid, role, content):
    with _conn() as c:
        c.execute("INSERT INTO messages(session_id,role,content,created_at) VALUES (?,?,?,?)",
                  (sid, role, content, _now()))


def get_messages(sid):
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT role,content,created_at FROM messages WHERE session_id=? ORDER BY id", (sid,))]


# ---- artifacts ----
def add_artifact(sid, kind, title, content):
    with _conn() as c:
        row = c.execute("SELECT MAX(version) v FROM artifacts WHERE session_id=? AND title=?",
                        (sid, title)).fetchone()
        version = (row["v"] or 0) + 1
        c.execute("INSERT INTO artifacts(session_id,kind,title,content,version,created_at) VALUES (?,?,?,?,?,?)",
                  (sid, kind, title, content, version, _now()))
        return version


def list_artifacts(sid=None):
    with _conn() as c:
        if sid:
            return [dict(r) for r in c.execute(
                "SELECT * FROM artifacts WHERE session_id=? ORDER BY id DESC", (sid,))]
        return [dict(r) for r in c.execute("SELECT * FROM artifacts ORDER BY id DESC")]


# ---- review cards ----
def add_card(question, answer, subject):
    with _conn() as c:
        cur = c.execute("INSERT INTO cards(question,answer,subject,due_at,created_at) VALUES (?,?,?,?,?)",
                        (question, answer, subject, _now(), _now()))
        return cur.lastrowid


def list_cards(only_due=False):
    from memory import is_due
    with _conn() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM cards ORDER BY id")]
    if only_due:
        rows = [r for r in rows if is_due(r.get("due_at"))]
    return rows


def review_card(cid, quality, reps, interval, due_at):
    with _conn() as c:
        c.execute("UPDATE cards SET reps=?, interval=?, due_at=? WHERE id=?",
                  (reps, interval, due_at, cid))


def delete_card(cid):
    with _conn() as c:
        c.execute("DELETE FROM cards WHERE id=?", (cid,))


# ---- progress ----
def get_progress(key, default=None):
    with _conn() as c:
        row = c.execute("SELECT value FROM progress WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_progress(key, value):
    with _conn() as c:
        c.execute("INSERT INTO progress(key,value) VALUES (?,?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def bump_counter(key, amount=1):
    cur = int(get_progress(key, "0") or 0) + amount
    set_progress(key, cur)
    return cur
