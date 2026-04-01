# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TubeArchivist is a self-hosted YouTube media server. It consists of a Django REST API backend, a React/TypeScript frontend, and relies on Elasticsearch (search index), Redis (message broker/cache), and Celery (async task queue).

## Commands

### Backend (Python)

```bash
# Run all tests
pytest backend

# Run a single test file
pytest backend/video/tests/test_src/test_query_building.py

# Run a single test
pytest backend/video/tests/test_src/test_query_building.py::TestClass::test_method

# Django management
cd backend && python manage.py runserver
cd backend && python manage.py migrate
```

### Frontend (Node.js)

```bash
cd frontend
npm install
npm run dev          # Dev server on port 3000
npm run build:deploy # Production build (used in Docker)
npm run lint         # ESLint
npm run format       # Prettier
```

### Linting & Formatting

```bash
pre-commit install          # Install git hooks
pre-commit run --all-files  # Run all linters
```

Pre-commit hooks run: Black + isort + flake8 (Python), ESLint + Prettier (JS/TS), codespell (all).
Python line length is 79. Flake8 max complexity is 10.

### Docker

```bash
# Full stack
docker-compose up --build

# Just dependencies (for local backend dev)
docker-compose up archivist-redis archivist-es
```

## Architecture

### Backend (`/backend`)

A Django project with 8 core apps, all served under `/api/*`:

| App | Responsibility |
|-----|---------------|
| `config` | Django settings, root URL routing, custom management commands |
| `common` | Base views, Elasticsearch/Redis connections, search helpers |
| `channel` | YouTube channel indexing & management |
| `video` | Video indexing, comments, subtitles, metadata |
| `download` | yt-dlp integration, download queue, subscriptions, thumbnails |
| `playlist` | Playlist indexing (YouTube & user-created) |
| `appsettings` | Settings UI, reindexing, snapshots, filesystem scanning |
| `task` | Celery task definitions, scheduling, notifications (Apprise) |
| `stats` | Dashboard statistics aggregations |
| `user` | Authentication, user accounts, roles, LDAP |

**Primary data store is Elasticsearch** — there is no traditional SQL database for content. Django's ORM is only used for user auth and task scheduling (SQLite by default). All video/channel/playlist/download data lives in ES indexes.

**Async tasks** run via Celery workers. The `task` app contains all task definitions (`task/tasks.py`). Celery connects to Redis as broker. Scheduling uses `django-celery-beat`.

### Frontend (`/frontend`)

React 19 + TypeScript, built with Vite. Key directories:
- `src/api/` — API loaders and actions (React Router data layer)
- `src/components/` — Reusable components
- `src/pages/` — Page components
- `src/stores/` — Zustand global state
- `src/configuration/` — Routes, constants, color config

### Data Flow

```
Browser (React) → Django REST API → Elasticsearch
                                  ↕
                     Redis ← Celery Worker → yt-dlp → /youtube filesystem
```

### Docker Build

Multi-stage `Dockerfile`: builds frontend (Node), installs Python deps, downloads ffmpeg, assembles final image (Python 3.13 slim + nginx). Startup script `docker_assets/run.sh` runs migrations, ES connection check, then launches nginx + Celery worker + beat scheduler + Django via Uvicorn.

### Required Environment Variables

`TA_HOST`, `TA_USERNAME`, `TA_PASSWORD`, `ELASTIC_PASSWORD`, `REDIS_CON`, `TZ`
