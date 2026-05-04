"""GET /trades"""

import json
import os
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["trades"])

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))


@router.get("/trades")
async def get_trades() -> list[dict]:
    log_path = DATA_DIR / "trades" / "log.json"
    if not log_path.exists():
        return []
    try:
        entries = json.loads(log_path.read_text())
        return sorted(entries, key=lambda e: e.get("timestamp", ""), reverse=True)
    except Exception:
        return []
