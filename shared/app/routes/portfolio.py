"""GET /portfolio, GET /portfolio/history"""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["portfolio"])

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))


@router.get("/portfolio")
async def get_portfolio() -> dict:
    state_path = DATA_DIR / "portfolio" / "state.json"
    if not state_path.exists():
        raise HTTPException(status_code=404, detail="No portfolio state found. Run analyst agent first.")
    import json
    return json.loads(state_path.read_text())


@router.get("/portfolio/history")
async def get_portfolio_history() -> list[dict]:
    history_dir = DATA_DIR / "portfolio" / "history"
    if not history_dir.exists():
        return []
    import json
    snapshots = []
    for f in sorted(history_dir.glob("*.json")):
        try:
            snapshots.append(json.loads(f.read_text()))
        except Exception:
            pass
    return snapshots
