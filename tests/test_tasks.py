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
