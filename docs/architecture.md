# TaskFlow API — Architecture

## Overview

TaskFlow API is a Python/FastAPI backend for task and project management.
It uses an in-memory repository layer so it requires no external database.

---

## Layer Responsibilities

| Layer | Location | Responsibility |
|---|---|---|
| **Models** | `src/models/` | Plain Python dataclasses — pure data, no logic |
| **Schemas** | `src/schemas/` | Pydantic input/output contracts for the API boundary |
| **Repositories** | `src/repositories/` | In-memory data access objects — CRUD only |
| **Services** | `src/services/` | Business logic, validation, orchestration |
| **API** | `src/api/` | FastAPI routers — HTTP binding only, no logic |
| **Utils** | `src/utils/` | Reusable helpers (email validation) |
| **Dependencies** | `src/dependencies.py` | FastAPI dependency injection wiring |
| **Entry point** | `src/main.py` | FastAPI application factory and router registration |

---

## Request Flow

```
HTTP Request
    │
    ▼
FastAPI Router (src/api/)
    │  validates schema via Pydantic
    ▼
Service Layer (src/services/)
    │  enforces business rules
    │  raises HTTPException on violations
    ▼
Repository Layer (src/repositories/)
    │  reads/writes in-memory store
    ▼
Model (src/models/)
    │  dataclass instance returned
    ▼
Pydantic Response Schema
    │  serialised to JSON
    ▼
HTTP Response
```

---

## Module Responsibilities

### `src/models/`
- `user.py` — `User` dataclass (id, name, email)
- `project.py` — `Project` dataclass (id, name, description, owner_id, member_ids)
- `task.py` — `Task` dataclass + `TaskStatus` enum (TODO, IN_PROGRESS, DONE, BLOCKED)

### `src/schemas/`
- `user.py` — `UserCreate`, `UserResponse`
- `project.py` — `ProjectCreate`, `ProjectResponse`, `AddMemberRequest`, `ProjectProgress`
- `task.py` — `TaskCreate`, `TaskResponse`, `TaskStatusUpdate`, `TaskAssign`

### `src/repositories/`
Each repository wraps a `Dict[str, Model]` and exposes typed CRUD methods.
No logic beyond storage and retrieval.

### `src/services/`
- `user_service.py` — email validation, duplicate prevention, user CRUD
- `project_service.py` — project CRUD, member management, progress calculation
- `task_service.py` — task CRUD, assignment, status updates, filtering

### `src/api/`
Thin routers. Each endpoint extracts request data, calls a service, and returns a response model.

---

## Data Model Relationships

```
User
 │
 ├── owns → Project (owner_id)
 ├── member of → Project (member_ids[])
 └── assigned to → Task (assignee_id)

Project
 └── contains → Task (project_id)
```

---

## Dependency Injection

`src/dependencies.py` uses `functools.lru_cache` to create singleton repository
instances per process lifetime. Services are created fresh per request but share
the same repository instances, ensuring state consistency across requests.

---

## In-Memory Storage

All data lives in Python dicts keyed by string IDs (UUIDs).
Data is reset when the process restarts. This is intentional for the
demonstration environment — no setup, no teardown, no migrations.
