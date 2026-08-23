# Sprint 3.6.9 Block 1 -- hosted STRATUS backend image.
#
# Build context is the REPO ROOT, not backend/, deliberately: backend/app/*.py
# (logan_feed.py, logan_demo.py, ask_context.py, models.py) import logan_core
# via a runtime sys.path bridge that reaches three parents up from each file
# (see ADR-022) -- an established, unmodified pattern this image preserves
# rather than refactoring imports, matching Block 1's "operationalize the
# existing architecture, don't replace it" constraint. That means the
# deployable unit is backend/ and logan_core/ together, as siblings, exactly
# as they already sit in this repo.
#
# Build from the repo root:
#   docker build -t stratus-api .
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (both requirements files -- overlapping pins
# like pydantic/httpx resolve once, no conflict) so this layer only
# rebuilds when a dependency actually changes, not on every code edit.
COPY backend/requirements.txt backend/requirements.txt
COPY logan_core/requirements.txt logan_core/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt -r logan_core/requirements.txt

COPY backend backend
COPY logan_core logan_core

# Runs from backend/ (matching local dev's own working directory, per
# README.md's `uvicorn app.main:app` invocation) so `app.main:app` resolves
# the same way here as it does on a developer's machine.
WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# No --reload (dev-only; see README.md), binds 0.0.0.0 so Fly's proxy can
# reach it, and reads $PORT so this image is not locked to one specific
# host's port-injection convention (Fly, Render, etc. all work without
# editing this file -- fly.toml's own internal_port must match whatever
# $PORT resolves to, see fly.toml).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
