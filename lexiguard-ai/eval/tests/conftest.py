import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = EVAL_DIR.parent / "backend"
for p in (str(EVAL_DIR), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)
