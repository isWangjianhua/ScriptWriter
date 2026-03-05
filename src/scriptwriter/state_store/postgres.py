from __future__ import annotations

from uuid import uuid4

from scriptwriter.state_store.base import StateStore, StoredEvent, StoredRun, StoredSnapshot


class PostgresStateStore(StateStore):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._ensure_schema()

    def _connect(self):
        import psycopg

        return psycopg.connect(self._dsn)

    def _ensure_schema(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS agent_sessions (
            id UUID PRIMARY KEY,
            user_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (user_id, project_id)
        );

        CREATE TABLE IF NOT EXISTS agent_runs (
            id UUID PRIMARY KEY,
            session_id UUID NOT NULL REFERENCES agent_sessions(id),
            thread_id TEXT NOT NULL,
            input_message TEXT NOT NULL,
            status TEXT NOT NULL,
            current_step TEXT,
            error_code TEXT,
            error_message TEXT,
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ
        );

        CREATE TABLE IF NOT EXISTS agent_events (
            id BIGSERIAL PRIMARY KEY,
            run_id UUID NOT NULL REFERENCES agent_runs(id),
            seq_no INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            payload_jsonb JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (run_id, seq_no)
        );

        CREATE TABLE IF NOT EXISTS agent_snapshots (
            id BIGSERIAL PRIMARY KEY,
            run_id UUID NOT NULL REFERENCES agent_runs(id),
            last_seq_no INTEGER NOT NULL,
            state_jsonb JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
                cur.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS thread_id TEXT")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_thread_id ON agent_runs(thread_id)")
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_agent_events_run_seq ON agent_events(run_id, seq_no)"
                )

    def create_or_get_session(self, user_id: str, project_id: str) -> str:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM agent_sessions WHERE user_id=%s AND project_id=%s",
                    (user_id, project_id),
                )
                row = cur.fetchone()
                if row:
                    return str(row[0])
                session_id = str(uuid4())
                cur.execute(
                    "INSERT INTO agent_sessions (id, user_id, project_id, status) VALUES (%s, %s, %s, 'ACTIVE')",
                    (session_id, user_id, project_id),
                )
                return session_id

    def create_run(self, session_id: str, thread_id: str, input_message: str) -> str:
        run_id = str(uuid4())
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_runs (id, session_id, thread_id, input_message, status)
                    VALUES (%s, %s, %s, %s, 'RUNNING')
                    """,
                    (run_id, session_id, thread_id, input_message),
                )
        return run_id

    def append_event(self, run_id: str, event_type: str, agent_name: str, payload: dict) -> StoredEvent:
        from psycopg.types.json import Json

        with self._connect() as conn:
            with conn.cursor() as cur:
                # Serialize sequence allocation for this run to avoid MAX+1 races.
                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (run_id,))
                cur.execute(
                    "SELECT COALESCE(MAX(seq_no), 0) FROM agent_events WHERE run_id=%s",
                    (run_id,),
                )
                next_seq = int(cur.fetchone()[0]) + 1
                cur.execute(
                    """
                    INSERT INTO agent_events (run_id, seq_no, event_type, agent_name, payload_jsonb)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (run_id, next_seq, event_type, agent_name, Json(payload)),
                )
        return StoredEvent(
            run_id=run_id,
            seq_no=next_seq,
            event_type=event_type,
            agent_name=agent_name,
            payload=payload,
        )

    def save_snapshot(self, run_id: str, last_seq_no: int, state: dict) -> None:
        from psycopg.types.json import Json

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO agent_snapshots (run_id, last_seq_no, state_jsonb) VALUES (%s, %s, %s)",
                    (run_id, last_seq_no, Json(state)),
                )

    def get_latest_snapshot(self, run_id: str) -> StoredSnapshot | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT run_id, last_seq_no, state_jsonb
                    FROM agent_snapshots
                    WHERE run_id=%s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (run_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                state = row[2] if isinstance(row[2], dict) else {}
                return StoredSnapshot(run_id=str(row[0]), last_seq_no=int(row[1]), state=state)

    def get_events(self, run_id: str, after_seq_no: int = 0) -> list[StoredEvent]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT run_id, seq_no, event_type, agent_name, payload_jsonb
                    FROM agent_events
                    WHERE run_id=%s AND seq_no>%s
                    ORDER BY seq_no ASC
                    """,
                    (run_id, after_seq_no),
                )
                rows = cur.fetchall()
        return [
            StoredEvent(
                run_id=str(row[0]),
                seq_no=int(row[1]),
                event_type=str(row[2]),
                agent_name=str(row[3]),
                payload=dict(row[4]),
            )
            for row in rows
        ]

    def get_run(self, run_id: str) -> StoredRun | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, session_id, thread_id, input_message, status, current_step, error_code, error_message
                    FROM agent_runs
                    WHERE id=%s
                    """,
                    (run_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return StoredRun(
                    run_id=str(row[0]),
                    session_id=str(row[1]),
                    thread_id=str(row[2] or ""),
                    input_message=str(row[3]),
                    status=str(row[4]),
                    current_step=row[5],
                    error_code=row[6],
                    error_message=row[7],
                )

    def get_run_scoped(
        self,
        run_id: str,
        thread_id: str,
        user_id: str,
        project_id: str,
    ) -> StoredRun | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.id, r.session_id, r.thread_id, r.input_message, r.status, r.current_step, r.error_code, r.error_message
                    FROM agent_runs r
                    JOIN agent_sessions s ON s.id = r.session_id
                    WHERE r.id=%s AND r.thread_id=%s AND s.user_id=%s AND s.project_id=%s
                    """,
                    (run_id, thread_id, user_id, project_id),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return StoredRun(
                    run_id=str(row[0]),
                    session_id=str(row[1]),
                    thread_id=str(row[2] or ""),
                    input_message=str(row[3]),
                    status=str(row[4]),
                    current_step=row[5],
                    error_code=row[6],
                    error_message=row[7],
                )

    def mark_run_completed(self, run_id: str, current_step: str | None = None) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE agent_runs
                    SET status='COMPLETED', current_step=%s, finished_at=now()
                    WHERE id=%s
                    """,
                    (current_step, run_id),
                )

    def mark_run_failed(
        self,
        run_id: str,
        error_code: str,
        error_message: str,
        current_step: str | None = None,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE agent_runs
                    SET status='FAILED', current_step=%s, error_code=%s, error_message=%s, finished_at=now()
                    WHERE id=%s
                    """,
                    (current_step, error_code, error_message, run_id),
                )
