"""Data contracts for the deliberately separate Trinity memory domains."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4


class Sensitivity(StrEnum):
    """Classification used by policy and export tooling."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class RetentionRule(StrEnum):
    """Supported retention schedules.

    ``SESSION`` is removed when a session is cleared, while the dated policies are
    also enforced lazily by the local store before every operation.
    """

    SESSION = "session"
    DAYS_30 = "30_days"
    DAYS_365 = "365_days"
    INDEFINITE = "indefinite"

    def expires_at(self, created_at: datetime) -> datetime | None:
        days = {self.DAYS_30: 30, self.DAYS_365: 365}.get(self)
        return created_at + timedelta(days=days) if days is not None else None


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, kw_only=True)
class MemoryRecord:
    """Fields that every persisted memory record is required to carry."""

    owner_id: str
    source: str
    sensitivity: Sensitivity
    retention: RetentionRule
    created_at: datetime = field(default_factory=utc_now)
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if not self.owner_id.strip() or not self.source.strip():
            raise ValueError("owner_id and source must not be empty")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")


@dataclass(frozen=True, kw_only=True)
class ShortTermContext(MemoryRecord):
    """Ephemeral working context for one user session."""

    session_id: str
    content: Mapping[str, Any]


@dataclass(frozen=True, kw_only=True)
class LongTermUserMemory(MemoryRecord):
    """A durable user preference or user-approved recollection."""

    content: Mapping[str, Any]


@dataclass(frozen=True, kw_only=True)
class ProjectFact(MemoryRecord):
    """A durable fact isolated to a project."""

    project_id: str
    content: Mapping[str, Any]


@dataclass(frozen=True, kw_only=True)
class AuditEvent(MemoryRecord):
    """An append-only description of a memory operation or policy event."""

    action: str
    details: Mapping[str, Any]
    project_id: str | None = None


MemoryRecordType = ShortTermContext | LongTermUserMemory | ProjectFact | AuditEvent
