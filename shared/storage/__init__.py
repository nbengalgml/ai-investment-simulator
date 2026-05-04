import json
import os
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))


def sim_dir(sim_id: str) -> Path:
    """Return the isolated data directory for one simulation track."""
    return DATA_DIR / "simulations" / sim_id


def make_sim_id(sector: str, account_type: str) -> str:
    return f"{sector}-{account_type}"


def read_json(path: Path) -> Any:
    with open(path) as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def append_json_list(path: Path, entry: Any) -> None:
    """Append an entry to a JSON array file, creating it if it doesn't exist."""
    existing: list[Any] = []
    if path.exists():
        existing = read_json(path)
    existing.append(entry)
    write_json(path, existing)
