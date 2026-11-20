"""Memory storage API and a dependency-free SQLite implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import UTC, datetime
import json
import re
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, Iterable, Mapping

from .models import (
    AuditEvent,
    LongTermUserMemory,
    MemoryRecordType,
    ProjectFact,
    RetentionRule,
    Sensitivity,
    ShortTermContext,
)

_KINDS = {
    "short_term": ShortTermContext,
    "user_memory": LongTermUserMemory,
    "project_fact": ProjectFact,
    "audit_event": AuditEvent,
}
_SECRET_KEY = re.compile(
    r"(^|_)(password|passwd|pwd|api_?key|api_?token|access_?token|refresh_?token|secret|"
    r"environment|env|system_?variables?)(_|$)", re.IGNORECASE
)


def _safe_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe payload, rejecting likely credential/env containers."""

    def inspect(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                if _SECRET_KEY.search(str(key)):
                    raise ValueError(f"prohibited secret or environment field: {key}")
                inspect(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                inspect(child)

    inspect(value)
    try:
        return json.loads(json.dumps(value, ensure_ascii=False))
    except (TypeError, ValueError) as exc:
        raise ValueError("memory payload must be JSON serializable") from exc


class MemoryStore(ABC):
    """Explicit privacy-scoped operations supported by every memory backend."""

    @abstractmethod
    def write(self, record: MemoryRecordType) -> str: ...

    @abstractmethod
    def search(
        self, *, user_id: str | None = None, project_id: str | None = None,
        query: str | None = None, kinds: Iterable[str] | None = None,
    ) -> list[MemoryRecordType]: ...

    @abstractmethod
    def export(
        self, *, user_id: str | None = None, project_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def delete(
        self, *, user_id: str | None = None, project_id: str | None = None,
        record_id: str | None = None,
    ) -> int: ...


class SQLiteMemoryStore(MemoryStore):
    """Small local backend with mandatory owner/project scoping on reads."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._connection = sqlite3.connect(str(path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS memory_records (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, owner_id TEXT NOT NULL,
                project_id TEXT, source TEXT NOT NULL, created_at TEXT NOT NULL,
                sensitivity TEXT NOT NULL, retention TEXT NOT NULL,
                session_id TEXT, action TEXT, payload TEXT NOT NULL
            )"""
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS memory_owner ON memory_records(owner_id, kind)"
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS memory_project ON memory_records(project_id, kind)"
        )
        self._connection.commit()

    @staticmethod
    def _scope(user_id: str | None, project_id: str | None) -> tuple[str, str]:
        if bool(user_id) == bool(project_id):
            raise ValueError("provide exactly one of user_id or project_id")
        return ("owner_id", user_id) if user_id else ("project_id", project_id)  # type: ignore[return-value]

    def _purge_expired(self) -> None:
        rows = self._connection.execute(
            "SELECT id, created_at, retention FROM memory_records"
        ).fetchall()
        now = datetime.now(UTC)
        expired = []
        for row in rows:
            expiry = RetentionRule(row["retention"]).expires_at(
                datetime.fromisoformat(row["created_at"])
            )
            if expiry is not None and expiry <= now:
                expired.append((row["id"],))
        self._connection.executemany("DELETE FROM memory_records WHERE id = ?", expired)

    def write(self, record: MemoryRecordType) -> str:
        if not isinstance(record, tuple(_KINDS.values())):
            raise TypeError("unsupported memory record")
        kind = next(name for name, model in _KINDS.items() if isinstance(record, model))
        raw = record.details if isinstance(record, AuditEvent) else record.content
        payload = _safe_payload(raw)
        project_id = record.project_id if isinstance(record, (ProjectFact, AuditEvent)) else None
        session_id = record.session_id if isinstance(record, ShortTermContext) else None
        action = record.action if isinstance(record, AuditEvent) else None
        with self._lock, self._connection:
            self._purge_expired()
            self._connection.execute(
                "INSERT INTO memory_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (record.id, kind, record.owner_id, project_id, record.source,
                 record.created_at.astimezone(UTC).isoformat(), record.sensitivity.value,
                 record.retention.value, session_id, action,
                 json.dumps(payload, ensure_ascii=False, sort_keys=True)),
            )
        return record.id

    def search(
        self, *, user_id: str | None = None, project_id: str | None = None,
        query: str | None = None, kinds: Iterable[str] | None = None,
    ) -> list[MemoryRecordType]:
        column, scope_id = self._scope(user_id, project_id)
        clauses, params = [f"{column} = ?"], [scope_id]
        if query:
            clauses.append("payload LIKE ? ESCAPE '\\'")
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            params.append(f"%{escaped}%")
        selected_kinds = tuple(kinds or ())
        unknown = set(selected_kinds) - _KINDS.keys()
        if unknown:
            raise ValueError(f"unknown memory kinds: {sorted(unknown)}")
        if selected_kinds:
            clauses.append(f"kind IN ({','.join('?' for _ in selected_kinds)})")
            params.extend(selected_kinds)
        with self._lock, self._connection:
            self._purge_expired()
            rows = self._connection.execute(
                f"SELECT * FROM memory_records WHERE {' AND '.join(clauses)} ORDER BY created_at",
                params,
            ).fetchall()
        return [self._deserialize(row) for row in rows]

    def export(
        self, *, user_id: str | None = None, project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        records = self.search(user_id=user_id, project_id=project_id)
        return [self._export_record(record) for record in records]

    def delete(
        self, *, user_id: str | None = None, project_id: str | None = None,
        record_id: str | None = None,
    ) -> int:
        column, scope_id = self._scope(user_id, project_id)
        sql, params = f"DELETE FROM memory_records WHERE {column} = ?", [scope_id]
        if record_id:
            sql += " AND id = ?"
            params.append(record_id)
        with self._lock, self._connection:
            cursor = self._connection.execute(sql, params)
        return cursor.rowcount

    def clear_session(self, *, user_id: str, session_id: str) -> int:
        """End a session and remove only its transient working context."""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "DELETE FROM memory_records WHERE owner_id = ? AND session_id = ? "
                "AND retention = ?",
                (user_id, session_id, RetentionRule.SESSION.value),
            )
        return cursor.rowcount

    @staticmethod
    def _deserialize(row: sqlite3.Row) -> MemoryRecordType:
        common = dict(
            id=row["id"], owner_id=row["owner_id"], source=row["source"],
            created_at=datetime.fromisoformat(row["created_at"]),
            sensitivity=Sensitivity(row["sensitivity"]),
            retention=RetentionRule(row["retention"]),
        )
        payload = json.loads(row["payload"])
        if row["kind"] == "short_term":
            return ShortTermContext(**common, session_id=row["session_id"], content=payload)
        if row["kind"] == "user_memory":
            return LongTermUserMemory(**common, content=payload)
        if row["kind"] == "project_fact":
            return ProjectFact(**common, project_id=row["project_id"], content=payload)
        return AuditEvent(**common, project_id=row["project_id"], action=row["action"], details=payload)

    @staticmethod
    def _export_record(record: MemoryRecordType) -> dict[str, Any]:
        result = asdict(record)
        result["created_at"] = record.created_at.isoformat()
        result["sensitivity"] = record.sensitivity.value
        result["retention"] = record.retention.value
        result["kind"] = next(name for name, model in _KINDS.items() if isinstance(record, model))
        return result

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SQLiteMemoryStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
