from backend.core.db_error_handler import DBErrorHandler
from fastapi import HTTPException, status
from backend.core.database import DatabaseError


class TickerWorkspaceDBErrorHandler(DBErrorHandler):
    def handle_db_error(self, exc: Exception, operation: str) -> HTTPException:
        if isinstance(exc, DatabaseError):
            code = getattr(exc, "code", None) or "unknown"
            msg = getattr(exc, "message", None) or str(exc)
            return HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Database error {operation} [code {code}]: {msg}",
            )
        self.logger.exception("Ticker workspace %s failed", operation)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to {operation}.",
        )
