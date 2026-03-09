from __future__ import annotations

from pydantic import BaseModel, Field


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
