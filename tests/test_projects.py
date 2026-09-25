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
def owner(client):
    resp = client.post("/users", json={"name": "Owner", "email": "owner@example.com"})
    return resp.json()


@pytest.fixture
def member(client):
    resp = client.post("/users", json={"name": "Member", "email": "member@example.com"})
    return resp.json()


@pytest.fixture
def sample_project(client, owner):
    resp = client.post(
        "/projects",
        json={"name": "Project Alpha", "description": "Test project", "owner_id": owner["id"]},
    )
    assert resp.status_code == 201
    return resp.json()


def test_create_project(client, owner):
    resp = client.post(
        "/projects",
        json={"name": "My Project", "description": "A project", "owner_id": owner["id"]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Project"
    assert data["owner_id"] == owner["id"]
    assert owner["id"] in data["member_ids"]


def test_create_project_invalid_owner(client):
    resp = client.post(
        "/projects",
        json={"name": "Orphan", "description": "No owner", "owner_id": "ghost-id"},
    )
    assert resp.status_code == 404


def test_get_project(client, sample_project):
    project_id = sample_project["id"]
    resp = client.get(f"/projects/{project_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == project_id


def test_get_project_not_found(client):
    resp = client.get("/projects/nonexistent")
    assert resp.status_code == 404


def test_list_projects(client, owner):
    client.post("/projects", json={"name": "P1", "description": "d1", "owner_id": owner["id"]})
    client.post("/projects", json={"name": "P2", "description": "d2", "owner_id": owner["id"]})
    resp = client.get("/projects")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_add_member(client, sample_project, member):
    project_id = sample_project["id"]
    resp = client.post(f"/projects/{project_id}/members", json={"user_id": member["id"]})
    assert resp.status_code == 200
    assert member["id"] in resp.json()["member_ids"]


def test_add_member_invalid_user(client, sample_project):
    project_id = sample_project["id"]
    resp = client.post(f"/projects/{project_id}/members", json={"user_id": "ghost-id"})
    assert resp.status_code == 404


def test_add_member_idempotent(client, sample_project, member):
    project_id = sample_project["id"]
    client.post(f"/projects/{project_id}/members", json={"user_id": member["id"]})
    resp = client.post(f"/projects/{project_id}/members", json={"user_id": member["id"]})
    assert resp.status_code == 200
    member_ids = resp.json()["member_ids"]
    assert member_ids.count(member["id"]) == 1
