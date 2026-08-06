import sys
from pathlib import Path

# backend/app's own modules do this too (see logan_demo.py, ADR-022) -- repeated
# here so the test suite doesn't depend on import order pulling one of them in
# first.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
