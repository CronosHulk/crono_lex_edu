from __future__ import annotations

import pytest

from app.application.admin.ai_usage.errors import AdminAIUsageReadValidationError
from app.application.admin.ai_usage.read_service import AdminAIUsageReadService
from app.time_utils import TimeService
from tests.test_admin_service import FakeAdminDb, build_pending_row

ACTOR = {"telegram_user_id": 1, "acl_group_title": "admin"}


def test_ai_usage_service_rejects_invalid_session_pagination() -> None:
    service = AdminAIUsageReadService(FakeAdminDb(build_pending_row()), TimeService("Europe/Kyiv"))

    with pytest.raises(AdminAIUsageReadValidationError) as error:
        service.list_sessions(actor=ACTOR, params={"page": "1", "page_size": "25"})

    assert "page_size" in error.value.detail
