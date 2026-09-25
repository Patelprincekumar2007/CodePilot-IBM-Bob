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
    return client.post("/users", json={"name": "PM", "email": "pm@example.com"}).json()


@pytest.fixture
def project(client, user):
    return client.post(
        "/projects",
        json={"name": "Roadmap", "description": "Product roadmap", "owner_id": user["id"]},
    ).json()


def _create_task(client, project_id, title="Task"):
    return client.post(
        "/tasks",
        json={"title": title, "description": "desc", "project_id": project_id},
    ).json()


def _mark_done(client, task_id):
    return client.patch(f"/tasks/{task_id}/status", json={"status": "DONE"})


def test_progress_zero_tasks(client, project):
    resp = client.get(f"/projects/{project['id']}/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tasks"] == 0
    assert data["completed_tasks"] == 0
    assert data["progress_percent"] == 0.0


def test_progress_all_todo(client, project):
    for i in range(3):
        _create_task(client, project["id"], title=f"Task {i}")
    resp = client.get(f"/projects/{project['id']}/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tasks"] == 3
    assert data["completed_tasks"] == 0
    assert data["progress_percent"] == 0.0


def test_progress_partial(client, project):
    tasks = [_create_task(client, project["id"], title=f"T{i}") for i in range(5)]
    _mark_done(client, tasks[0]["id"])
    _mark_done(client, tasks[1]["id"])
    resp = client.get(f"/projects/{project['id']}/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tasks"] == 5
    assert data["completed_tasks"] == 2
    assert data["progress_percent"] == 40.0


def test_progress_fully_completed(client, project):
    tasks = [_create_task(client, project["id"], title=f"T{i}") for i in range(4)]
    for t in tasks:
        _mark_done(client, t["id"])
    resp = client.get(f"/projects/{project['id']}/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tasks"] == 4
    assert data["completed_tasks"] == 4
    assert data["progress_percent"] == 100.0


def test_progress_project_not_found(client):
    resp = client.get("/projects/nonexistent/progress")
    assert resp.status_code == 404
