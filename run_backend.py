#!/usr/bin/env python3
"""
Entry point to run the FastAPI backend. Used by Tauri to spawn the server.
Run from project root: python run_backend.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )
