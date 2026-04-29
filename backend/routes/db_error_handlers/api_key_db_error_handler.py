from backend.core.db_error_handler import DBErrorHandler
from fastapi import HTTPException, status
from postgrest.exceptions import APIError


class ApiKeyDBErrorHandler(DBErrorHandler):
    def handle_db_error(self, exc: Exception, operation: str) -> HTTPException:
        """
        Map PostgREST/encryption errors to HTTPException with actionable detail.
        Logs full error for debugging.
        """
        if isinstance(exc, APIError):
            code = getattr(exc, "code", None) or "unknown"
            msg = getattr(exc, "message", None) or str(exc)
            hint = getattr(exc, "hint", None)
            details = getattr(exc, "details", None)
            self.logger.exception(
                "API key %s failed: code=%s message=%r hint=%r details=%r",
                operation,
                code,
                msg,
                hint,
                details,
            )
            # Map known Postgres/PostgREST codes to user-facing messages (include code for debugging)
            code_suffix = f" [code {code}]" if code else ""
            if code == "42501":
                detail = f"Permission denied: {msg}. Ensure your session is valid and try again.{code_suffix}"
            elif code == "23503":
                detail = f"Referenced user or resource not found.{code_suffix}"
            elif code == "23505":
                detail = f"Duplicate entry: {msg}{code_suffix}"
            elif code == "42P01":
                detail = f"Database schema issue. {code_suffix}"
            elif str(code).startswith("PGRST"):
                detail = f"Request error: {msg}{code_suffix}"
            else:
                detail = f"{msg}" + (f" ({hint})" if hint else "") + code_suffix
            return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
        if isinstance(exc, RuntimeError) and "API_KEYS_ENCRYPTION_KEY" in str(exc):
            self.logger.exception(
                "API key %s failed: encryption not configured", operation
            )
            return HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API key storage is not configured.",
            )
        self.logger.exception("API key %s failed: %s", operation, exc)
        # Never expose internal exception details to the client.
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to {operation}.",
        )
