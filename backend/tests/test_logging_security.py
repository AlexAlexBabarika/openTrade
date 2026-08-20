import logging

from backend.core.logging_security import SecretRedactionFilter, redact_secrets


def test_redacts_query_keys_tokens_and_database_passwords():
    message = (
        "url=https://example.test?apikey=secret-value&symbol=AAPL "
        "Authorization: Bearer-value "
        "postgresql://user:database-password@postgres/db"
    )
    redacted = redact_secrets(message)
    assert "secret-value" not in redacted
    assert "Bearer-value" not in redacted
    assert "database-password" not in redacted
    assert redacted.count("[REDACTED]") == 3


def test_filter_redacts_formatted_log_arguments():
    record = logging.LogRecord(
        "test", logging.ERROR, __file__, 1, "token=%s", ("secret",), None
    )
    assert SecretRedactionFilter().filter(record)
    assert record.getMessage() == "token=[REDACTED]"
