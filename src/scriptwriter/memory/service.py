from __future__ import annotations

from pydantic import BaseModel, Field

from scriptwriter.memory.models import CharacterProfile, StoryFact, TimelineEvent, WorldRule


class MemoryConflict(BaseModel):
    key: str
    existing_value: str
    incoming_value: str


class MemorySnapshot(BaseModel):
    characters: list[CharacterProfile] = Field(default_factory=list)
    world_rules: list[WorldRule] = Field(default_factory=list)
    story_facts: list[StoryFact] = Field(default_factory=list)
    timeline_events: list[TimelineEvent] = Field(default_factory=list)


class MemoryService:
    def __init__(self) -> None:
        self._snapshots: dict[str, MemorySnapshot] = {}

    def add_character(self, project_id: str, character: CharacterProfile) -> CharacterProfile:
        snapshot = self._get_or_create_snapshot(project_id)
        snapshot.characters.append(character)
        return character

    def add_world_rule(self, project_id: str, rule: WorldRule) -> WorldRule:
        snapshot = self._get_or_create_snapshot(project_id)
        snapshot.world_rules.append(rule)
        return rule

    def add_story_fact(self, project_id: str, fact: StoryFact) -> StoryFact:
        snapshot = self._get_or_create_snapshot(project_id)
        snapshot.story_facts.append(fact)
        return fact

    def add_timeline_event(self, project_id: str, event: TimelineEvent) -> TimelineEvent:
        snapshot = self._get_or_create_snapshot(project_id)
        snapshot.timeline_events.append(event)
        return event

    def get_snapshot(self, project_id: str) -> MemorySnapshot:
        snapshot = self._snapshots.get(project_id)
        if snapshot is None:
            return MemorySnapshot()
        return snapshot.model_copy(deep=True)

    def detect_fact_conflicts(self, project_id: str, facts: list[StoryFact]) -> list[MemoryConflict]:
        snapshot = self._snapshots.get(project_id)
        if snapshot is None:
            return []

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

    def _get_or_create_snapshot(self, project_id: str) -> MemorySnapshot:
        return self._snapshots.setdefault(project_id, MemorySnapshot())
