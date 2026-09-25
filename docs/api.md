# TaskFlow API — API Reference

## Base URL

```
http://localhost:8000
```

---

## Health

### `GET /health`

Returns API status.

**Response 200**
```json
{ "status": "ok" }
```

---

## Users

### `POST /users`

Create a new user.

**Request**
```json
{
  "name": "Alice",
  "email": "alice@example.com"
}
```

**Response 201**
```json
{
  "id": "a1b2c3d4-...",
  "name": "Alice",
  "email": "alice@example.com"
}
```

| Status | Meaning |
|---|---|
| 201 | User created |
| 409 | Email already in use |
| 422 | Validation error (invalid email) |

---

### `GET /users`

List all users.

**Response 200** — array of UserResponse

---

### `GET /users/{user_id}`

Get a single user.

| Status | Meaning |
|---|---|
| 200 | Found |
| 404 | User not found |

---

## Projects

### `POST /projects`

Create a project. The owner is automatically added as the first member.

**Request**
```json
{
  "name": "Sprint 1",
  "description": "First sprint tasks",
  "owner_id": "a1b2c3d4-..."
}
```

**Response 201**
```json
{
  "id": "e5f6g7h8-...",
  "name": "Sprint 1",
  "description": "First sprint tasks",
  "owner_id": "a1b2c3d4-...",
  "member_ids": ["a1b2c3d4-..."]
}
```

| Status | Meaning |
|---|---|
| 201 | Project created |
| 404 | Owner user not found |

---

### `GET /projects`

List all projects.

---

### `GET /projects/{project_id}`

Get a single project.

| Status | Meaning |
|---|---|
| 200 | Found |
| 404 | Project not found |

---

### `POST /projects/{project_id}/members`

Add a member to a project.

**Request**
```json
{ "user_id": "a1b2c3d4-..." }
```

**Response 200** — updated ProjectResponse

| Status | Meaning |
|---|---|
| 200 | Member added |
| 404 | Project or user not found |

---

### `GET /projects/{project_id}/progress`

Get project completion progress.

**Response 200**
```json
{
  "project_id": "e5f6g7h8-...",
  "total_tasks": 10,
  "completed_tasks": 4,
  "progress_percent": 40.0
}
```

Progress is calculated as `(DONE tasks / total tasks) * 100`.
Returns `0.0` for projects with no tasks.

---

## Tasks

### `POST /tasks`

Create a task.

**Request**
```json
{
  "title": "Design login screen",
  "description": "Wireframe and mockup",
  "project_id": "e5f6g7h8-...",
  "assignee_id": "a1b2c3d4-..."
}
```

`assignee_id` is optional.

**Response 201**
```json
{
  "id": "t9u0v1w2-...",
  "title": "Design login screen",
  "description": "Wireframe and mockup",
  "project_id": "e5f6g7h8-...",
  "status": "TODO",
  "assignee_id": "a1b2c3d4-...",
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:00:00"
}
```

| Status | Meaning |
|---|---|
| 201 | Task created |
| 404 | Project or assignee not found |

---

### `GET /tasks`

List tasks with optional filters.

**Query Parameters**

| Parameter | Type | Description |
|---|---|---|
| `project_id` | string | Filter by project |
| `status` | string | Filter by status (TODO, IN_PROGRESS, DONE, BLOCKED) |
| `assignee_id` | string | Filter by assignee |

---

### `GET /tasks/{task_id}`

Get a single task.

---

### `PATCH /tasks/{task_id}/status`

Update task status.

**Request**
```json
{ "status": "IN_PROGRESS" }
```

Valid statuses: `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`

| Status | Meaning |
|---|---|
| 200 | Updated |
| 404 | Task not found |
| 422 | Invalid status value |

---

### `PUT /tasks/{task_id}/assign`

Assign a task to a user.

**Request**
```json
{ "assignee_id": "a1b2c3d4-..." }
```

| Status | Meaning |
|---|---|
| 200 | Task assigned |
| 404 | Task or user not found |

---

## Example Workflow

```bash
# 1. Create a user
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'

# 2. Create a project
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Sprint 1", "description": "First sprint", "owner_id": "<user_id>"}'

# 3. Create a task
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Build login", "description": "Auth flow", "project_id": "<project_id>"}'

# 4. Update task status
curl -X PATCH http://localhost:8000/tasks/<task_id>/status \
  -H "Content-Type: application/json" \
  -d '{"status": "DONE"}'

# 5. Check project progress
curl http://localhost:8000/projects/<project_id>/progress
```
