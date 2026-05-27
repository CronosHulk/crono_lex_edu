from __future__ import annotations


class ClientWebTeacherStudentError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ClientWebTeacherStudentValidationError(ClientWebTeacherStudentError):
    pass


class ClientWebTeacherStudentForbiddenError(ClientWebTeacherStudentError):
    pass


class ClientWebTeacherStudentNotFoundError(ClientWebTeacherStudentError):
    pass


class ClientWebTeacherStudentConflictError(ClientWebTeacherStudentError):
    pass


class ClientWebTeacherStudentUpstreamError(ClientWebTeacherStudentError):
    pass


class ClientWebTeacherStudentConfigurationError(ClientWebTeacherStudentError):
    pass
