#!/usr/bin/env python3
"""
Entry point to run the FastAPI backend.
Run from project root: python run_backend.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
