#!/usr/bin/env python3
"""Market Researcher Agent — entry point."""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)

# Resolve shared/ for both Docker (/app/shared) and standalone runs
for candidate in [
    Path("/app/shared"),
    Path(__file__).parent.parent.parent / "shared",
]:
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
        break

from research import run_research_cycle  # noqa: E402 — path must be set first


def main() -> None:
    parser = argparse.ArgumentParser(description="Market Researcher Agent")
    parser.add_argument(
        "--sector",
        default=os.getenv("DEFAULT_TARGET_MARKET", "AI"),
        help="Sector to research: AI, cloud, networking, alternative_energy, gas, finance",
    )
    parser.add_argument(
        "--no-claude",
        action="store_true",
        help="Skip Claude scoring (uses algorithmic fallback)",
    )
    args = parser.parse_args()

    snapshot = run_research_cycle(sector=args.sector, use_claude=not args.no_claude)
    print(f"Done: {snapshot.snapshot_id} | {len(snapshot.stocks)} stocks | sources: {snapshot.data_sources}")


if __name__ == "__main__":
    main()
