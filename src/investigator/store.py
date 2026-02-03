import sqlite3, json
from pathlib import Path
from .types import Event

SCHEMA = '''
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 run_id TEXT,
 ts TEXT,
 step TEXT,
 payload TEXT
);
'''

class EventStore:
    def __init__(self, db):
        Path(db).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db)
        self.conn.execute(SCHEMA)

    def append(self, e: Event):
        self.conn.execute(
            "INSERT INTO events(run_id,ts,step,payload) VALUES (?,?,?,?)",
            (e.run_id, e.ts.isoformat(), e.step, json.dumps(e.payload))
        )
        self.conn.commit()

    def load(self, run_id):
        for row in self.conn.execute(
            "SELECT ts,step,payload FROM events WHERE run_id=?",
            (run_id,)
        ):
            yield row
