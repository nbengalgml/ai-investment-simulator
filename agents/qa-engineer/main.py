#!/usr/bin/env python3
"""QA Engineer Agent — runs the full test suite and writes a QA report."""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, date, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("qa-engineer")

for _candidate in [Path("/app/shared"), Path(__file__).parent.parent.parent / "shared"]:
    if _candidate.is_dir() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))
        break

import storage as _storage  # noqa: E402

_REPO_ROOT = Path(__file__).parent.parent.parent
_TESTS_DIR = _REPO_ROOT / "tests"


def run_tests(tests_dir: Path) -> dict:
    """Run pytest and return structured results."""
    cmd = [
        sys.executable, "-m", "pytest", str(tests_dir),
        "-v", "--tb=short", "--no-header",
        "--json-report", "--json-report-file=/dev/stdout",
        "-q",
    ]
    # Fallback if pytest-json-report not installed — use plain output
    plain_cmd = [sys.executable, "-m", "pytest", str(tests_dir), "-q", "--tb=short"]

    logger.info("Running test suite: %s", tests_dir)
    try:
        result = subprocess.run(
            plain_cmd,
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            timeout=300,
        )
        output = result.stdout + result.stderr
        passed = _parse_count(output, "passed")
        failed = _parse_count(output, "failed")
        errors = _parse_count(output, "error")
        return {
            "exit_code": result.returncode,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "total": passed + failed + errors,
            "output_tail": output[-2000:],
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": 1, "passed": 0, "failed": 0, "errors": 1,
                "total": 0, "output_tail": "TIMEOUT after 300s", "success": False}
    except Exception as exc:
        return {"exit_code": 1, "passed": 0, "failed": 0, "errors": 1,
                "total": 0, "output_tail": str(exc), "success": False}


def _parse_count(output: str, keyword: str) -> int:
    import re
    m = re.search(rf"(\d+)\s+{keyword}", output)
    return int(m.group(1)) if m else 0


def write_qa_report(results: dict) -> Path:
    today = date.today().isoformat()
    now = datetime.now(timezone.utc)
    report = {
        "report_date": today,
        "generated_at": now.isoformat(),
        "suite": "full",
        **results,
        "disclaimer": "SIMULATION ONLY — not financial advice.",
    }
    out_path = _storage.DATA_DIR / "qa" / f"{today}_qa_report.json"
    _storage.write_json(out_path, report)
    return out_path


def main() -> None:
    results = run_tests(_TESTS_DIR)
    out_path = write_qa_report(results)

    status = "PASS" if results["success"] else "FAIL"
    logger.info(
        "QA %s | passed=%d failed=%d errors=%d | report → %s",
        status, results["passed"], results["failed"], results["errors"], out_path.name,
    )
    print(
        f"QA {status}: {results['passed']} passed, "
        f"{results['failed']} failed, {results['errors']} errors"
    )
    sys.exit(results["exit_code"])


if __name__ == "__main__":
    main()
