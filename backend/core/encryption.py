"""
AES-256-GCM encryption for API keys stored in Supabase.

The 32-byte key is read from the API_KEYS_ENCRYPTION_KEY env var (hex-encoded).
Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
"""

import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_ENV_KEY_NAME = "API_KEYS_ENCRYPTION_KEY"

_cached_key: bytes | None = None


def _get_key() -> bytes:
    global _cached_key
    if _cached_key is not None:
        return _cached_key
    raw = os.environ.get(_ENV_KEY_NAME, "").strip()
    if not raw:
        raise RuntimeError(
            f"{_ENV_KEY_NAME} is not set. "
            'Generate one: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    key = bytes.fromhex(raw)
    if len(key) != 32:
        raise RuntimeError(f"{_ENV_KEY_NAME} must be exactly 32 bytes (64 hex chars)")
    _cached_key = key
    return key


def encrypt_api_key(plaintext: str) -> bytes:
    """Encrypt a plaintext API key → bytes (nonce‖ciphertext) suitable for bytea."""
    key = _get_key()
    nonce = secrets.token_bytes(12)  # 96-bit nonce for AES-GCM
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    return nonce + ciphertext


def decrypt_api_key(blob: bytes) -> str:
    """Decrypt bytes (nonce‖ciphertext) back to plaintext API key."""
    key = _get_key()
    if len(blob) < 13:
        raise ValueError("Encrypted blob too short")
    nonce, ciphertext = blob[:12], blob[12:]
    return AESGCM(key).decrypt(nonce, ciphertext, None).decode()


def make_key_prefix(plaintext: str, visible: int = 4) -> str:
    """Return a masked prefix like 'sk_l••••••••' for display."""
    if len(plaintext) <= visible:
        return "•" * len(plaintext)
    return plaintext[:visible] + "•" * min(len(plaintext) - visible, 8)
