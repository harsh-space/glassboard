# conftest.py — repo root
# Loads .env into the process environment BEFORE any backend module is imported,
# so that backend/auth.py sees JWT_SECRET_KEY at module-load time.
# This mirrors what uvicorn + dotenv-loaded environment does in production/local runs.
import os
from pathlib import Path

_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value
