"""Retrieve and decrypt user API keys stored in Supabase."""

import string

from postgrest.exceptions import APIError

from backend.core.encryption import decrypt_api_key
from backend.core.supabase_client import get_service_postgrest


def _api_error_code_message(exc: APIError) -> tuple[str | None, str]:
    """Best-effort extract PostgREST / Postgres error code and message."""
    code = getattr(exc, "code", None)
    message = getattr(exc, "message", None) or ""
    if (code is None or not message) and exc.args:
        first = exc.args[0]
        if isinstance(first, dict):
            code = code or first.get("code")
            message = message or str(first.get("message", ""))
    return code, message or str(exc)


def _bytea_to_bytes(value) -> bytes:
    """Decode PostgREST / Postgres ``bytea`` column values to raw bytes.

    PostgREST may return ``\\x`` + hex, plain hex, raw ``bytes``, or (rarely) a
    byte array. Mis-decoding produces garbage plaintext and APIs report
    "apikey incorrect or not specified".
    """
    if value is None:
        raise ValueError("encrypted_key is missing")
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, memoryview):
        return bytes(value)
    if isinstance(value, list) and value and isinstance(value[0], int):
        return bytes(value)
    if not isinstance(value, str):
        raise TypeError(f"encrypted_key has unsupported type {type(value)!r}")

    s = value.strip()
    if not s:
        raise ValueError("encrypted_key is empty")

    # Postgres text format: \x + hex (JSON gives one backslash before x)
    if s.startswith("\\x") and len(s) > 2:
        try:
            return bytes.fromhex(s[2:])
        except ValueError:
            pass
    if s.startswith("0x") and len(s) > 2:
        try:
            return bytes.fromhex(s[2:])
        except ValueError:
            pass

    # Some clients return hex only (no prefix)
    if len(s) % 2 == 0 and all(c in string.hexdigits for c in s):
        try:
            return bytes.fromhex(s)
        except ValueError:
            pass

    # Last resort: treat as Latin-1 byte sequence (legacy / mis-encoded reads)
    return s.encode("latin-1")


def fetch_api_key(user_id: str, provider: str) -> str:
    """Fetch and decrypt a user's API key for the given provider.

    Raises ValueError if no key is found or decryption yields an empty string.
    If the database enum does not include ``provider`` (Postgres 22P02), raises
    ValueError so callers like Binance can fall back to unauthenticated access.
    """
    db = get_service_postgrest()
    try:
        resp = (
            db.from_("api_keys")
            .select("encrypted_key")
            .eq("user_id", user_id)
            .eq("provider", provider)
            .limit(1)
            .execute()
        )
    except APIError as e:
        code, msg = _api_error_code_message(e)
        msg_l = msg.lower()
        if code == "22P02" or "invalid input value for enum" in msg_l:
            raise ValueError(
                f"No {provider} API key: add value '{provider}' to api_key_provider "
                "enum (run Supabase migrations), or omit keys for public access."
            ) from e
        raise
    if not resp.data:
        raise ValueError(
            f"No {provider} API key configured. Add one in API Keys settings."
        )
    raw = resp.data[0]["encrypted_key"]
    blob = _bytea_to_bytes(raw)
    plaintext = decrypt_api_key(blob).strip()
    # Remove BOM / zero-width chars sometimes pasted from web UIs
    plaintext = plaintext.replace("\ufeff", "").replace("\u200b", "").strip()
    if not plaintext:
        raise ValueError(
            f"Stored {provider} API key decrypts to an empty value. "
            "Remove and re-save the key in API Keys."
        )
    return plaintext
