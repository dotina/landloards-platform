# Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a runnable, containerised foundation for the Landloads platform — FastAPI backend, Next.js 15 frontend, Postgres / Redis / MinIO services, an arq worker, and an Nginx reverse proxy — wired together by `docker compose up`, with `/healthz` and `/readyz` endpoints, structured logging, baseline tests, and a CI workflow.

**Architecture:** Monorepo with `backend/` (FastAPI + SQLAlchemy + arq) and `frontend/` (Next.js 15 + Tailwind + shadcn), each with its own Dockerfile. `docker-compose.yml` at the repo root orchestrates seven services: `postgres`, `redis`, `minio`, `backend`, `worker`, `frontend`, `nginx`. Nginx is the single ingress; backend and frontend are not exposed directly. The plan finishes with an end-to-end smoke test (curl `/healthz` through Nginx) and a GitHub Actions CI pipeline that lints + tests both apps.

**Tech Stack:** Python 3.14, FastAPI 0.115+, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, asyncpg, arq, structlog, pytest, testcontainers, httpx, respx · Node 20 LTS, Next.js 15, React 19, TypeScript 5, Tailwind CSS 3.4, Vitest, Playwright (config only) · Postgres 16, Redis 7, MinIO RELEASE.2024+, Nginx 1.27 · Docker Compose v2 · GitHub Actions.

**Repository layout produced by this plan:**

```
landloads/
├── .github/workflows/ci.yml
├── .env.example                    # documented env vars (committed)
├── .env                            # local secrets (gitignored)
├── .gitignore                      # exists
├── docker-compose.yml
├── docs/superpowers/{specs,plans}/  # exists
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI factory + router include
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py           # Pydantic Settings
│   │   │   ├── logging.py          # structlog setup
│   │   │   └── db.py               # async engine + session
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py             # FastAPI dependencies (db, redis)
│   │   │   └── health.py           # /healthz + /readyz routers
│   │   └── jobs/
│   │       ├── __init__.py
│   │       └── worker.py           # arq WorkerSettings
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_config.py
│       ├── test_logging.py
│       └── test_health.py
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── Dockerfile
│   ├── next.config.mjs
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.mjs
│   ├── vitest.config.ts
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── globals.css
│   │   └── lib/
│   │       └── env.ts
│   └── tests/
│       └── home.test.tsx
└── deploy/
    └── nginx/
        ├── nginx.conf
        └── conf.d/
            └── default.conf
```

**Out of scope for this plan (handled in later plans):** auth, any business entities, M-Pesa, real DB schema (this plan only creates an empty Alembic baseline), TLS termination, production hardening.

---

## Pre-flight (read once, do not commit anything yet)

Before starting Task 1, the engineer must have these tools installed and verified:

```bash
python --version    # 3.14.x
node --version      # 20.x or 22.x LTS
docker --version    # 24.x or newer
docker compose version  # v2.x
git --version
```

If any are missing, install them before continuing. On Windows, use Docker Desktop (which ships Compose v2) and the official Python and Node installers.

The repo already exists at `G:\MyWork\dev\felix\landloads` with `main` branch and one initial commit. All work in this plan happens on `main` with frequent commits. Do not push to a remote — there isn't one yet.

---

## Task 1: Project skeleton + `.env.example`

**Files:**
- Create: `.env.example`
- Create: `backend/.gitkeep`, `frontend/.gitkeep`, `deploy/nginx/.gitkeep`

- [ ] **Step 1: Create the top-level subdirectories**

```bash
cd G:/MyWork/dev/felix/landloads
mkdir -p backend frontend deploy/nginx/conf.d
```

- [ ] **Step 2: Add `.env.example` documenting every variable the stack needs**

Create `.env.example`:

```dotenv
# ─── Application ──────────────────────────────────────────────
APP_ENV=development
LOG_LEVEL=INFO

# ─── Backend ──────────────────────────────────────────────────
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# ─── Database (Postgres) ──────────────────────────────────────
POSTGRES_USER=landloads
POSTGRES_PASSWORD=landloads_dev_password
POSTGRES_DB=landloads
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://landloads:landloads_dev_password@postgres:5432/landloads

# ─── Redis ────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ─── MinIO ────────────────────────────────────────────────────
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=minio_dev_password
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio_admin
MINIO_SECRET_KEY=minio_dev_password
MINIO_BUCKET=landloads
MINIO_USE_SSL=false

# ─── Frontend ─────────────────────────────────────────────────
NEXT_PUBLIC_API_BASE_URL=http://localhost/api

# ─── Observability ────────────────────────────────────────────
SENTRY_DSN=
```

- [ ] **Step 3: Create a local `.env` for development (NOT committed)**

```bash
cp .env.example .env
```

`.env` is already in `.gitignore`, so this stays local.

- [ ] **Step 4: Verify directory structure**

```bash
ls -la
```

Expected: see `backend/`, `frontend/`, `deploy/`, `.env.example`, `.env`, `.gitignore`, `docs/`, `.git/`.

- [ ] **Step 5: Commit**

```bash
git add .env.example backend frontend deploy
git commit -m "chore: scaffold top-level project directories and .env.example"
```

(The empty subdirs need a `.gitkeep` if `git add` skips them — add `.gitkeep` files if so.)

---

## Task 2: Backend Python project (`pyproject.toml` + venv)

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.python-version`

- [ ] **Step 1: Pin Python version**

Create `backend/.python-version`:

```
3.14
```

- [ ] **Step 2: Write `pyproject.toml`**

Create `backend/pyproject.toml`:

```toml
[project]
name = "landloads-backend"
version = "0.1.0"
description = "Landloads backend API"
requires-python = ">=3.14,<3.15"
dependencies = [
    "fastapi>=0.115,<1.0",
    "uvicorn[standard]>=0.30,<1.0",
    "pydantic>=2.8,<3.0",
    "pydantic-settings>=2.4,<3.0",
    "sqlalchemy[asyncio]>=2.0.32,<3.0",
    "asyncpg>=0.29,<1.0",
    "alembic>=1.13,<2.0",
    "redis>=5.0,<6.0",
    "arq>=0.26,<1.0",
    "minio>=7.2,<8.0",
    "structlog>=24.4,<26.0",
    "httpx>=0.27,<1.0",
    "sentry-sdk[fastapi]>=2.13,<3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3,<9.0",
    "pytest-asyncio>=0.24,<1.0",
    "pytest-cov>=5.0,<6.0",
    "testcontainers[postgres,redis]>=4.8,<5.0",
    "respx>=0.21,<1.0",
    "ruff>=0.6,<1.0",
    "mypy>=1.11,<2.0",
]

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]

[tool.ruff]
line-length = 100
target-version = "py314"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "A", "RUF"]
ignore = ["E501"]  # line length handled by formatter

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.mypy]
python_version = "3.14"
strict = true
plugins = ["pydantic.mypy"]
```

- [ ] **Step 3: Create venv and install**

```bash
cd backend
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# (or on bash: source .venv/bin/activate)
pip install --upgrade pip
pip install -e ".[dev]"
```

- [ ] **Step 4: Verify pytest installed**

```bash
pytest --version
```

Expected: `pytest 8.x.y`.

- [ ] **Step 5: Add backend venv to gitignore (already covered by `.venv/` rule) and commit**

```bash
cd ..
git add backend/pyproject.toml backend/.python-version
git commit -m "feat(backend): scaffold Python project with pyproject.toml"
```

---

## Task 3: Backend config module (Pydantic Settings)

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_config.py`

- [ ] **Step 1: Create empty package files**

```bash
cd backend
touch app/__init__.py app/core/__init__.py tests/__init__.py
mkdir -p app/api app/jobs
touch app/api/__init__.py app/jobs/__init__.py
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_config.py`:

```python
"""Tests for the Settings class."""
from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_settings_loads_required_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings populates from env vars (overrides conftest defaults)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    monkeypatch.setenv("REDIS_URL", "redis://h:6379/0")

    from app.core.config import Settings
    settings = Settings()

    assert settings.database_url == "postgresql+asyncpg://u:p@h:5432/d"
    assert settings.redis_url == "redis://h:6379/0"
    assert settings.app_env == "development"  # default
    assert settings.log_level == "INFO"        # default


def test_settings_rejects_missing_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing DATABASE_URL must fail validation."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from app.core.config import Settings
    with pytest.raises(ValidationError):
        Settings()
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: `ImportError` or collection error — `app.core.config` does not exist.

- [ ] **Step 4: Create a minimal conftest**

Create `backend/tests/conftest.py`:

```python
"""Shared pytest fixtures."""
from __future__ import annotations

from collections.abc import Iterator

import pytest

# Safe default env values so modules that call get_settings() at import time
# (e.g. app.main, app.jobs.worker) can be imported during test collection.
# Individual tests that need different values override via their own monkeypatch.
_DEFAULT_ENV = {
    "APP_ENV": "development",
    "LOG_LEVEL": "INFO",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
    "REDIS_URL": "redis://localhost:6379/0",
    "MINIO_ENDPOINT": "localhost:9000",
    "MINIO_ACCESS_KEY": "test",
    "MINIO_SECRET_KEY": "test",
    "MINIO_BUCKET": "test",
    "MINIO_USE_SSL": "false",
}


@pytest.fixture(autouse=True)
def _default_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Set default env vars before each test and clear the Settings cache.

    Tests that test "missing required env" use monkeypatch.delenv explicitly.
    Tests that need different values override via monkeypatch.setenv.
    """
    for key, value in _DEFAULT_ENV.items():
        monkeypatch.setenv(key, value)

    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

- [ ] **Step 5: Implement `app/core/config.py`**

Create `backend/app/core/config.py`:

```python
"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    All values come from environment variables. See `.env.example` at the
    repo root for the canonical list.
    """

    model_config = SettingsConfigDict(
        env_file=None,                # don't auto-load; Docker/CI provide env
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_url: str = Field(..., description="SQLAlchemy async DB URL")
    redis_url: str = Field(..., description="Redis URL for cache and arq queue")

    minio_endpoint: str = Field(..., description="host:port of MinIO")
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_use_ssl: bool = False

    sentry_dsn: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor used as a FastAPI dependency."""
    return Settings()
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
cd ..
git add backend/app backend/tests
git commit -m "feat(backend): add typed Settings loaded from environment"
```

---

## Task 4: Backend structured logging

**Files:**
- Create: `backend/app/core/logging.py`
- Create: `backend/tests/test_logging.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_logging.py`:

```python
"""Tests for structlog configuration."""
from __future__ import annotations

import json
import logging

import pytest


def test_configure_logging_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    """After configure_logging, log records must be valid JSON on stdout."""
    from app.core.logging import configure_logging, get_logger

    configure_logging(level="INFO")
    log = get_logger("test")
    log.info("hello", request_id="abc-123", user="bob")

    captured = capsys.readouterr().out.strip().splitlines()
    assert captured, "expected at least one log line"
    record = json.loads(captured[-1])

    assert record["event"] == "hello"
    assert record["request_id"] == "abc-123"
    assert record["user"] == "bob"
    assert record["level"] == "info"


def test_configure_logging_respects_level(capsys: pytest.CaptureFixture[str]) -> None:
    """DEBUG records must be filtered out at INFO level."""
    from app.core.logging import configure_logging, get_logger

    configure_logging(level="INFO")
    log = get_logger("test")
    log.debug("should-not-appear")
    log.info("should-appear")

    out = capsys.readouterr().out
    assert "should-not-appear" not in out
    assert "should-appear" in out
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_logging.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `app/core/logging.py`**

Create `backend/app/core/logging.py`:

```python
"""Structured logging via structlog, JSON output to stdout."""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog and stdlib logging for the whole app.

    Idempotent — safe to call multiple times.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None, **initial_values: Any) -> structlog.stdlib.BoundLogger:
    """Return a bound logger; pass keyword args to seed context."""
    return structlog.get_logger(name).bind(**initial_values)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_logging.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/app/core/logging.py backend/tests/test_logging.py
git commit -m "feat(backend): add JSON structured logging via structlog"
```

---

## Task 5: Backend FastAPI app + `/healthz` (liveness)

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/health.py`
- Create: `backend/tests/test_health.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_health.py`:

```python
"""Tests for /healthz and /readyz endpoints."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch):
    """Provide a fully-configured FastAPI app for tests."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    monkeypatch.setenv("REDIS_URL", "redis://h:6379/0")
    monkeypatch.setenv("MINIO_ENDPOINT", "h:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "k")
    monkeypatch.setenv("MINIO_SECRET_KEY", "s")
    monkeypatch.setenv("MINIO_BUCKET", "b")
    from app.main import create_app
    return create_app()


@pytest.mark.asyncio
async def test_healthz_returns_ok(app) -> None:
    """/healthz must return 200 and a status payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_health.py -v
```

Expected: `ImportError` — `app.main` does not exist.

- [ ] **Step 3: Implement `app/api/health.py`**

Create `backend/app/api/health.py`:

```python
"""Liveness and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/healthz", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def healthz() -> HealthResponse:
    """Liveness probe: returns 200 as long as the process can serve requests.

    Does NOT check downstream dependencies — see /readyz for that.
    """
    return HealthResponse(status="ok", version=APP_VERSION)
```

- [ ] **Step 4: Implement `app/main.py`**

Create `backend/app/main.py`:

```python
"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI

from app.api import health
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    """Build and return the FastAPI app instance."""
    settings = get_settings()
    configure_logging(level=settings.log_level)

    app = FastAPI(
        title="Landloads API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    log = get_logger("app.startup", env=settings.app_env)
    log.info("application_startup")

    app.include_router(health.router, prefix="")

    return app


app = create_app()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_health.py::test_healthz_returns_ok -v
```

Expected: 1 passed.

- [ ] **Step 6: Smoke-test the app locally**

```bash
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
curl http://localhost:8000/healthz
```

Expected: `{"status":"ok","version":"0.1.0"}`. Stop uvicorn with Ctrl+C.

- [ ] **Step 7: Commit**

```bash
cd ..
git add backend/app/main.py backend/app/api/health.py backend/tests/test_health.py
git commit -m "feat(backend): add FastAPI app factory and /healthz liveness probe"
```

---

## Task 6: Backend `/readyz` (readiness with DB + Redis checks)

**Files:**
- Create: `backend/app/core/db.py`
- Create: `backend/app/api/deps.py`
- Modify: `backend/app/api/health.py`
- Modify: `backend/tests/test_health.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_health.py`:

```python
@pytest.mark.asyncio
async def test_readyz_returns_ok_when_deps_healthy(app, monkeypatch) -> None:
    """/readyz returns 200 when DB and Redis ping succeed."""
    from app.api import health as health_module

    async def _ok_db() -> bool:
        return True

    async def _ok_redis() -> bool:
        return True

    monkeypatch.setattr(health_module, "check_database", _ok_db)
    monkeypatch.setattr(health_module, "check_redis", _ok_redis)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}


@pytest.mark.asyncio
async def test_readyz_returns_503_when_db_down(app, monkeypatch) -> None:
    """/readyz returns 503 when DB ping fails."""
    from app.api import health as health_module

    async def _bad_db() -> bool:
        return False

    async def _ok_redis() -> bool:
        return True

    monkeypatch.setattr(health_module, "check_database", _bad_db)
    monkeypatch.setattr(health_module, "check_redis", _ok_redis)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/readyz")
    assert r.status_code == 503
    body = r.json()
    assert body["checks"]["database"] == "fail"
    assert body["checks"]["redis"] == "ok"
```

- [ ] **Step 2: Run tests to verify failures**

```bash
cd backend
pytest tests/test_health.py -v
```

Expected: 2 new tests fail (no `/readyz` route).

- [ ] **Step 3: Implement `app/core/db.py`**

Create `backend/app/core/db.py`:

```python
"""Async SQLAlchemy engine + session factory."""
from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Lazily build the shared async engine."""
    return create_async_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        future=True,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory."""
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an AsyncSession."""
    async with get_session_factory()() as session:
        yield session
```

- [ ] **Step 4: Update `app/api/health.py`**

Replace `backend/app/api/health.py` with:

```python
"""Liveness and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine
from app.core.logging import get_logger

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"
log = get_logger("app.health")


class HealthResponse(BaseModel):
    status: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


async def check_database() -> bool:
    """Return True iff `SELECT 1` succeeds against Postgres."""
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("readiness_db_check_failed", error=str(exc))
        return False


async def check_redis() -> bool:
    """Return True iff Redis PING succeeds."""
    client: Redis | None = None
    try:
        client = Redis.from_url(get_settings().redis_url)
        return bool(await client.ping())
    except Exception as exc:  # noqa: BLE001
        log.warning("readiness_redis_check_failed", error=str(exc))
        return False
    finally:
        if client is not None:
            await client.aclose()


@router.get("/healthz", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def healthz() -> HealthResponse:
    """Liveness probe: 200 as long as the process can serve requests."""
    return HealthResponse(status="ok", version=APP_VERSION)


@router.get("/readyz", response_model=ReadinessResponse)
async def readyz(response: Response) -> ReadinessResponse:
    """Readiness probe: checks DB + Redis. 503 if any check fails."""
    db_ok = await check_database()
    redis_ok = await check_redis()
    checks = {
        "database": "ok" if db_ok else "fail",
        "redis": "ok" if redis_ok else "fail",
    }
    if not (db_ok and redis_ok):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="degraded", checks=checks)
    return ReadinessResponse(status="ready", checks=checks)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_health.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/app/core/db.py backend/app/api/health.py backend/tests/test_health.py
git commit -m "feat(backend): add /readyz with Postgres and Redis checks"
```

---

## Task 7: Backend Alembic baseline

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/.gitkeep`

- [ ] **Step 1: Generate Alembic scaffold**

```bash
cd backend
alembic init -t async alembic
```

This creates `alembic/`, `alembic.ini`, and template files.

- [ ] **Step 2: Replace generated `alembic/env.py`**

Overwrite `backend/alembic/env.py` with:

```python
"""Alembic env: read DATABASE_URL from app settings, async-friendly."""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

# No models registered yet — later plans will set:
#   from app.core.models import Base
#   target_metadata = Base.metadata
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emit SQL)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live DB."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 3: Edit `alembic.ini`**

Open `backend/alembic.ini` and ensure these keys are set (leave the rest as Alembic generated):

```ini
[alembic]
script_location = alembic
sqlalchemy.url =
prepend_sys_path = .
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic
```

(`sqlalchemy.url` is left blank because `env.py` overrides it from settings.)

- [ ] **Step 4: Generate the empty baseline migration**

```bash
alembic revision -m "baseline"
```

This creates `alembic/versions/<hash>_baseline.py`. Open it and confirm `upgrade()` and `downgrade()` are empty (`pass`). Do not edit it further yet — later plans will add real models.

- [ ] **Step 5: Verify Alembic file structure**

Verifying against a live database is deferred to Task 15 (smoke test), which brings Postgres up via docker compose. For now, confirm the file layout:

```bash
ls alembic/versions/
```

Expected: one `*_baseline.py` file plus `.gitkeep`.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/alembic.ini backend/alembic
git commit -m "feat(backend): add async Alembic config and empty baseline migration"
```

---

## Task 8: Backend arq worker skeleton

**Files:**
- Create: `backend/app/jobs/worker.py`
- Create: `backend/tests/test_worker.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_worker.py`:

```python
"""Tests for the arq WorkerSettings."""
from __future__ import annotations

import pytest
from arq.connections import RedisSettings


def test_worker_settings_lists_functions() -> None:
    """WorkerSettings.functions must be a list (empty is fine for now)."""
    from app.jobs.worker import WorkerSettings
    assert isinstance(WorkerSettings.functions, list)


def test_worker_settings_redis_settings_is_redis_settings() -> None:
    """WorkerSettings.redis_settings must resolve to an arq RedisSettings."""
    from app.jobs.worker import WorkerSettings
    assert isinstance(WorkerSettings.redis_settings, RedisSettings)


def test_worker_settings_redis_settings_reflects_current_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lazy descriptor must pick up the current REDIS_URL on each access."""
    monkeypatch.setenv("REDIS_URL", "redis://myredis:6379/2")
    from app.core.config import get_settings
    get_settings.cache_clear()

    from app.jobs.worker import WorkerSettings
    rs = WorkerSettings.redis_settings
    assert rs.host == "myredis"
    assert rs.port == 6379
    assert rs.database == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_worker.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `app/jobs/worker.py`**

Create `backend/app/jobs/worker.py`:

```python
"""arq worker: background jobs (reminders, late-fee accrual, M-Pesa reconciliation).

Later plans register real tasks. For now this module just makes the worker bootable.
"""
from __future__ import annotations

from typing import Any

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


async def startup(ctx: dict[str, Any]) -> None:
    """Run once on worker boot."""
    configure_logging(level=get_settings().log_level)
    log = get_logger("worker.startup")
    log.info("worker_started")
    ctx["log"] = log


async def shutdown(ctx: dict[str, Any]) -> None:
    """Run once on worker shutdown."""
    ctx["log"].info("worker_stopped")


class _LazyRedisSettings:
    """Class-attribute descriptor that resolves RedisSettings on every access.

    Needed because ``WorkerSettings`` is read at module-import time but
    REDIS_URL may be set later (e.g. by tests). arq accesses this attribute
    once at worker start, so per-access cost is irrelevant in production.
    """

    def __get__(self, _obj: object, _objtype: type | None = None) -> RedisSettings:
        return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    """arq picks this up: `arq app.jobs.worker.WorkerSettings`."""

    functions: list = []  # later plans append task functions here
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _LazyRedisSettings()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_worker.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/app/jobs/worker.py backend/tests/test_worker.py
git commit -m "feat(backend): add arq worker skeleton (no tasks yet)"
```

---

## Task 9: Backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

- [ ] **Step 1: Write `.dockerignore`**

Create `backend/.dockerignore`:

```
.venv
__pycache__
*.py[cod]
.pytest_cache
.mypy_cache
.ruff_cache
.coverage
htmlcov
tests
.git
.env
.env.*
```

- [ ] **Step 2: Write the Dockerfile (multi-stage, slim runtime)**

Create `backend/Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1.7

# ─── Builder stage ────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build tools needed for asyncpg, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

# Install runtime deps into a venv we'll copy into the runtime stage
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install .

# ─── Runtime stage ────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Build the image to verify it succeeds**

```bash
cd backend
docker build -t landloads-backend:dev .
```

Expected: build completes; final image tagged `landloads-backend:dev`. Build time roughly 2–5 minutes on first build.

- [ ] **Step 4: Smoke-run the image (will fail readyz without DB; healthz must work)**

```bash
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://u:p@127.0.0.1:5432/x \
  -e REDIS_URL=redis://127.0.0.1:6379/0 \
  -e MINIO_ENDPOINT=x:9000 \
  -e MINIO_ACCESS_KEY=k \
  -e MINIO_SECRET_KEY=s \
  -e MINIO_BUCKET=b \
  landloads-backend:dev
```

In another terminal:

```bash
curl http://localhost:8000/healthz
```

Expected: `{"status":"ok","version":"0.1.0"}`. Stop the container with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/Dockerfile backend/.dockerignore
git commit -m "feat(backend): add multi-stage Dockerfile with healthcheck"
```

---

## Task 10: Frontend Next.js scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/package-lock.json` (generated)
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.mjs`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/.eslintrc.json`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/globals.css`
- Create: `frontend/src/lib/env.ts`

- [ ] **Step 1: Write `package.json`**

Create `frontend/package.json`:

```json
{
  "name": "landloads-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "next lint",
    "test": "vitest run",
    "test:watch": "vitest",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "15.0.3",
    "react": "19.0.0",
    "react-dom": "19.0.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.5.0",
    "@testing-library/react": "^16.0.1",
    "@types/node": "^22.7.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.3",
    "autoprefixer": "^10.4.20",
    "eslint": "^9",
    "eslint-config-next": "15.0.3",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.13",
    "typescript": "^5.6.3",
    "vitest": "^2.1.3"
  }
}
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install
```

This generates `package-lock.json` and `node_modules/`.

- [ ] **Step 3: Write `tsconfig.json`**

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"],
    "paths": { "@/*": ["./src/*"] },
    "plugins": [{ "name": "next" }]
  },
  "include": ["next-env.d.ts", "src/**/*", "tests/**/*", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 4: Write `next.config.mjs` (standalone output for Docker)**

Create `frontend/next.config.mjs`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
};

export default nextConfig;
```

- [ ] **Step 5: Write Tailwind & PostCSS configs**

Create `frontend/tailwind.config.ts`:

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // M-Pesa-adjacent green for paid states; refine in Plan 8
        paid: { 500: "#16a34a" },
        due:  { 500: "#f59e0b" },
        overdue: { 500: "#dc2626" },
      },
    },
  },
  plugins: [],
};
export default config;
```

Create `frontend/postcss.config.mjs`:

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 6: Write `.eslintrc.json`**

Create `frontend/.eslintrc.json`:

```json
{
  "extends": ["next/core-web-vitals", "next/typescript"]
}
```

- [ ] **Step 7: Write `src/lib/env.ts`**

Create `frontend/src/lib/env.ts`:

```typescript
/** Runtime-validated public env vars. */

const required = (name: string, value: string | undefined): string => {
  if (!value || value.length === 0) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
};

export const env = {
  apiBaseUrl: required("NEXT_PUBLIC_API_BASE_URL", process.env.NEXT_PUBLIC_API_BASE_URL),
} as const;
```

- [ ] **Step 8: Write the layout, page, and globals**

Create `frontend/src/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root { color-scheme: light; }
html, body { height: 100%; }
body { @apply bg-white text-gray-900 antialiased; }
```

Create `frontend/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Landloads",
  description: "Landlord management platform",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

Create `frontend/src/app/page.tsx`:

```tsx
export default function HomePage() {
  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-semibold">Landloads</h1>
        <p className="text-gray-600">Foundation is up and running.</p>
        <p data-testid="health-link" className="text-sm text-gray-500">
          API base: <code className="bg-gray-100 px-2 py-1 rounded">/api</code>
        </p>
      </div>
    </main>
  );
}
```

- [ ] **Step 9: Run `next build` to verify the project compiles**

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost/api npm run build
```

(On Windows PowerShell: `$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost/api"; npm run build`)

Expected: build succeeds, prints route table including `/`. A `.next/` directory is created.

- [ ] **Step 10: Commit**

```bash
cd ..
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json \
        frontend/next.config.mjs frontend/postcss.config.mjs frontend/tailwind.config.ts \
        frontend/.eslintrc.json frontend/src
git commit -m "feat(frontend): scaffold Next.js 15 app with Tailwind and typed env"
```

---

## Task 11: Frontend Vitest setup + home page test

**Files:**
- Create: `frontend/vitest.config.ts`
- Create: `frontend/tests/setup.ts`
- Create: `frontend/tests/home.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/home.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import HomePage from "@/app/page";

describe("HomePage", () => {
  it("renders the brand and the API base hint", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: /landloads/i })).toBeInTheDocument();
    expect(screen.getByTestId("health-link")).toHaveTextContent("/api");
  });
});
```

- [ ] **Step 2: Configure Vitest**

Create `frontend/vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    css: false,
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
```

Create `frontend/tests/setup.ts`:

```typescript
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 3: Run the test**

```bash
cd frontend
npm test
```

Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
cd ..
git add frontend/vitest.config.ts frontend/tests
git commit -m "test(frontend): add Vitest config and HomePage smoke test"
```

---

## Task 12: Frontend Dockerfile

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/.dockerignore`

- [ ] **Step 1: Write `.dockerignore`**

Create `frontend/.dockerignore`:

```
node_modules
.next
out
.turbo
coverage
tests
.git
.env
.env.*
*.log
```

- [ ] **Step 2: Write the Dockerfile (uses Next.js standalone output)**

Create `frontend/Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1.7

# ─── Deps ─────────────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ─── Builder ──────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

# Build-time public env (must be set or `next build` errors via env.ts)
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost/api
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ─── Runtime ──────────────────────────────────────────────────
FROM node:20-alpine AS runtime
WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://localhost:3000/ >/dev/null 2>&1 || exit 1

CMD ["node", "server.js"]
```

- [ ] **Step 3: Build the image**

```bash
cd frontend
docker build -t landloads-frontend:dev .
```

Expected: build succeeds. (First build ~3–5 min; later builds <1 min.)

- [ ] **Step 4: Smoke-run the image**

```bash
docker run --rm -p 3000:3000 landloads-frontend:dev
```

In another terminal:

```bash
curl http://localhost:3000/
```

Expected: HTML response containing the string `Landloads`. Stop the container.

- [ ] **Step 5: Commit**

```bash
cd ..
git add frontend/Dockerfile frontend/.dockerignore
git commit -m "feat(frontend): add multi-stage Dockerfile with standalone Next output"
```

---

## Task 13: Nginx reverse proxy configuration

**Files:**
- Create: `deploy/nginx/nginx.conf`
- Create: `deploy/nginx/conf.d/default.conf`

- [ ] **Step 1: Write `nginx.conf`**

Create `deploy/nginx/nginx.conf`:

```nginx
user  nginx;
worker_processes auto;

error_log  /var/log/nginx/error.log notice;
pid        /var/run/nginx.pid;

events { worker_connections 1024; }

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format json_combined escape=json
        '{"time":"$time_iso8601","remote":"$remote_addr",'
        '"method":"$request_method","path":"$request_uri",'
        '"status":$status,"bytes":$body_bytes_sent,'
        '"referer":"$http_referer","ua":"$http_user_agent",'
        '"rt":$request_time}';

    access_log /var/log/nginx/access.log json_combined;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    server_tokens off;
    client_max_body_size 25m;   # KYC doc uploads

    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    include /etc/nginx/conf.d/*.conf;
}
```

- [ ] **Step 2: Write `conf.d/default.conf`**

Create `deploy/nginx/conf.d/default.conf`:

```nginx
upstream backend  { server backend:8000; }
upstream frontend { server frontend:3000; }

server {
    listen 80 default_server;
    server_name _;

    # Backend API
    location /api/ {
        proxy_pass http://backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-Id $request_id;
    }

    # Health passthrough — proxied so monitors hit a single port
    location = /healthz { proxy_pass http://backend/healthz; }
    location = /readyz  { proxy_pass http://backend/readyz; }

    # Everything else → Next.js
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

- [ ] **Step 3: Validate the config syntactically**

```bash
docker run --rm \
  -v "$(pwd)/deploy/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "$(pwd)/deploy/nginx/conf.d:/etc/nginx/conf.d:ro" \
  nginx:1.27-alpine nginx -t
```

(On Windows PowerShell, replace `$(pwd)` with `${PWD}`.)

Expected: `nginx: configuration file /etc/nginx/nginx.conf test is successful`. The DNS lookups for `backend` / `frontend` will not resolve at this stage — that's fine; this is a syntax check only.

- [ ] **Step 4: Commit**

```bash
git add deploy/nginx
git commit -m "feat(deploy): add Nginx reverse-proxy config for backend and frontend"
```

---

## Task 14: docker-compose.yml

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Write `docker-compose.yml`**

Create `docker-compose.yml` at the repo root:

```yaml
name: landloads

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  minio:
    image: minio/minio:RELEASE.2024-09-22T00-33-43Z
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 6
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file: .env
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      MINIO_ENDPOINT: ${MINIO_ENDPOINT}
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      MINIO_BUCKET: ${MINIO_BUCKET}
    depends_on:
      postgres: { condition: service_healthy }
      redis:    { condition: service_healthy }
      minio:    { condition: service_healthy }
    restart: unless-stopped

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: ["arq", "app.jobs.worker.WorkerSettings"]
    env_file: .env
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      MINIO_ENDPOINT: ${MINIO_ENDPOINT}
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      MINIO_BUCKET: ${MINIO_BUCKET}
    depends_on:
      postgres: { condition: service_healthy }
      redis:    { condition: service_healthy }
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_API_BASE_URL: ${NEXT_PUBLIC_API_BASE_URL}
    environment:
      NEXT_PUBLIC_API_BASE_URL: ${NEXT_PUBLIC_API_BASE_URL}
    depends_on:
      backend:
        condition: service_started
    restart: unless-stopped

  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
    volumes:
      - ./deploy/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./deploy/nginx/conf.d:/etc/nginx/conf.d:ro
    depends_on:
      backend:
        condition: service_started
      frontend:
        condition: service_started
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

- [ ] **Step 2: Validate the compose file**

```bash
docker compose config >/dev/null
```

Expected: no output (validation passed). If errors print, fix the YAML.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(deploy): add docker-compose.yml orchestrating full stack"
```

---

## Task 15: End-to-end smoke test

This task verifies the full stack boots and routes traffic correctly. No code changes — just exercise the system.

- [ ] **Step 1: Build and bring the stack up**

```bash
docker compose up --build -d
```

Expected: all services start. Wait ~30s for health checks to settle.

- [ ] **Step 2: Inspect status**

```bash
docker compose ps
```

Expected: all services show `Up` and `healthy` (where applicable).

- [ ] **Step 3: Hit `/healthz` through Nginx**

```bash
curl -i http://localhost/healthz
```

Expected: HTTP 200, body `{"status":"ok","version":"0.1.0"}`.

- [ ] **Step 4: Hit `/readyz` through Nginx**

```bash
curl -i http://localhost/readyz
```

Expected: HTTP 200, body containing `"database":"ok"` and `"redis":"ok"`.

- [ ] **Step 5: Hit the frontend home page through Nginx**

```bash
curl -is http://localhost/ | head -20
```

Expected: HTTP 200 and HTML containing `Landloads`.

- [ ] **Step 6: Hit the API docs through Nginx**

```bash
curl -i http://localhost/api/docs
```

Expected: HTTP 200, HTML for Swagger UI.

- [ ] **Step 7: Inspect logs (one per service) and confirm no errors**

```bash
docker compose logs backend  --tail=50
docker compose logs frontend --tail=20
docker compose logs worker   --tail=20
docker compose logs nginx    --tail=20
```

Expected: structured JSON logs from backend and worker; no stack traces.

- [ ] **Step 8: Tear the stack down**

```bash
docker compose down
```

(Volumes persist; use `docker compose down -v` only if you want to wipe Postgres/Redis/MinIO data.)

- [ ] **Step 9: Commit a marker noting smoke test passed**

There's nothing to commit code-wise; the stack worked. Continue to Task 16.

---

## Task 16: GitHub Actions CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: backend/pyproject.toml

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Lint (ruff)
        run: ruff check .

      - name: Type-check (mypy)
        run: mypy app

      - name: Tests
        run: pytest --cov=app --cov-report=term-missing

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    env:
      NEXT_PUBLIC_API_BASE_URL: http://localhost/api
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test
      - run: npm run build

  compose:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4

      - name: Validate docker-compose.yml
        run: |
          cp .env.example .env
          docker compose config >/dev/null

      - name: Build all images
        run: docker compose build
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow for backend, frontend, and compose validation"
```

(The workflow can't actually run until a remote is added and pushed to. That's deferred to Plan 10.)

---

## Task 17: Final verification + summary commit

- [ ] **Step 1: Run all backend tests**

```bash
cd backend
pytest
```

Expected: all tests pass (8+ tests across `test_config.py`, `test_logging.py`, `test_health.py`, `test_worker.py`).

- [ ] **Step 2: Run all frontend tests**

```bash
cd ../frontend
npm test
```

Expected: 1 test passes.

- [ ] **Step 3: Run lint + typecheck on both apps**

```bash
cd ../backend
ruff check .
mypy app
cd ../frontend
npm run lint
npm run typecheck
```

Expected: all green.

- [ ] **Step 4: Bring the stack up one final time and verify smoke test**

```bash
cd ..
docker compose up --build -d
sleep 30
curl -fsS http://localhost/healthz
curl -fsS http://localhost/readyz
curl -fsS http://localhost/ -o /dev/null -w "%{http_code}\n"
docker compose down
```

Expected: `/healthz` and `/readyz` return JSON status, frontend curl prints `200`.

- [ ] **Step 5: Confirm git log shape**

```bash
git log --oneline
```

Expected: ~16 commits on `main`, each with a clear `feat:`, `test:`, `chore:`, or `ci:` prefix.

- [ ] **Step 6: Tag the foundation milestone**

```bash
git tag -a v0.1.0-foundation -m "Plan 1 complete: foundation stack runnable end-to-end"
```

(No remote to push to yet — the tag is local. Plan 10 will set up a remote and push tags.)

---

## Done criteria for Plan 1

All boxes below must be checked before declaring Plan 1 complete:

- [ ] `docker compose up --build -d` brings up 7 services, all healthy
- [ ] `curl http://localhost/healthz` returns `{"status":"ok","version":"0.1.0"}`
- [ ] `curl http://localhost/readyz` returns `{"status":"ready","checks":{"database":"ok","redis":"ok"}}`
- [ ] `curl http://localhost/` returns HTML containing `Landloads`
- [ ] `curl http://localhost/api/docs` returns Swagger UI HTML
- [ ] Backend `pytest` is green (≥ 8 tests)
- [ ] Frontend `npm test` is green
- [ ] `ruff check .` and `mypy app` are green
- [ ] `npm run lint` and `npm run typecheck` are green
- [ ] `docker compose config` validates
- [ ] `.github/workflows/ci.yml` exists and uses pinned versions for setup-python and setup-node
- [ ] Tag `v0.1.0-foundation` exists locally
- [ ] No `.env` or other secrets committed (run `git ls-files | grep -i env` — only `.env.example`)
