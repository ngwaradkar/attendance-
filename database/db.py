from pathlib import Path
import os
import sqlite3
from contextlib import contextmanager
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
def get_db_path():
    return Path(os.environ.get('ATTENDANCE_DB_PATH', str(ROOT / 'data' / 'attendance.db')))

DB_PATH = get_db_path()

@contextmanager
def connection():
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def query(sql, params=()):
    with connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)

def one(sql, params=()):
    with connection() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

def execute(sql, params=()):
    with connection() as conn:
        return conn.execute(sql, params).lastrowid

def settings():
    return {r['key']: r['value'] for r in query('SELECT key,value FROM settings').to_dict('records')}

def audit(conn, user, action, details):
    from utils.helpers import now
    conn.execute('INSERT INTO audit_logs(timestamp,user_id,username,action,details) VALUES(?,?,?,?,?)',
                 (now(),user['id'],user['username'],action,str(details)))

def initialize():
    from database.schema import SCHEMA
    from database.seed_data import seed
    with connection() as conn:
        conn.executescript(SCHEMA)
        if not conn.execute('SELECT 1 FROM users LIMIT 1').fetchone():
            seed(conn)
