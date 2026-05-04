import sys
from pathlib import Path

# Make shared/ importable as top-level packages when running pytest from repo root
sys.path.insert(0, str(Path(__file__).parent / "shared"))
