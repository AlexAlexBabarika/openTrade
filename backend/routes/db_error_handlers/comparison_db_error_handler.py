from backend.core.db_error_handler import DBErrorHandler
from fastapi import HTTPException, status
from postgrest.exceptions import APIError


class ComparisonDBErrorHandler(DBErrorHandler):
    def handle_db_error(self, exc: Exception, operation: str) -> HTTPException:
        if isinstance(exc, APIError):
            code = getattr(exc, "code", None) or "unknown"
            msg = getattr(exc, "message", None) or str(exc)
            self.logger.exception(
                "symbol_comparisons %s failed: code=%s msg=%r", operation, code, msg
            )
            if code == "23505":
                return HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="That comparison symbol is already attached to this main symbol.",
                )
            return HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Database error {operation} [code {code}]: {msg}",
            )
        self.logger.exception("symbol_comparisons %s failed: %s", operation, exc)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to {operation}.",
        )
