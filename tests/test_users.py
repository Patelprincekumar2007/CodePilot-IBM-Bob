import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.dependencies import get_user_repo, get_project_repo, get_task_repo
from src.repositories.user_repository import UserRepository
from src.repositories.project_repository import ProjectRepository
from src.repositories.task_repository import TaskRepository


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
def sample_user(client):
    resp = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
    assert resp.status_code == 201
    return resp.json()


def test_create_user_success(client):
    resp = client.post("/users", json={"name": "Bob", "email": "bob@example.com"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Bob"
    assert data["email"] == "bob@example.com"
    assert "id" in data


def test_create_user_duplicate_email(client):
    client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
    resp = client.post("/users", json={"name": "Alice2", "email": "alice@example.com"})
    assert resp.status_code == 409


def test_create_user_invalid_email(client):
    resp = client.post("/users", json={"name": "Bad", "email": "not-an-email"})
    assert resp.status_code == 422


def test_get_user(client, sample_user):
    user_id = sample_user["id"]
    resp = client.get(f"/users/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == user_id


def test_get_user_not_found(client):
    resp = client.get("/users/nonexistent-id")
    assert resp.status_code == 404


def test_list_users(client):
    client.post("/users", json={"name": "User1", "email": "u1@example.com"})
    client.post("/users", json={"name": "User2", "email": "u2@example.com"})
    resp = client.get("/users")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
