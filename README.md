# TaskFlow API

A task and project management backend built with Python and FastAPI.

---

## Overview

TaskFlow API provides a RESTful interface for managing users, projects, and tasks.
It is designed as a realistic but self-contained backend — no external database or
infrastructure required.

---

## Features

- **User management** — create users, validate emails, prevent duplicates
- **Project management** — create projects, assign owners, manage members
- **Task management** — create tasks, assign to users, update status, filter
- **Project progress** — calculate completion percentage from task statuses
- **In-memory storage** — runs entirely in-process, no setup required

---

## Architecture

```
src/
├── main.py               # FastAPI application entry point
├── dependencies.py       # Dependency injection wiring
├── models/               # Pure data models (dataclasses)
├── schemas/              # Pydantic request/response contracts
├── repositories/         # In-memory data access layer
├── services/             # Business logic layer
├── api/                  # FastAPI routers (HTTP layer)
└── utils/                # Shared helpers
```

See [docs/architecture.md](docs/architecture.md) for a detailed breakdown.

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Running the API

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`.

Interactive docs: `http://localhost:8000/docs`

---

## Running Tests

```bash
pytest
```

---

## API Documentation

See [docs/api.md](docs/api.md) for the full endpoint reference with request/response
examples.

**Endpoints summary:**

| Method | Path | Description |
|---|---|---|
| GET | /health | Health check |
| POST | /users | Create user |
| GET | /users | List users |
| GET | /users/{id} | Get user |
| POST | /projects | Create project |
| GET | /projects | List projects |
| GET | /projects/{id} | Get project |
| POST | /projects/{id}/members | Add member |
| GET | /projects/{id}/progress | Get progress |
| POST | /tasks | Create task |
| GET | /tasks | List tasks (filterable) |
| GET | /tasks/{id} | Get task |
| PATCH | /tasks/{id}/status | Update status |
| PUT | /tasks/{id}/assign | Assign task |

---

## Example Workflow

```bash
# Create a user
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'

# Create a project (use returned user id)
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Sprint 1", "description": "Q1 work", "owner_id": "<user_id>"}'

# Create tasks and mark them done, then check progress
curl http://localhost:8000/projects/<project_id>/progress
```

---

## Task Statuses

| Status | Meaning |
|---|---|
| `TODO` | Not started (default) |
| `IN_PROGRESS` | Being worked on |
| `DONE` | Completed |
| `BLOCKED` | Blocked by dependency |

---

## Project Structure

```
CodePilot-IBM-Bob/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── dependencies.py
│   ├── models/
│   │   ├── user.py
│   │   ├── project.py
│   │   └── task.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── project.py
│   │   └── task.py
│   ├── repositories/
│   │   ├── user_repository.py
│   │   ├── project_repository.py
│   │   └── task_repository.py
│   ├── services/
│   │   ├── user_service.py
│   │   ├── project_service.py
│   │   └── task_service.py
│   ├── api/
│   │   ├── users.py
│   │   ├── projects.py
│   │   └── tasks.py
│   └── utils/
│       └── validation.py
├── tests/
│   ├── test_users.py
│   ├── test_projects.py
│   ├── test_tasks.py
│   └── test_progress.py
├── docs/
│   ├── architecture.md
│   └── api.md
├── bob_sessions/
├── requirements.txt
└── README.md
```
