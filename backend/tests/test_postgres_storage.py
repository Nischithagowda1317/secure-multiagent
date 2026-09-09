from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine

from app.services.postgres import create_postgres_engine, validate_schema
from app.services.postgres_runtime_store import PostgresRuntimeStore, _Connection
from app.services.runtime_store import RuntimeStore
from app.settings import settings


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_supabase_url_normalization(scheme):
    with patch("sqlalchemy.create_engine") as factory:
        create_postgres_engine(f"{scheme}://postgres.project:p%40ss@aws-0-region.pooler.supabase.com:6543/postgres")
    url = factory.call_args.args[0]
    assert url.drivername == "postgresql+psycopg"
    assert url.password == "p@ss"
    assert url.query["sslmode"] == "require"
    assert factory.call_args.kwargs["connect_args"]["prepare_threshold"] is None


def test_supabase_rejects_plaintext_and_placeholder_connections():
    with pytest.raises(ValueError, match="sslmode"):
        create_postgres_engine("postgresql://postgres:password@db.example.supabase.co/postgres?sslmode=disable")
    with pytest.raises(ValueError, match="Set DATABASE_URL"):
        create_postgres_engine("postgresql://postgres:YOUR_PASSWORD@YOUR_HOST/postgres")
    with pytest.raises(ValueError, match="identifier"):
        validate_schema('enterprise_ai"; DROP SCHEMA public; --')


@pytest.mark.parametrize("backend,expected", [("csv", "sqlite"), ("supabase", "postgres"), ("postgres", "postgres")])
def test_runtime_follows_data_backend(backend, expected):
    config = replace(settings, data_backend=backend, runtime_backend="auto")
    assert config.resolved_runtime_backend == expected


class AdapterStore(PostgresRuntimeStore):
    """Exercise runtime SQL and transaction semantics locally via SQLAlchemy.

    PostgreSQL search_path and advisory locks require a live server and are not
    emulated by these adapter contract tests.
    """
    @contextmanager
    def connect(self):
        with self.engine.begin() as connection:
            yield _Connection(connection)

    def _lock_approval_transaction(self, connection):
        pass


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "runtime.db"
    sqlite_store = RuntimeStore(path)
    store = AdapterStore.__new__(AdapterStore)
    store._lock = sqlite_store._lock
    store.engine = create_engine(f"sqlite:///{path.as_posix()}")
    yield store
    store.engine.dispose()


def approval(store, target="E002"):
    return store.create_approval(
        request_type="Task Reassignment", business_object_type="task",
        business_object_id="T001", requested_action="Reassign", risk_tier="High",
        required_roles=["Project Manager"], requested_by="U001",
        payload={"reassignment_plan": {"task_id": "T001", "source_employee_id": "E001", "target_employee_id": target}},
    )


def test_runtime_bound_values_and_json_roundtrip(store):
    message = "What's next? '; DROP TABLE audit_events; -- :p0 %s"
    store.add_audit("U001", "test", None, None, None, {"message": message})
    assert store.recent_audit(1)[0]["details_json"] == {"message": message}
    store.save_chat("U001", "W001", message, {"answer": message})
    with store.connect() as connection:
        row = connection.execute("SELECT * FROM chat_history WHERE user_id = ?", ("U001",)).fetchone()
    assert store._row(row)["response_json"] == {"answer": message}
    document = store.add_uploaded_document(
        title=message, filename="file.txt", classification="Internal",
        allowed_roles=["Employee"], required_permission="read", stored_path="file.txt",
        extracted_text_path="text.txt", chunk_count=1, uploaded_by="U001",
    )
    assert store.list_uploaded_documents()[0]["allowed_roles"] == ["Employee"]
    assert store.get_uploaded_document(document["document_id"])["title"] == message


def test_reassignment_commit_replay_and_stale_plan(store):
    first = approval(store)
    stale = approval(store, "E003")
    args = dict(resolved_by="U002", comment="Approved", base_assignee_employee_id="E001")
    assert store.execute_task_reassignment(first["approval_id"], **args)[1] == "executed"
    assert store.execute_task_reassignment(first["approval_id"], **args)[1] == "not_pending"
    assert store.execute_task_reassignment(stale["approval_id"], **args)[1] == "stale"
    assert store.task_assignment_overrides() == {"T001": "E002"}
    assert len(store.recent_audit()) == 2


def test_reassignment_audit_failure_rolls_back_every_write(store, monkeypatch):
    record = approval(store)
    def fail(*args, **kwargs):
        raise RuntimeError("Audit write failed")
    monkeypatch.setattr(store, "_insert_audit", fail)
    with pytest.raises(RuntimeError, match="Audit write failed"):
        store.execute_task_reassignment(record["approval_id"], resolved_by="U002", comment="Approved", base_assignee_employee_id="E001")
    assert store.task_assignment_overrides() == {}
    assert store.get_approval(record["approval_id"])["status"] == "Pending"


def test_decision_cannot_overwrite_resolved_approval(store):
    record = approval(store)
    assert store.decide_approval(record["approval_id"], "Rejected", "U002", "No")["status"] == "Rejected"
    assert store.decide_approval(record["approval_id"], "Approved", "U002", "Retry") is None
