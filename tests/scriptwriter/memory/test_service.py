from scriptwriter.memory.models import CharacterProfile, StoryFact, TimelineEvent, WorldRule
from scriptwriter.memory.service import MemoryConflict, MemoryService


def test_memory_service_stores_structured_entries_by_project():
    service = MemoryService()
    character = CharacterProfile(character_id="char_1", name="Lin", summary="A stubborn detective.")
    rule = WorldRule(rule_id="rule_1", description="No magic exists in this world.")
    fact = StoryFact(fact_id="fact_1", key="protagonist.profession", value="detective")
    event = TimelineEvent(event_id="event_1", description="Lin joins the task force.", order=1)

    service.add_character("project_123", character)
    service.add_world_rule("project_123", rule)
    service.add_story_fact("project_123", fact)
    service.add_timeline_event("project_123", event)

    snapshot = service.get_snapshot("project_123")
    assert snapshot.characters == [character]
    assert snapshot.world_rules == [rule]
    assert snapshot.story_facts == [fact]
    assert snapshot.timeline_events == [event]


def test_detect_fact_conflicts_when_key_value_disagree():
    service = MemoryService()
    service.add_story_fact(
        "project_123",
        StoryFact(fact_id="fact_1", key="protagonist.profession", value="detective"),
    )

    conflicts = service.detect_fact_conflicts(
        "project_123",
        [StoryFact(fact_id="fact_2", key="protagonist.profession", value="lawyer")],
    )

    assert conflicts == [
        MemoryConflict(
            key="protagonist.profession",
            existing_value="detective",
            incoming_value="lawyer",
        )
    ]


def test_detect_fact_conflicts_ignores_matching_values():
    service = MemoryService()
    service.add_story_fact(
        "project_123",
        StoryFact(fact_id="fact_1", key="protagonist.profession", value="detective"),
    )

    conflicts = service.detect_fact_conflicts(
        "project_123",
        [StoryFact(fact_id="fact_2", key="protagonist.profession", value="detective")],
    )

    assert conflicts == []
