# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- **FastAPI** — HTTP API layer (Python 3.12)
- **SQLAlchemy 2.x** — ORM (sync, psycopg2)
- **PostgreSQL** — primary database
- **Celery + Redis** — background task queue (scraping, plan generation)
- **Pydantic Settings** — environment/config via `.env`
- **uv** — package manager and virtual environment

## Commands

```bash
uv sync                                          # install dependencies
uv run uvicorn app.main:app --reload             # dev server
uv run celery -A app.celery_app worker --loglevel=info  # celery worker
uv run celery -A app.celery_app beat --loglevel=info    # celery beat scheduler
uv run pytest                                      # test suite
uv add <package>                                 # add dependency

# verify imports
uv run python -c "from app.models import User, Place; print('ok')"
```

## Architecture

```
app/
  config.py       — BaseSettings (reads from .env)
  database.py     — SQLAlchemy engine, SessionLocal, get_db() dep
  main.py         — FastAPI app + lifespan (create_all on startup)
  models/
    base.py       — declarative Base, UUIDMixin, TimestampMixin, all Enums
    user.py       — User (Google OAuth)
    place.py      — Place (scraped/manual venues)
    hangout.py    — HangoutRequest, GeneratedPlan, PlanStop
    rating.py     — PlanRating
  schemas/
    auth.py       — GoogleAuthRequest, TokenResponse
    user.py       — UserOut
    place.py      — PlaceOut
    hangout.py    — HangoutRequestCreate/Out, GeneratedPlanOut, PlanStopOut, PlanSelectionRequest
    rating.py     — PlanRatingCreate, PlanRatingOut
  services/
    planner.py    — business logic (plan generation, stub)
```

## Domain Model

A **User** submits a **HangoutRequest** (location text, vibe, price tier, duration). The planner generates 3 **GeneratedPlan**s, each with ordered **PlanStop**s pointing to **Place** records. The user selects one plan; after the hangout they submit a **PlanRating** (1–5).

**Enums** (defined in `app/models/base.py`, imported by both models and schemas):
- `Vibe`: `chill | hype | romantic | outdoorsy`
- `PriceTier`: `low | med | high | luxury`
- `HangoutStatus`: `pending → generated → selected → completed | cancelled`
- `PlaceSource`: `manual | scraped`

## Required `.env` keys

```
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379/0
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
JWT_SECRET=
```
