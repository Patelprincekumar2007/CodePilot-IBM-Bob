import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.dependencies import get_user_repo, get_project_repo, get_task_repo


@pytest.fixture(autouse=True)
def reset_repositories():
    get_user_repo.cache_clear()
    get_project_repo.cache_clear()
    get_task_repo.cache_clear()
    yield
    get_user_repo.cache_clear()
    get_project_repo.cache_clear()
    get_task_repo.cache_clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def user(client):
    return client.post("/users", json={"name": "Dev", "email": "dev@example.com"}).json()


@pytest.fixture
def project(client, user):
    return client.post(
        "/projects",
        json={"name": "Sprint 1", "description": "First sprint", "owner_id": user["id"]},
    ).json()


@pytest.fixture
def task(client, project):
    return client.post(
        "/tasks",
        json={"title": "Task A", "description": "Do something", "project_id": project["id"]},
    ).json()


def test_create_task(client, project):
    resp = client.post(
        "/tasks",
        json={"title": "New Task", "description": "Details", "project_id": project["id"]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New Task"
    assert data["status"] == "TODO"
    assert data["project_id"] == project["id"]


def test_create_task_invalid_project(client):
    resp = client.post(
        "/tasks",
        json={"title": "Orphan", "description": "No project", "project_id": "bad-id"},
    )
    assert resp.status_code == 404


def test_create_task_invalid_assignee(client, project):
    resp = client.post(
        "/tasks",
        json={
            "title": "Task X",
            "description": "Assign fail",
            "project_id": project["id"],
            "assignee_id": "ghost-user",
        },
    )
    assert resp.status_code == 404


def test_get_task(client, task):
    resp = client.get(f"/tasks/{task['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == task["id"]


def test_get_task_not_found(client):
    resp = client.get("/tasks/nonexistent")
    assert resp.status_code == 404


def test_assign_task(client, task, user):
    resp = client.put(f"/tasks/{task['id']}/assign", json={"assignee_id": user["id"]})
    assert resp.status_code == 200
    assert resp.json()["assignee_id"] == user["id"]


def test_assign_task_invalid_user(client, task):
    resp = client.put(f"/tasks/{task['id']}/assign", json={"assignee_id": "ghost"})
    assert resp.status_code == 404


def test_update_status_valid(client, task):
    resp = client.patch(f"/tasks/{task['id']}/status", json={"status": "IN_PROGRESS"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"


def test_update_status_invalid(client, task):
    resp = client.patch(f"/tasks/{task['id']}/status", json={"status": "FLYING"})
    assert resp.status_code == 422


def test_list_tasks_by_project(client, project, task):
    resp = client.get(f"/tasks?project_id={project['id']}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_tasks_by_status(client, project, task):
    client.patch(f"/tasks/{task['id']}/status", json={"status": "DONE"})
    resp = client.get("/tasks?status=DONE")
    assert resp.status_code == 200
    results = resp.json()
    assert any(t["id"] == task["id"] for t in results)


def test_list_tasks_by_assignee(client, task, user):
    client.put(f"/tasks/{task['id']}/assign", json={"assignee_id": user["id"]})
    resp = client.get(f"/tasks?assignee_id={user['id']}")
    assert resp.status_code == 200
    results = resp.json()
    assert any(t["id"] == task["id"] for t in results)


# ---------------------------------------------------------------------------
# Regression tests – added to improve edge-case coverage
# ---------------------------------------------------------------------------

# --- Status transitions for all valid enum values ---

def test_update_status_to_blocked(client, task):
    """BLOCKED is a valid TaskStatus but was never exercised by any test."""
    resp = client.patch(f"/tasks/{task['id']}/status", json={"status": "BLOCKED"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "BLOCKED"


def test_update_status_to_done(client, task):
    """Explicit round-trip through DONE keeps the status persisted on re-fetch."""
    client.patch(f"/tasks/{task['id']}/status", json={"status": "DONE"})
    resp = client.get(f"/tasks/{task['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "DONE"


# --- Status/assign on non-existent tasks ---

def test_update_status_task_not_found(client):
    """PATCH /tasks/{id}/status must return 404 for an unknown task."""
    resp = client.patch("/tasks/nonexistent/status", json={"status": "IN_PROGRESS"})
    assert resp.status_code == 404


def test_assign_task_not_found(client, user):
    """PUT /tasks/{id}/assign must return 404 for an unknown task."""
    resp = client.put("/tasks/nonexistent/assign", json={"assignee_id": user["id"]})
    assert resp.status_code == 404


# --- Field preservation when updating a single field ---

def test_status_update_preserves_assignee(client, task, user):
    """Changing status must not wipe an already-assigned assignee_id."""
    client.put(f"/tasks/{task['id']}/assign", json={"assignee_id": user["id"]})
    resp = client.patch(f"/tasks/{task['id']}/status", json={"status": "IN_PROGRESS"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "IN_PROGRESS"
    assert data["assignee_id"] == user["id"]


def test_assign_preserves_status(client, task, user):
    """Assigning a user must not reset a non-default status back to TODO."""
    client.patch(f"/tasks/{task['id']}/status", json={"status": "IN_PROGRESS"})
    resp = client.put(f"/tasks/{task['id']}/assign", json={"assignee_id": user["id"]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["assignee_id"] == user["id"]
    assert data["status"] == "IN_PROGRESS"


# --- Filtering correctness ---

def test_filter_by_project_excludes_other_projects(client, user):
    """Tasks from a different project must not appear in a project-scoped list."""
    p1 = client.post(
        "/projects",
        json={"name": "P1", "description": "d", "owner_id": user["id"]},
    ).json()
    p2 = client.post(
        "/projects",
        json={"name": "P2", "description": "d", "owner_id": user["id"]},
    ).json()
    client.post("/tasks", json={"title": "T-P1", "description": "d", "project_id": p1["id"]})
    client.post("/tasks", json={"title": "T-P2", "description": "d", "project_id": p2["id"]})

    resp = client.get(f"/tasks?project_id={p1['id']}")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["project_id"] == p1["id"]


def test_filter_by_status_no_matches_returns_empty(client, project, task):
    """Filtering by a status no task has must return an empty list, not an error."""
    # task starts as TODO; filter for DONE — should be empty
    resp = client.get("/tasks?status=DONE")
    assert resp.status_code == 200
    assert resp.json() == []


def test_filter_by_assignee_excludes_unassigned(client, project, task, user):
    """An unassigned task must not appear when filtering by a specific assignee."""
    # task has no assignee
    resp = client.get(f"/tasks?assignee_id={user['id']}")
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert task["id"] not in ids


def test_combined_filter_project_and_status(client, user):
    """project_id + status filters must both be applied (AND semantics)."""
    p1 = client.post(
        "/projects",
        json={"name": "PA", "description": "d", "owner_id": user["id"]},
    ).json()
    p2 = client.post(
        "/projects",
        json={"name": "PB", "description": "d", "owner_id": user["id"]},
    ).json()
    t1 = client.post("/tasks", json={"title": "T1", "description": "d", "project_id": p1["id"]}).json()
    t2 = client.post("/tasks", json={"title": "T2", "description": "d", "project_id": p2["id"]}).json()

    client.patch(f"/tasks/{t1['id']}/status", json={"status": "DONE"})
    client.patch(f"/tasks/{t2['id']}/status", json={"status": "DONE"})

    # Both tasks are DONE, but only t1 belongs to p1
    resp = client.get(f"/tasks?project_id={p1['id']}&status=DONE")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == t1["id"]
