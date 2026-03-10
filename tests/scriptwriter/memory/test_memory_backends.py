from __future__ import annotations

from pathlib import Path

from scriptwriter.projects.memory import (
    MemoryService,
    PostgresMemoryRepository,
    RedisMemoryCache,
    StoryFact,
    create_memory_service_from_env,
)


def test_postgres_memory_repository_persists_snapshot_across_service_instances(tmp_path: Path):
    dsn = f"sqlite+pysqlite:///{tmp_path / 'memory.db'}"
    repository = PostgresMemoryRepository(dsn=dsn)

    service = MemoryService(repository=repository)
    service.add_story_fact(
        "project_1",
        StoryFact(fact_id="fact_1", key="protagonist.name", value="Lin"),
    )

    another_service = MemoryService(repository=repository)
    snapshot = another_service.get_snapshot("project_1")
    assert snapshot.story_facts == [StoryFact(fact_id="fact_1", key="protagonist.name", value="Lin")]


def test_memory_service_prefers_redis_cache_when_available():
    class _FakeRepository:
        def __init__(self):
            self.get_calls = 0
            self.save_calls = 0

        def load_snapshot(self, project_id: str):
            self.get_calls += 1
            _ = project_id
            return None

        def save_snapshot(self, project_id: str, snapshot):
            self.save_calls += 1
            _ = (project_id, snapshot)

    class _FakeCache:
        def __init__(self):
            self._store = {}
            self.get_calls = 0
            self.set_calls = 0

        def get_snapshot(self, project_id: str):
            self.get_calls += 1
            return self._store.get(project_id)

        def set_snapshot(self, project_id: str, snapshot):
            self.set_calls += 1
            self._store[project_id] = snapshot

        def invalidate(self, project_id: str):
            self._store.pop(project_id, None)

    repository = _FakeRepository()
    cache = _FakeCache()
    service = MemoryService(repository=repository, cache=cache)

    service.add_story_fact(
        "project_2",
        StoryFact(fact_id="fact_2", key="protagonist.profession", value="detective"),
    )
    assert repository.save_calls == 1
    assert cache.set_calls == 2

    service.get_snapshot("project_2")
    service.get_snapshot("project_2")
    assert repository.get_calls == 1
    assert cache.get_calls >= 2


def test_redis_memory_cache_roundtrip_with_fake_client():
    class _FakeRedis:
        def __init__(self):
            self._kv = {}

        def get(self, key: str):
            return self._kv.get(key)

        def set(self, key: str, value: str, ex: int):
            _ = ex
            self._kv[key] = value

        def delete(self, key: str):
            self._kv.pop(key, None)

    client = _FakeRedis()
    cache = RedisMemoryCache(redis_url="redis://unused", client=client, key_prefix="test:", ttl_seconds=10)
    snapshot_fact = StoryFact(fact_id="fact_3", key="genre", value="crime")

    service = MemoryService(cache=cache)
    service.add_story_fact("project_3", snapshot_fact)

    cached = cache.get_snapshot("project_3")
    assert cached is not None
    assert cached.story_facts == [snapshot_fact]


def test_create_memory_service_from_env_uses_postgres_repository(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("SCRIPTWRITER_MEMORY_PG_DSN", f"sqlite+pysqlite:///{tmp_path / 'factory.db'}")
    monkeypatch.delenv("SCRIPTWRITER_MEMORY_REDIS_URL", raising=False)

    service = create_memory_service_from_env()
    service.add_story_fact("project_4", StoryFact(fact_id="fact_4", key="tone", value="gritty"))

    snapshot = service.get_snapshot("project_4")
    assert snapshot.story_facts == [StoryFact(fact_id="fact_4", key="tone", value="gritty")]
