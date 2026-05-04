"""GET /settings, POST /settings"""

import json
import os
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["settings"])

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))

TARGET_MARKETS = ["AI", "Cloud", "Networking", "Alternative Energy", "Gas", "Finance"]

_DEFAULTS = {
    "budget_total": 10000.0,
    "account_type": "brokerage",
    "target_market": "AI",
}


def _settings_path() -> Path:
    return DATA_DIR / "settings.json"


def _load() -> dict:
    p = _settings_path()
    if not p.exists():
        return dict(_DEFAULTS)
    try:
        return {**_DEFAULTS, **json.loads(p.read_text())}
    except Exception:
        return dict(_DEFAULTS)


class SettingsUpdate(BaseModel):
    budget_total: float | None = None
    account_type: str | None = None
    target_market: str | None = None


@router.get("/settings")
async def get_settings() -> dict:
    return _load()


@router.post("/settings")
async def update_settings(body: SettingsUpdate) -> dict:
    current = _load()
    if body.budget_total is not None:
        current["budget_total"] = body.budget_total
    if body.account_type is not None:
        if body.account_type not in ("brokerage", "traditional_ira"):
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="account_type must be 'brokerage' or 'traditional_ira'")
        current["account_type"] = body.account_type
    if body.target_market is not None:
        current["target_market"] = body.target_market
    p = _settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(current))
    return current
