from __future__ import annotations


class ApiError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        error_class: str,
        retryable: bool,
        http_status: int,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.error_class = error_class
        self.retryable = retryable
        self.http_status = http_status
