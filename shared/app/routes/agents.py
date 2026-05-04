"""
POST /agents/{agent}/trigger
Runs an agent script as a background subprocess and returns immediately.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

AGENTS_DIR = Path(os.getenv("AGENTS_DIR", "/app/agents"))

_AGENT_SCRIPTS: dict[str, str] = {
    "market-researcher": "market-researcher/main.py",
    "analyst": "analyst/main.py",
    "ceo": "ceo/main.py",
    "qa-engineer": "qa-engineer/main.py",
}


class TriggerPayload(BaseModel):
    sector: str = "AI"
    no_claude: bool = False


class TriggerResponse(BaseModel):
    agent: str
    status: Literal["accepted", "error"]
    message: str


async def _run_agent(script: Path, sector: str, no_claude: bool) -> None:
    args = [sys.executable, str(script), "--sector", sector]
    if no_claude:
        args.append("--no-claude")
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        if stdout:
            for line in stdout.decode().strip().splitlines():
                logger.info("[%s] %s", script.parent.name, line)
        if proc.returncode != 0:
            logger.error("[%s] exited with code %d", script.parent.name, proc.returncode)
        else:
            logger.info("[%s] completed successfully", script.parent.name)
    except Exception as exc:
        logger.error("[%s] subprocess error: %s", script.parent.name, exc)


@router.post("/{agent}/trigger", response_model=TriggerResponse)
async def trigger_agent(
    agent: str,
    payload: TriggerPayload,
    background_tasks: BackgroundTasks,
) -> TriggerResponse:
    if agent not in _AGENT_SCRIPTS:
        known = ", ".join(_AGENT_SCRIPTS)
        raise HTTPException(status_code=404, detail=f"Unknown agent '{agent}'. Known: {known}")

    script = AGENTS_DIR / _AGENT_SCRIPTS[agent]
    if not script.exists():
        raise HTTPException(status_code=503, detail=f"Agent script not found: {script}")

    background_tasks.add_task(_run_agent, script, payload.sector, payload.no_claude)
    logger.info("Accepted trigger for %s | sector=%s", agent, payload.sector)

    return TriggerResponse(
        agent=agent,
        status="accepted",
        message=f"{agent} scheduled (sector={payload.sector})",
    )


@router.get("/status")
async def agents_status() -> dict:
    """Return which agent scripts are present on disk."""
    return {
        agent: (AGENTS_DIR / path).exists()
        for agent, path in _AGENT_SCRIPTS.items()
    }
