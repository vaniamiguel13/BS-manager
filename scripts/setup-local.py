#!/usr/bin/env python3
"""Create a private local configuration without printing credentials or overwriting files."""
import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
content = (root / ".env.example").read_text()
for key in ("SECRET_KEY", "POSTGRES_OWNER_PASSWORD", "POSTGRES_PASSWORD"):
    content = content.replace(key + "=\n", key + "=" + secrets.token_hex(32) + "\n")
try:
    descriptor = os.open(root / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit(".env already exists; preserved it. Review .env.example for required settings.")
with os.fdopen(descriptor, "w") as handle:
    handle.write(content)
print("Created private .env. Next: docker compose run --build --rm migrate")
