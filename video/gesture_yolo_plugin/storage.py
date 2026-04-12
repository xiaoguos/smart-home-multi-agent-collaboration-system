from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


@dataclass(frozen=True, slots=True)
class LabelStats:
    label: str
    sample_count: int


class GestureLearningStore:
    def __init__(self, sqlite_path: Path) -> None:
        self._sqlite_path = sqlite_path
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._sqlite_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS gesture_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    feature_json TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_gesture_samples_label
                ON gesture_samples(label);
                """
            )
            self._conn.commit()

    def add_sample(
        self,
        *,
        label: str,
        feature_vector: np.ndarray,
        source: str,
        max_samples_per_label: int,
    ) -> int:
        feature_json = json.dumps(feature_vector.astype(np.float32).tolist(), separators=(",", ":"))
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO gesture_samples(label, feature_json, source, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (label, feature_json, source, now),
            )
            self._conn.execute(
                """
                DELETE FROM gesture_samples
                WHERE id IN (
                    SELECT id
                    FROM gesture_samples
                    WHERE label = ?
                    ORDER BY id DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (label, max_samples_per_label),
            )
            self._conn.commit()
            return self.count_samples(label)

    def count_samples(self, label: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM gesture_samples WHERE label = ?",
            (label,),
        ).fetchone()
        if row is None:
            return 0
        return int(row["count"])

    def list_labels(self) -> list[LabelStats]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT label, COUNT(*) AS sample_count
                FROM gesture_samples
                GROUP BY label
                ORDER BY sample_count DESC, label ASC
                """
            ).fetchall()
        return [LabelStats(label=str(row["label"]), sample_count=int(row["sample_count"])) for row in rows]

    def delete_label(self, label: str) -> int:
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM gesture_samples WHERE label = ?",
                (label,),
            )
            self._conn.commit()
            return int(cursor.rowcount)

    def get_label_centroids(self, *, min_samples_per_label: int) -> dict[str, np.ndarray]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT label, feature_json
                FROM gesture_samples
                ORDER BY id ASC
                """
            ).fetchall()

        grouped: dict[str, list[np.ndarray]] = {}
        for row in rows:
            label = str(row["label"])
            try:
                vector = np.array(json.loads(row["feature_json"]), dtype=np.float32)
            except (ValueError, TypeError, json.JSONDecodeError):
                continue
            if vector.ndim != 1 or vector.size == 0:
                continue
            grouped.setdefault(label, []).append(vector)

        centroids: dict[str, np.ndarray] = {}
        for label, vectors in grouped.items():
            if len(vectors) < min_samples_per_label:
                continue
            stacked = np.vstack(vectors)
            centroid = stacked.mean(axis=0)
            norm = float(np.linalg.norm(centroid))
            if norm <= 1e-8:
                continue
            centroids[label] = (centroid / norm).astype(np.float32)
        return centroids

    def close(self) -> None:
        with self._lock:
            self._conn.close()
