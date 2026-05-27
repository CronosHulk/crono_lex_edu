from __future__ import annotations


class AdminDashboardError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminDashboardAccessDeniedError(AdminDashboardError):
    pass


class AdminDashboardNotFoundError(AdminDashboardError):
    pass


class AdminDashboardUserNotFoundError(AdminDashboardNotFoundError):
    def __init__(self) -> None:
        super().__init__("User not found")


class AdminDashboardActiveAssignmentNotFoundError(AdminDashboardNotFoundError):
    def __init__(self) -> None:
        super().__init__("Active teacher assignment not found")


class AdminDashboardValidationError(AdminDashboardError):
    pass


class AdminDashboardSameUserError(AdminDashboardValidationError):
    def __init__(self) -> None:
        super().__init__("Teacher and student must be different users")


class AdminDashboardTeacherRoleError(AdminDashboardValidationError):
    def __init__(self) -> None:
        super().__init__("Teacher user must have teacher learning role")


class AdminDashboardStudentRoleError(AdminDashboardValidationError):
    def __init__(self) -> None:
        super().__init__("Student user must have student learning role")
