from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, MetaData, String, Table, Text, create_engine, insert, select, update
from sqlalchemy.engine import Engine


class CharacterProfile(BaseModel):
    character_id: str
    name: str
    summary: str
    traits: list[str] = Field(default_factory=list)


class WorldRule(BaseModel):
    rule_id: str
    description: str


class StoryFact(BaseModel):
    fact_id: str
    key: str
    value: str
    source_version_id: str | None = None


class TimelineEvent(BaseModel):
    event_id: str
    description: str
    order: int


class MemoryConflict(BaseModel):
    key: str
    existing_value: str
    incoming_value: str


class MemorySnapshot(BaseModel):
    characters: list[CharacterProfile] = Field(default_factory=list)
    world_rules: list[WorldRule] = Field(default_factory=list)
    story_facts: list[StoryFact] = Field(default_factory=list)
    timeline_events: list[TimelineEvent] = Field(default_factory=list)


@runtime_checkable
class MemoryRepository(Protocol):
    def load_snapshot(self, project_id: str) -> MemorySnapshot | None:
        ...

    def save_snapshot(self, project_id: str, snapshot: MemorySnapshot) -> None:
        ...


@runtime_checkable
class MemoryCache(Protocol):
    def get_snapshot(self, project_id: str) -> MemorySnapshot | None:
        ...

    def set_snapshot(self, project_id: str, snapshot: MemorySnapshot) -> None:
        ...

    def invalidate(self, project_id: str) -> None:
        ...


class InMemoryMemoryRepository(MemoryRepository):
    def __init__(self) -> None:
        self._snapshots: dict[str, MemorySnapshot] = {}

    def load_snapshot(self, project_id: str) -> MemorySnapshot | None:
        snapshot = self._snapshots.get(project_id)
        if snapshot is None:
            return None
        return snapshot.model_copy(deep=True)

    def save_snapshot(self, project_id: str, snapshot: MemorySnapshot) -> None:
        self._snapshots[project_id] = snapshot.model_copy(deep=True)


_MEMORY_METADATA = MetaData()
_PROJECT_MEMORY = Table(
    "project_memory_snapshots",
    _MEMORY_METADATA,
    Column("project_id", String, primary_key=True),
    Column("snapshot_json", Text, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


def _normalize_sqlalchemy_dsn(dsn: str) -> str:
    normalized = dsn.strip()
    if normalized.startswith("postgresql+asyncpg://"):
        return normalized.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if normalized.startswith("postgres://"):
        return normalized.replace("postgres://", "postgresql+psycopg://", 1)
    if normalized.startswith("postgresql://"):
        return normalized.replace("postgresql://", "postgresql+psycopg://", 1)
    return normalized


class PostgresMemoryRepository(MemoryRepository):
    def __init__(self, *, dsn: str) -> None:
        self._engine: Engine = create_engine(_normalize_sqlalchemy_dsn(dsn), future=True, pool_pre_ping=True)
        _MEMORY_METADATA.create_all(self._engine, checkfirst=True)

    def load_snapshot(self, project_id: str) -> MemorySnapshot | None:
        stmt = select(_PROJECT_MEMORY.c.snapshot_json).where(_PROJECT_MEMORY.c.project_id == project_id)
        with self._engine.connect() as conn:
            row = conn.execute(stmt).first()
        if row is None:
            return None
        return MemorySnapshot.model_validate_json(str(row._mapping["snapshot_json"]))

    def save_snapshot(self, project_id: str, snapshot: MemorySnapshot) -> None:
        now = datetime.now(UTC)
        payload = snapshot.model_dump_json()
        with self._engine.begin() as conn:
            updated = conn.execute(
                update(_PROJECT_MEMORY)
                .where(_PROJECT_MEMORY.c.project_id == project_id)
                .values(snapshot_json=payload, updated_at=now)
            )
            if not updated.rowcount:
                conn.execute(
                    insert(_PROJECT_MEMORY).values(
                        project_id=project_id,
                        snapshot_json=payload,
                        updated_at=now,
                    )
                )


class RedisMemoryCache(MemoryCache):
    def __init__(
        self,
        *,
        redis_url: str,
        key_prefix: str = "scriptwriter:memory:",
        ttl_seconds: int = 3600,
        client: object | None = None,
    ) -> None:
        self._key_prefix = key_prefix
        self._ttl_seconds = max(ttl_seconds, 1)
        if client is None:
            from redis import Redis

            self._client = Redis.from_url(redis_url, decode_responses=True)
        else:
            self._client = client

    def get_snapshot(self, project_id: str) -> MemorySnapshot | None:
        payload = self._client.get(self._key(project_id))
        if not payload:
            return None
        return MemorySnapshot.model_validate_json(str(payload))

    def set_snapshot(self, project_id: str, snapshot: MemorySnapshot) -> None:
        self._client.set(self._key(project_id), snapshot.model_dump_json(), ex=self._ttl_seconds)

    def invalidate(self, project_id: str) -> None:
        self._client.delete(self._key(project_id))

    def _key(self, project_id: str) -> str:
        return f"{self._key_prefix}{project_id}"


class MemoryService:
    def __init__(self, repository: MemoryRepository | None = None, cache: MemoryCache | None = None) -> None:
        self._repository = repository or InMemoryMemoryRepository()
        self._cache = cache

    def add_character(self, project_id: str, character: CharacterProfile) -> CharacterProfile:
        snapshot = self._load_snapshot(project_id)
        snapshot.characters.append(character)
        self._save_snapshot(project_id, snapshot)
        return character

    def add_world_rule(self, project_id: str, rule: WorldRule) -> WorldRule:
        snapshot = self._load_snapshot(project_id)
        snapshot.world_rules.append(rule)
        self._save_snapshot(project_id, snapshot)
        return rule

    def add_story_fact(self, project_id: str, fact: StoryFact) -> StoryFact:
        snapshot = self._load_snapshot(project_id)
        snapshot.story_facts.append(fact)
        self._save_snapshot(project_id, snapshot)
        return fact

    def add_timeline_event(self, project_id: str, event: TimelineEvent) -> TimelineEvent:
        snapshot = self._load_snapshot(project_id)
        snapshot.timeline_events.append(event)
        self._save_snapshot(project_id, snapshot)
        return event

    def get_snapshot(self, project_id: str) -> MemorySnapshot:
        return self._load_snapshot(project_id).model_copy(deep=True)

    def detect_fact_conflicts(self, project_id: str, facts: list[StoryFact]) -> list[MemoryConflict]:
        snapshot = self._load_snapshot(project_id)

        existing = {fact.key: fact.value for fact in snapshot.story_facts}
        conflicts: list[MemoryConflict] = []
        for fact in facts:
            existing_value = existing.get(fact.key)
            if existing_value is not None and existing_value != fact.value:
                conflicts.append(
                    MemoryConflict(
                        key=fact.key,
                        existing_value=existing_value,
                        incoming_value=fact.value,
                    )
                )
        return conflicts

    def _load_snapshot(self, project_id: str) -> MemorySnapshot:
        if self._cache is not None:
            cached = self._cache.get_snapshot(project_id)
            if cached is not None:
                return cached.model_copy(deep=True)

        stored = self._repository.load_snapshot(project_id)
        snapshot = stored.model_copy(deep=True) if stored is not None else MemorySnapshot()

        if self._cache is not None:
            self._cache.set_snapshot(project_id, snapshot.model_copy(deep=True))
        return snapshot

    def _save_snapshot(self, project_id: str, snapshot: MemorySnapshot) -> None:
        stored = snapshot.model_copy(deep=True)
        self._repository.save_snapshot(project_id, stored)
        if self._cache is not None:
            self._cache.set_snapshot(project_id, stored.model_copy(deep=True))


def create_memory_service_from_env() -> MemoryService:
    pg_dsn = os.getenv("SCRIPTWRITER_MEMORY_PG_DSN", "").strip()
    redis_url = os.getenv("SCRIPTWRITER_MEMORY_REDIS_URL", "").strip()
    redis_key_prefix = os.getenv("SCRIPTWRITER_MEMORY_REDIS_PREFIX", "scriptwriter:memory:").strip() or "scriptwriter:memory:"
    ttl_raw = os.getenv("SCRIPTWRITER_MEMORY_REDIS_TTL_SECONDS", "3600").strip() or "3600"
    redis_ttl = int(ttl_raw)

    repository: MemoryRepository
    if pg_dsn:
        repository = PostgresMemoryRepository(dsn=pg_dsn)
    else:
        repository = InMemoryMemoryRepository()

    cache: MemoryCache | None = None
    if redis_url:
        cache = RedisMemoryCache(
            redis_url=redis_url,
            key_prefix=redis_key_prefix,
            ttl_seconds=redis_ttl,
        )
    return MemoryService(repository=repository, cache=cache)
