"""Bounded reads for user-supplied uploads."""

from fastapi import HTTPException, UploadFile, status

from backend.core.config import security_settings


async def read_upload(file: UploadFile) -> bytes:
    limit = security_settings().max_upload_bytes
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Upload exceeds the {limit // (1024 * 1024)} MiB limit",
        )
    return content
