from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .memory_models import MemoryDecision, MemoryRecord

CATEGORY_BRANCHES = {
    "stocks": (
        "markets.stocks",
        ["markets.portfolio", "markets.opportunities", "news.companies"],
    ),
    "markets": ("markets", ["markets.stocks", "markets.portfolio", "news.companies"]),
    "sports": (
        "sports_betting",
        ["sports_betting.teams", "sports_betting.odds", "news.sports"],
    ),
    "sports_betting": (
        "sports_betting",
        ["sports_betting.teams", "sports_betting.odds", "news.sports"],
    ),
    "polymarket": (
        "polymarket",
        ["polymarket.positions", "news.politics", "news.economics"],
    ),
    "news": ("news", ["markets", "sports_betting", "polymarket"]),
    "user_profile": (
        "user_profile",
        ["decision_dna", "markets", "sports_betting", "polymarket"],
    ),
    "decision_dna": (
        "decision_dna",
        ["user_profile", "markets.opportunities", "sports_betting", "polymarket"],
    ),
}


class MemoryEngine:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    normalized_content TEXT NOT NULL,
                    primary_branch TEXT NOT NULL,
                    linked_branches TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    importance INTEGER NOT NULL,
                    confidence INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    action TEXT NOT NULL,
                    source TEXT NOT NULL,
                    reinforcement_count INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """)

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.lower().strip().split())

    @staticmethod
    def _classify_type(content: str, user_confirmed: bool) -> str:
        text = content.lower()

        if user_confirmed:
            return "core"
        if any(
            word in text
            for word in ["always", "never", "prefer", "usually", "normally"]
        ):
            return "behavioral_signal"
        if any(
            word in text
            for word in ["goal", "strategy", "plan", "watching", "position"]
        ):
            return "strategic"
        if any(word in text for word in ["today", "tonight", "this week", "right now"]):
            return "temporary"
        return "contextual"

    @staticmethod
    def _score(content: str, memory_type: str, user_confirmed: bool) -> tuple[int, int]:
        importance = 45
        confidence = 58

        if user_confirmed:
            importance += 35
            confidence += 35

        if memory_type == "behavioral_signal":
            importance += 25
            confidence += 8
        elif memory_type == "strategic":
            importance += 22
            confidence += 12
        elif memory_type == "temporary":
            importance -= 8
            confidence += 8

        if len(content.split()) >= 10:
            importance += 6
            confidence += 5

        return min(100, importance), min(100, confidence)

    @staticmethod
    def _decision(
        importance: int, confidence: int, user_confirmed: bool
    ) -> tuple[str, str]:
        if user_confirmed:
            return "stored", "confirmed"
        if importance >= 70 and confidence >= 68:
            return "stored", "observed"
        if importance >= 55:
            return "inbox", "proposed"
        return "ignored", "proposed"

    def add_memory(
        self,
        content: str,
        active_category: str,
        source: str,
        user_confirmed: bool,
    ) -> MemoryDecision:
        normalized = self._normalize(content)
        category = active_category.lower().strip()
        primary_branch, linked_branches = CATEGORY_BRANCHES.get(
            category,
            (f"custom.{category}", ["user_profile"]),
        )

        memory_type = self._classify_type(content, user_confirmed)
        importance, confidence = self._score(content, memory_type, user_confirmed)
        action, status = self._decision(importance, confidence, user_confirmed)
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM memories WHERE normalized_content = ? AND primary_branch = ?",
                (normalized, primary_branch),
            ).fetchone()

            if existing:
                reinforcement_count = int(existing["reinforcement_count"]) + 1
                importance = min(100, max(importance, int(existing["importance"])) + 5)
                confidence = min(100, max(confidence, int(existing["confidence"])) + 7)
                action, status = self._decision(importance, confidence, user_confirmed)
                if reinforcement_count >= 3 and status not in {"confirmed", "core"}:
                    status = "reinforced"
                    action = "stored"

                connection.execute(
                    """
                    UPDATE memories
                    SET importance = ?, confidence = ?, status = ?, action = ?,
                        reinforcement_count = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        importance,
                        confidence,
                        status,
                        action,
                        reinforcement_count,
                        now,
                        existing["id"],
                    ),
                )
                memory_id = existing["id"]
                created_at = existing["created_at"]
            else:
                memory_id = str(uuid4())
                reinforcement_count = 1
                created_at = now
                connection.execute(
                    """
                    INSERT INTO memories (
                        id, content, normalized_content, primary_branch, linked_branches,
                        memory_type, importance, confidence, status, action, source,
                        reinforcement_count, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        memory_id,
                        content.strip(),
                        normalized,
                        primary_branch,
                        "|".join(linked_branches),
                        memory_type,
                        importance,
                        confidence,
                        status,
                        action,
                        source,
                        reinforcement_count,
                        created_at,
                        now,
                    ),
                )

        record = MemoryRecord(
            id=memory_id,
            content=content.strip(),
            primary_branch=primary_branch,
            linked_branches=linked_branches,
            memory_type=memory_type,
            importance=importance,
            confidence=confidence,
            status=status,
            action=action,
            source=source,
            reinforcement_count=reinforcement_count,
            created_at=created_at,
            updated_at=now,
        )

        explanation = (
            f"Classified as {memory_type}, assigned to {primary_branch}, "
            f"scored {importance}/100 importance and {confidence}/100 confidence."
        )
        return MemoryDecision(memory=record, explanation=explanation)

    def list_memories(
        self, category: str | None = None, inbox_only: bool = False
    ) -> list[MemoryRecord]:
        query = "SELECT * FROM memories"
        clauses = []
        values: list[str] = []

        if category:
            primary, linked = CATEGORY_BRANCHES.get(
                category.lower().strip(),
                (f"custom.{category.lower().strip()}", []),
            )
            branch_values = [primary, *linked]
            branch_clauses = ["primary_branch = ?"]
            values.append(primary)
            for branch in branch_values:
                branch_clauses.append("linked_branches LIKE ?")
                values.append(f"%{branch}%")
            clauses.append("(" + " OR ".join(branch_clauses) + ")")

        if inbox_only:
            clauses.append("action = 'inbox'")

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        query += " ORDER BY importance DESC, updated_at DESC"

        with self._connect() as connection:
            rows = connection.execute(query, values).fetchall()

        return [self._row_to_record(row) for row in rows]

    def confirm_memory(self, memory_id: str, confirmed: bool) -> MemoryRecord | None:
        now = datetime.now(timezone.utc).isoformat()
        status = "confirmed" if confirmed else "rejected"
        action = "stored" if confirmed else "ignored"
        confidence = 100 if confirmed else 0

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE memories
                SET status = ?, action = ?, confidence = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, action, confidence, now, memory_id),
            )
            row = connection.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()

        return self._row_to_record(row) if row else None

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            content=row["content"],
            primary_branch=row["primary_branch"],
            linked_branches=[
                item for item in row["linked_branches"].split("|") if item
            ],
            memory_type=row["memory_type"],
            importance=row["importance"],
            confidence=row["confidence"],
            status=row["status"],
            action=row["action"],
            source=row["source"],
            reinforcement_count=row["reinforcement_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
