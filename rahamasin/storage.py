import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from .models import Candle, Config


class Repository:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS candles(source TEXT, timeframe TEXT, time INTEGER,
                open REAL, high REAL, low REAL, close REAL, volume REAL,
                PRIMARY KEY(source,timeframe,time));
            CREATE TABLE IF NOT EXISTS configuration(id INTEGER PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP, payload TEXT);
            CREATE TABLE IF NOT EXISTS trades(run_id INTEGER, ordinal INTEGER, payload TEXT,
                PRIMARY KEY(run_id,ordinal));
            ''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def candles(self, source, timeframe, start, end):
        with self.connect() as db:
            rows = db.execute('SELECT time,open,high,low,close,volume FROM candles WHERE source=? AND timeframe=? AND time>=? AND time<? ORDER BY time',
                              (source,timeframe,start,end)).fetchall()
        return [Candle(*r) for r in rows]

    def save_candles(self, source, timeframe, candles):
        with self.connect() as db:
            db.executemany('INSERT OR REPLACE INTO candles VALUES(?,?,?,?,?,?,?,?)',
                           [(source,timeframe,c.time,c.open,c.high,c.low,c.close,c.volume) for c in candles])

    def config(self):
        with self.connect() as db:
            row = db.execute('SELECT value FROM configuration WHERE id=1').fetchone()
        return Config.from_dict(json.loads(row[0])) if row else Config()

    def save_config(self, config):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO configuration VALUES(1,?)',(json.dumps(asdict(config)),))

    def save_run(self, result):
        payload = asdict(result)
        trades = payload.pop('trades')
        with self.connect() as db:
            run_id = db.execute('INSERT INTO runs(payload) VALUES(?)',(json.dumps(payload),)).lastrowid
            db.executemany('INSERT INTO trades VALUES(?,?,?)',[(run_id,i,json.dumps(t)) for i,t in enumerate(trades)])
        return run_id

    def runs(self):
        with self.connect() as db:
            return db.execute('SELECT id,created,payload FROM runs ORDER BY id DESC').fetchall()

    def load_run(self, run_id):
        from .models import Result, Trade, Setup, Zone
        with self.connect() as db:
            payload = json.loads(db.execute('SELECT payload FROM runs WHERE id=?',(run_id,)).fetchone()[0])
            rows = db.execute('SELECT payload FROM trades WHERE run_id=? ORDER BY ordinal',(run_id,)).fetchall()
        trades = []
        for row in rows:
            t = json.loads(row[0])
            for key in ('zone','long_zone','short_zone','target_zone'):
                if t['setup'].get(key):
                    t['setup'][key] = Zone(**t['setup'][key])
            t['setup'] = Setup(**t['setup'])
            trades.append(Trade(**t))
        payload['config'] = Config.from_dict(payload['config'])
        return Result(trades=trades, **payload)
