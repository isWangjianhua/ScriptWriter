from scriptwriter.state_store.in_memory import InMemoryStateStore


def test_store_event_sequence_and_snapshot_roundtrip():
    store = InMemoryStateStore()
    session_id = store.create_or_get_session("user_1", "project_1")
    run_id = store.create_run(session_id, "thread_1", "Write a scene")

    e1 = store.append_event(run_id, "run_started", "supervisor", {"message": "Write a scene"})
    e2 = store.append_event(run_id, "planner_completed", "planner", {"delta": {"plan": [{"beat_number": 1}]}})
    assert e1.seq_no == 1
    assert e2.seq_no == 2

    store.save_snapshot(run_id, e2.seq_no, {"plan": [{"beat_number": 1}], "revision_count": 0})

    snapshot = store.get_latest_snapshot(run_id)
    assert snapshot is not None
    assert snapshot.last_seq_no == 2
    assert snapshot.state["plan"][0]["beat_number"] == 1


def test_store_returns_events_after_snapshot_seq():
    store = InMemoryStateStore()
    session_id = store.create_or_get_session("user_1", "project_1")
    run_id = store.create_run(session_id, "thread_1", "Write a scene")
    store.append_event(run_id, "run_started", "supervisor", {})
    store.append_event(run_id, "planner_completed", "planner", {"delta": {"plan": [{"beat_number": 1}]}})
    store.save_snapshot(run_id, 2, {"plan": [{"beat_number": 1}]})
    store.append_event(run_id, "writer_draft_produced", "writer", {"delta": {"current_draft": "draft"}})

    pending = store.get_events(run_id, after_seq_no=2)
    assert len(pending) == 1
    assert pending[0].event_type == "writer_draft_produced"


def test_store_enforces_scoped_run_lookup():
    store = InMemoryStateStore()
    session_id = store.create_or_get_session("user_1", "project_1")
    run_id = store.create_run(session_id, "thread_1", "Write a scene")

    assert store.get_run_scoped(run_id, "thread_1", "user_1", "project_1") is not None
    assert store.get_run_scoped(run_id, "thread_2", "user_1", "project_1") is None
    assert store.get_run_scoped(run_id, "thread_1", "user_2", "project_1") is None
