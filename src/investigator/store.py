import sqlite3
import json
from pathlib import Path
from typing import Iterator, Tuple, Dict, Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  step TEXT NOT NULL,
  payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
"""


class EventStore:
    """
    Event-sourced storage for investigator runs.

    This is the authoritative, replayable record of all agent actions.
    """

    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def append(self, event) -> None:
        """
        Append a new event to the store.
        """
        self.conn.execute(
            "INSERT INTO events(run_id, ts, step, payload) VALUES (?,?,?,?)",
            (
                event.run_id,
                event.ts.isoformat(),
                event.step,
                json.dumps(event.payload),
            ),
        )
        self.conn.commit()

    def load(self, run_id: str) -> Iterator[Tuple[str, str, Dict[str, Any]]]:
        """
        Iterate over all events for a given run_id in chronological order.
        """
        cur = self.conn.execute(
            "SELECT ts, step, payload FROM events WHERE run_id=? ORDER BY id ASC",
            (run_id,),
        )
        for ts, step, payload in cur.fetchall():
            yield ts, step, json.loads(payload)

    def load_run(self, run_id: str) -> Iterator[Tuple[str, str, Dict[str, Any]]]:
        """
        Semantic alias for load(run_id).
        """
        return self.load(run_id)
