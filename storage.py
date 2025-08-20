
import sqlite3, time, json
from typing import Optional, Dict, Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER,
  symbol TEXT,
  side TEXT,
  entry REAL,
  qty REAL,
  sl REAL,
  tp REAL,
  exit_price REAL,
  pnl REAL,
  fee REAL,
  status TEXT,      -- open, closed, cancelled
  meta TEXT
);
CREATE INDEX IF NOT EXISTS ix_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS ix_trades_ts ON trades(ts);
"""

def connect(db_path: str):
    con = sqlite3.connect(db_path, check_same_thread=False)
    cur = con.cursor()
    cur.executescript(SCHEMA)
    con.commit()
    return con

def insert_trade(con, symbol, side, entry, qty, sl, tp, fee, meta: Optional[Dict[str,Any]]=None):
    cur = con.cursor()
    cur.execute("""INSERT INTO trades (ts,symbol,side,entry,qty,sl,tp,fee,status,meta)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (int(time.time()*1000), symbol, side, float(entry), float(qty),
                 float(sl), float(tp), float(fee), "open", json.dumps(meta or {})))
    con.commit()
    return cur.lastrowid

def close_trade(con, trade_id, exit_price, pnl):
    cur = con.cursor()
    cur.execute("UPDATE trades SET exit_price=?, pnl=?, status='closed' WHERE id=?",
                (float(exit_price), float(pnl), trade_id))
    con.commit()

def list_trades(con):
    import pandas as pd
    df = pd.read_sql_query("SELECT * FROM trades ORDER BY ts ASC", con, parse_dates=['ts'])
    return df
