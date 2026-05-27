from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

from app.data_access.admin_users import AdminUserRepository, admin_user_to_dict
from app.models import AclGroup, TeacherStudentLink, User, UserSubscription


class FakeResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None


class FakeSession:
    def __init__(self, *, row_by_id=None, scalar_values=None, scalars_rows=None, execute_rows=None) -> None:
        self.row_by_id = row_by_id or {}
        self.scalar_values = list(scalar_values or [])
        self.scalars_rows = list(scalars_rows or [])
        self.execute_rows = list(execute_rows or [])
        self.deleted = []
        self.flushed = False

    def get(self, model, primary_key):
        return self.row_by_id.get(primary_key)

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        return FakeResult(self.scalars_rows)

    def execute(self, statement):
        return FakeResult(self.execute_rows.pop(0) if self.execute_rows else [])

    def delete(self, row) -> None:
        self.deleted.append(row)

    def flush(self) -> None:
        self.flushed = True


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_user(**overrides) -> User:
    now = datetime(2026, 4, 6, 10, 0, 0)
    values = {
        "uuid": UUID("11111111-1111-4111-8111-111111111111"),
        "telegram_user_id": 42,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "username": "ada",
        "language_code": "uk",
        "interface_locale": "uk",
        "status": "active",
        "learning_role": "student",
        "chat_id": 1001,
        "acl_group_id": 1,
        "created": now,
        "updated": now,
    }
    values.update(overrides)
    return User(**values)


def make_group(**overrides) -> AclGroup:
    values = {"id": 1, "title": "admin"}
    values.update(overrides)
    return AclGroup(**values)


def make_subscription(**overrides) -> UserSubscription:
    now = datetime(2026, 4, 6, 10, 0, 0)
    values = {
        "user_uuid": UUID("11111111-1111-4111-8111-111111111111"),
        "plan_key": "premium",
        "start": now,
        "end": None,
        "trial_start": None,
        "trial_end": None,
        "payment_required": False,
        "payment_due_at": None,
        "payment_reason": None,
        "status": "active",
        "created": now,
        "updated": now,
    }
    values.update(overrides)
    return UserSubscription(**values)


def make_teacher_student_link(**overrides) -> TeacherStudentLink:
    now = datetime(2026, 4, 6, 10, 0, 0)
    values = {
        "id": 7,
        "teacher_user_uuid": UUID("11111111-1111-4111-8111-111111111111"),
        "student_user_uuid": UUID("22222222-2222-4222-8222-222222222222"),
        "status": "active",
        "created": now,
        "updated": now,
    }
    values.update(overrides)
    return TeacherStudentLink(**values)


def test_admin_user_to_dict_serializes_admin_row() -> None:
    payload = admin_user_to_dict(make_user(), "admin", make_subscription())

    assert payload["telegram_user_id"] == 42
    assert payload["acl_group_title"] == "admin"
    assert payload["learning_role"] == "student"
    assert payload["subscription_plan_key"] == "premium"
    assert payload["subscription"]["plan_key"] == "premium"
    assert payload["payment_required"] is False
    assert payload["payment_due_at"] is None


def test_get_by_id_returns_payload_or_none() -> None:
    row = (make_user(), "admin")
    repository = AdminUserRepository(FakeSessionManager(FakeSession(execute_rows=[[row], []])))

    assert repository.get_by_id(42)["username"] == "ada"
    assert repository.get_by_id(404) is None


def test_get_login_by_username_requires_single_active_match() -> None:
    row = (make_user(), "admin")
    repository = AdminUserRepository(FakeSessionManager(FakeSession(execute_rows=[[row], [], [row, row]])))

    assert repository.get_login_by_username("ada")["telegram_user_id"] == 42
    assert repository.get_login_by_username("missing") is None
    assert repository.get_login_by_username("duplicate") is None


def test_get_filter_metadata_lists_acl_groups_and_static_statuses() -> None:
    repository = AdminUserRepository(
        FakeSessionManager(FakeSession(scalars_rows=[make_group(title="admin"), make_group(id=2, title="super_admin")]))
    )

    metadata = repository.get_filter_metadata()

    role_filter = next(row for row in metadata["filters"] if row["name"] == "role")
    status_filter = next(row for row in metadata["filters"] if row["name"] == "status")
    user_type_filter = next(row for row in metadata["filters"] if row["name"] == "user_type")
    assert [row["value"] for row in user_type_filter["options"]] == ["admin", "student", "teacher"]
    assert [row["value"] for row in role_filter["options"]] == ["admin", "super_admin"]
    assert [row["value"] for row in status_filter["options"]] == ["active", "inactive", "blocked", "archived"]


def test_list_admin_applies_pagination_and_serializes_rows() -> None:
    row = (make_user(), "admin", make_subscription())
    session = FakeSession(scalar_values=[1], execute_rows=[[row]])
    repository = AdminUserRepository(FakeSessionManager(session))

    payload = repository.list_admin(
        page=0,
        page_size=50,
        archived=False,
        search=" Ada ",
        role=["admin"],
        user_type="admin",
        status="active",
    )

    assert payload["page"] == 0
    assert payload["total"] == 1
    assert payload["pages"] == 1
    assert payload["items"][0]["username"] == "ada"
    assert payload["items"][0]["subscription_plan_key"] == "premium"


def test_list_admin_embeds_students_for_teacher_rows() -> None:
    teacher = make_user(learning_role="teacher")
    student = make_user(
        uuid=UUID("22222222-2222-4222-8222-222222222222"),
        telegram_user_id=43,
        first_name="Lin",
        last_name="Student",
        username="lin",
        acl_group_id=2,
    )
    teacher_subscription = make_subscription()
    student_subscription = make_subscription(
        user_uuid=UUID("22222222-2222-4222-8222-222222222222"),
        plan_key="premium",
    )
    link = make_teacher_student_link()
    session = FakeSession(
        scalar_values=[1],
        execute_rows=[
            [(teacher, "student", teacher_subscription)],
            [(link, student, "student", student_subscription)],
        ],
    )
    repository = AdminUserRepository(FakeSessionManager(session))

    payload = repository.list_admin(
        page=1,
        page_size=50,
        archived=False,
        user_type="teacher",
    )

    assert payload["items"][0]["learning_role"] == "teacher"
    assert payload["items"][0]["students"] == [
        {
            "link_id": 7,
            "link_status": "active",
            "user_id": "22222222-2222-4222-8222-222222222222",
            "first_name": "Lin",
            "last_name": "Student",
            "username": "lin",
            "language_code": "uk",
            "interface_locale": "uk",
            "status": "active",
            "learning_role": "student",
            "acl_group_title": "student",
            "subscription_plan_key": "premium",
        }
    ]


def test_set_acl_group_by_title_handles_missing_and_updates_user() -> None:
    current_time = datetime(2026, 4, 6, 11, 0, 0)
    user = make_user()
    group = make_group(id=2, title="super_admin")
    repository = AdminUserRepository(
        FakeSessionManager(FakeSession(scalar_values=[user, None, user, group]))
    )

    assert repository.set_acl_group_by_title(str(user.uuid), "missing", current_time=current_time) is None
    payload = repository.set_acl_group_by_title(str(user.uuid), "super_admin", current_time=current_time)

    assert payload is not None
    assert payload["acl_group_title"] == "super_admin"
    assert user.acl_group_id == 2
    assert user.updated == current_time


def test_set_status_and_delete_return_false_for_missing_user_and_mutate_existing() -> None:
    current_time = datetime(2026, 4, 6, 11, 0, 0)
    user = make_user()
    session = FakeSession(scalar_values=[None, user, None, user])
    repository = AdminUserRepository(FakeSessionManager(session))

    assert repository.set_status("22222222-2222-4222-8222-222222222222", "archived", current_time=current_time) is False
    assert repository.set_status(str(user.uuid), "archived", current_time=current_time) is True
    assert user.status == "archived"
    assert user.updated == current_time

    assert repository.delete("22222222-2222-4222-8222-222222222222") is False
    assert repository.delete(str(user.uuid)) is True
    assert session.deleted == [user]


def test_set_learning_role_handles_missing_and_updates_user() -> None:
    current_time = datetime(2026, 4, 6, 11, 0, 0)
    user = make_user()
    repository = AdminUserRepository(
        FakeSessionManager(FakeSession(scalar_values=[None, user], execute_rows=[[(user, "admin")]]))
    )

    assert repository.set_learning_role("22222222-2222-4222-8222-222222222222", "teacher", current_time=current_time) is None
    payload = repository.set_learning_role(str(user.uuid), "teacher", current_time=current_time)

    assert payload is not None
    assert payload["learning_role"] == "teacher"
    assert user.learning_role == "teacher"
    assert user.updated == current_time
