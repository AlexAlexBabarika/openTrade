"""Retrieve and decrypt user API keys stored in Supabase."""

from backend.core.encryption import decrypt_api_key
from backend.core.supabase_client import get_service_postgrest


def fetch_api_key(user_id: str, provider: str) -> str:
    """Fetch and decrypt a user's API key for the given provider.

    Raises ValueError if no key is found.
    """
    db = get_service_postgrest()
    resp = (
        db.from_("api_keys")
        .select("encrypted_key")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise ValueError(
            f"No {provider} API key configured. Add one in API Keys settings."
        )
    raw = resp.data[0]["encrypted_key"]
    if isinstance(raw, str) and raw.startswith("\\x"):
        raw = bytes.fromhex(raw[2:])
    elif isinstance(raw, str):
        raw = raw.encode("latin-1")
    return decrypt_api_key(raw)
