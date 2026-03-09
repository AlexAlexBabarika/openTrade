#!/usr/bin/env python3
"""
Generate SQLAlchemy/dataclass models from the running Postgres database.

Prerequisites:
  1. The DB container must be running:  docker compose up db -d
  2. Install deps:  pip install sqlacodegen[postgresql] psycopg2-binary

Usage:
  python backend/generate_models.py
"""

import os
import subprocess
import sys

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://user:password@localhost:5433/opentrade"
)

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "db_models.py")

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "sqlacodegen",
        DATABASE_URL,
        "--generator",
        "dataclasses",
    ],
    capture_output=True,
    text=True,
)

if result.returncode != 0:
    print(f"Error: {result.stderr}", file=sys.stderr)
    sys.exit(1)

with open(OUTPUT_FILE, "w") as f:
    f.write(result.stdout)

print(f"Generated models written to {OUTPUT_FILE}")
