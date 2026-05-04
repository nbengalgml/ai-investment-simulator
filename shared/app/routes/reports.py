"""GET /reports/daily, GET /reports/daily/{date}"""

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["reports"])

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))


@router.get("/reports/daily")
async def list_daily_reports() -> list[dict]:
    daily_dir = DATA_DIR / "reports" / "daily"
    if not daily_dir.exists():
        return []
    reports = []
    for f in sorted(daily_dir.glob("*.json"), reverse=True):
        try:
            reports.append(json.loads(f.read_text()))
        except Exception:
            pass
    return reports


@router.get("/reports/daily/{report_date}")
async def get_daily_report(report_date: str) -> dict:
    daily_dir = DATA_DIR / "reports" / "daily"
    # filename format: YYYY-MM-DD_executive_summary.json
    matches = list(daily_dir.glob(f"{report_date}*.json")) if daily_dir.exists() else []
    if not matches:
        raise HTTPException(status_code=404, detail=f"No report found for {report_date}")
    try:
        return json.loads(matches[0].read_text())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
