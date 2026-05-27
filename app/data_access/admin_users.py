from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import aliased

from app.data_access.filtering import normalize_filter_values
from app.data_access.subscriptions import subscription_to_dict
from app.data_access.user_identity import get_user_by_uuid
from app.models import AclGroup, TeacherStudentLink, User, UserSubscription
from app.orm import SessionManager

ACCESS_ROLE_LABELS = {
    "student": "user",
    "admin": "admin",
    "admin_editor": "admin editor",
    "super_admin": "super admin",
}
ADMIN_ACCESS_ROLES = {"admin", "admin_editor", "super_admin"}
USER_TYPE_LABELS = {
    "admin": "Admin",
    "student": "Student",
    "teacher": "Teacher",
}


def admin_user_to_dict(
    user: User,
    acl_group_title: str | None,
    subscription: UserSubscription | dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_id = str(user.uuid) if user.uuid is not None else None
    subscription_payload = (
        subscription_to_dict(subscription)
        if isinstance(subscription, UserSubscription)
        else dict(subscription or {})
        if subscription is not None
        else None
    )
    return {
        "id": user_id,
        "user_id": user_id,
        "telegram_user_id": user.telegram_user_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "language_code": user.language_code,
        "interface_locale": user.interface_locale,
        "admin_web_password_prompted": user.admin_web_password_prompted,
        "status": user.status,
        "learning_role": getattr(user, "learning_role", "student") or "student",
        "chat_id": user.chat_id,
        "acl_group_title": acl_group_title,
        "subscription": subscription_payload,
        "subscription_plan_key": subscription_payload.get("plan_key") if subscription_payload else None,
        "subscription_status": subscription_payload.get("status") if subscription_payload else None,
        "subscription_end": subscription_payload.get("end") if subscription_payload else None,
        "trial_end": subscription_payload.get("trial_end") if subscription_payload else None,
        "payment_required": subscription_payload.get("payment_required") if subscription_payload else False,
        "payment_due_at": subscription_payload.get("payment_due_at") if subscription_payload else None,
        "payment_reason": subscription_payload.get("payment_reason") if subscription_payload else None,
        "created": user.created,
        "updated": user.updated,
    }


def _unpack_user_row(row) -> tuple[User, str | None, UserSubscription | dict[str, Any] | None]:
    if len(row) == 2:
        user, acl_group_title = row
        return user, acl_group_title, None
    user, acl_group_title, subscription = row
    return user, acl_group_title, subscription


def student_link_to_dict(
    link: TeacherStudentLink,
    student: User,
    acl_group_title: str | None,
    subscription: UserSubscription | dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = admin_user_to_dict(student, acl_group_title, subscription)
    return {
        "link_id": link.id,
        "link_status": link.status,
        "user_id": payload["user_id"],
        "first_name": payload["first_name"],
        "last_name": payload["last_name"],
        "username": payload["username"],
        "language_code": payload["language_code"],
        "interface_locale": payload["interface_locale"],
        "status": payload["status"],
        "learning_role": payload["learning_role"],
        "acl_group_title": payload["acl_group_title"],
        "subscription_plan_key": payload["subscription_plan_key"],
    }


class AdminUserRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def get_by_id(self, user_id: str | int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            if isinstance(user_id, str) and "-" in user_id:
                user = get_user_by_uuid(session, user_id)
                if user is None:
                    return None
                row = session.execute(
                    select(User, AclGroup.title, UserSubscription)
                    .join(AclGroup, AclGroup.id == User.acl_group_id)
                    .outerjoin(UserSubscription, UserSubscription.user_uuid == User.uuid)
                    .where(User.uuid == user.uuid)
                    .limit(1)
                ).first()
                if row is None:
                    return None
                user, acl_group_title, subscription = _unpack_user_row(row)
                return admin_user_to_dict(user, acl_group_title, subscription)
            telegram_user_id = int(user_id)
            row = session.execute(
                select(User, AclGroup.title, UserSubscription)
                .join(AclGroup, AclGroup.id == User.acl_group_id)
                .outerjoin(UserSubscription, UserSubscription.user_uuid == User.uuid)
                .where(User.telegram_user_id == telegram_user_id)
                .limit(1)
            ).first()
            if row is None:
                return None
            user, acl_group_title, subscription = _unpack_user_row(row)
            return admin_user_to_dict(user, acl_group_title, subscription)

    def get_login_by_username(self, normalized_username: str) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            rows = session.execute(
                select(User, AclGroup.title, UserSubscription)
                .join(AclGroup, AclGroup.id == User.acl_group_id)
                .outerjoin(UserSubscription, UserSubscription.user_uuid == User.uuid)
                .where(func.lower(User.username) == normalized_username, User.status == "active")
                .order_by(User.telegram_user_id.asc())
                .limit(2)
            ).all()
            if len(rows) != 1:
                return None
            user, acl_group_title, subscription = _unpack_user_row(rows[0])
            return admin_user_to_dict(user, acl_group_title, subscription)

    def get_filter_metadata(self) -> dict[str, Any]:
        with self.session_manager.session() as session:
            groups = session.scalars(select(AclGroup).order_by(AclGroup.title.asc())).all()
            role_options = [
                {"value": row.title, "label": ACCESS_ROLE_LABELS[row.title]}
                for row in groups
                if row.title in ACCESS_ROLE_LABELS
            ]
            return {
                "entity": "users",
                "page_sizes": [50, 100],
                "filters": [
                    {"name": "search", "type": "text", "label": "Пошук"},
                    {
                        "name": "user_type",
                        "type": "single_select",
                        "label": "User type",
                        "options": [
                            {"value": value, "label": label}
                            for value, label in USER_TYPE_LABELS.items()
                        ],
                    },
                    {
                        "name": "role",
                        "type": "multi_select",
                        "label": "Role",
                        "options": role_options,
                    },
                    {
                        "name": "status",
                        "type": "multi_select",
                        "label": "Status",
                        "options": [
                            {"value": "active", "label": "active"},
                            {"value": "inactive", "label": "inactive"},
                            {"value": "blocked", "label": "blocked"},
                            {"value": "archived", "label": "archived"},
                        ],
                    },
                ],
            }

    def list_admin(
        self,
        *,
        page: int,
        page_size: int,
        archived: bool,
        search: str = "",
        role: str | list[str] | None = None,
        user_type: str = "student",
        user_id: str = "",
        status: str | list[str] | None = None,
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            filters = [User.status == ("archived" if archived else "active")]
            normalized_search = search.strip().lower()
            if normalized_search:
                like_value = f"%{normalized_search}%"
                filters.append(
                    or_(
                        func.lower(User.username).like(like_value),
                        func.lower(User.first_name).like(like_value),
                        func.lower(User.last_name).like(like_value),
                    )
                )

            query = (
                select(User, AclGroup.title, UserSubscription)
                .join(AclGroup, AclGroup.id == User.acl_group_id)
                .outerjoin(UserSubscription, UserSubscription.user_uuid == User.uuid)
                .where(*filters)
            )
            count_query = (
                select(func.count(User.telegram_user_id))
                .join(AclGroup, AclGroup.id == User.acl_group_id)
                .where(*filters)
            )
            role_values = normalize_filter_values(role)
            if user_id:
                query = query.where(User.uuid == UUID(user_id))
                count_query = count_query.where(User.uuid == UUID(user_id))
            if role_values:
                query = query.where(AclGroup.title.in_(role_values))
                count_query = count_query.where(AclGroup.title.in_(role_values))
            if user_type == "admin":
                query = query.where(AclGroup.title.in_(ADMIN_ACCESS_ROLES))
                count_query = count_query.where(AclGroup.title.in_(ADMIN_ACCESS_ROLES))
            else:
                query = query.where(User.learning_role == user_type, AclGroup.title.not_in(ADMIN_ACCESS_ROLES))
                count_query = count_query.where(User.learning_role == user_type, AclGroup.title.not_in(ADMIN_ACCESS_ROLES))
            status_values = normalize_filter_values(status)
            if status_values:
                query = query.where(User.status.in_(status_values))
                count_query = count_query.where(User.status.in_(status_values))
            total = int(session.scalar(count_query) or 0)
            rows = session.execute(query.order_by(User.telegram_user_id.asc()).offset(offset).limit(page_size)).all()
            items = [
                admin_user_to_dict(user, acl_group_title, subscription)
                for user, acl_group_title, subscription in (_unpack_user_row(row) for row in rows)
            ]
            if user_type == "teacher" and items:
                students_by_teacher = self._list_students_for_teachers(
                    session,
                    teacher_user_ids=[item["user_id"] for item in items if item.get("user_id")],
                )
                for item in items:
                    item["students"] = students_by_teacher.get(item["user_id"], [])
            return {
                "items": items,
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def _list_students_for_teachers(self, session, *, teacher_user_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        teacher_uuids = [UUID(user_id) for user_id in teacher_user_ids]
        if not teacher_uuids:
            return {}

        student = aliased(User)
        student_acl = aliased(AclGroup)
        rows = session.execute(
            select(TeacherStudentLink, student, student_acl.title, UserSubscription)
            .join(student, student.uuid == TeacherStudentLink.student_user_uuid)
            .join(student_acl, student_acl.id == student.acl_group_id)
            .outerjoin(UserSubscription, UserSubscription.user_uuid == student.uuid)
            .where(
                TeacherStudentLink.teacher_user_uuid.in_(teacher_uuids),
                TeacherStudentLink.status == "active",
            )
            .order_by(TeacherStudentLink.teacher_user_uuid.asc(), student.telegram_user_id.asc())
        ).all()
        grouped: dict[str, list[dict[str, Any]]] = {str(teacher_uuid): [] for teacher_uuid in teacher_uuids}
        for link, linked_student, acl_group_title, subscription in rows:
            grouped.setdefault(str(link.teacher_user_uuid), []).append(
                student_link_to_dict(link, linked_student, acl_group_title, subscription)
            )
        return grouped

    def set_acl_group_by_title(
        self,
        user_id: str,
        role: str,
        *,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user = get_user_by_uuid(session, user_id)
            group = session.scalar(select(AclGroup).where(AclGroup.title == role).limit(1))
            if user is None or group is None:
                return None
            user.acl_group_id = group.id
            user.updated = current_time
            session.flush()
            return admin_user_to_dict(user, group.title)

    def set_learning_role(
        self,
        user_id: str,
        learning_role: str,
        *,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user = get_user_by_uuid(session, user_id)
            if user is None:
                return None
            row = session.execute(
                select(User, AclGroup.title, UserSubscription)
                .join(AclGroup, AclGroup.id == User.acl_group_id)
                .outerjoin(UserSubscription, UserSubscription.user_uuid == User.uuid)
                .where(User.uuid == user.uuid)
                .limit(1)
            ).first()
            if row is None:
                return None
            user, acl_group_title, subscription = _unpack_user_row(row)
            user.learning_role = learning_role
            user.updated = current_time
            session.flush()
            return admin_user_to_dict(user, acl_group_title, subscription)

    def set_status(self, user_id: str, status: str, *, current_time: datetime) -> bool:
        with self.session_manager.session() as session:
            user = get_user_by_uuid(session, user_id)
            if user is None:
                return False
            user.status = status
            user.updated = current_time
            return True

    def delete(self, user_id: str) -> bool:
        with self.session_manager.session() as session:
            user = get_user_by_uuid(session, user_id)
            if user is None:
                return False
            session.delete(user)
            return True
