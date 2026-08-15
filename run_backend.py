#!/usr/bin/env python3
"""
Entry point to run the FastAPI backend.
Run from project root: python run_backend.py
"""

import uvicorn

from backend.core.config import security_settings

if __name__ == "__main__":
    settings = security_settings()
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        ws_max_size=settings.ws_max_message_bytes,
        timeout_graceful_shutdown=30,
    )
