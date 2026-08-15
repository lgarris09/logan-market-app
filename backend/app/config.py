"""Sprint 3.6.6C — the first place `backend/app/` reads `.env` or runtime
config. Reconnaissance before writing this: no config.py/settings.py
existed, and no module under backend/app/ called os.environ or load_dotenv
anywhere -- backend/.env (FMP_API_KEY, gitignored, local-dev-only) was not
being auto-loaded into the backend process at all. This is the minimal
addition needed, not a general settings framework.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# python-dotenv is already an installed dependency (backend/requirements.txt's
# uvicorn[standard] extra pulls it in transitively; confirmed present in this
# venv) -- not a new dependency addition. Loads backend/.env into the real
# process environment once, at import time, before any route or pipeline
# code runs. Safe no-op if the file doesn't exist (e.g. a fresh clone before
# the .env is restored) -- os.environ.get() calls elsewhere degrade to their
# own explicit "not configured" handling, never a crash here.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def live_nvda_earnings_enabled() -> bool:
    """Sprint 3.6.6C: gates whether /v1/opportunities attempts to replace the
    simulated NVDA fixture with a real FMP-driven earnings opportunity.
    Defaults to disabled -- existing simulated-only behavior is the safe,
    backward-compatible default; this must be explicitly turned on via
    STRATUS_LIVE_NVDA_EARNINGS=true.

    A function, not a frozen module-level constant, so it always reflects
    the current environment -- tests toggle this with monkeypatch.setenv
    without needing to reload the module, and the real backend only needs a
    clean restart (not a code change) to flip it.
    """
    return os.environ.get("STRATUS_LIVE_NVDA_EARNINGS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
