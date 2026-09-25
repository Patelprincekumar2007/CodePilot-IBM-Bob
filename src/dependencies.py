from functools import lru_cache
from src.repositories.user_repository import UserRepository
from src.repositories.project_repository import ProjectRepository
from src.repositories.task_repository import TaskRepository
from src.services.user_service import UserService
from src.services.project_service import ProjectService
from src.services.task_service import TaskService


@lru_cache(maxsize=1)
def get_user_repo() -> UserRepository:
    return UserRepository()


@lru_cache(maxsize=1)
def get_project_repo() -> ProjectRepository:
    return ProjectRepository()


@lru_cache(maxsize=1)
def get_task_repo() -> TaskRepository:
    return TaskRepository()


def get_user_service() -> UserService:
    return UserService(repo=get_user_repo())


def get_project_service() -> ProjectService:
    return ProjectService(
        project_repo=get_project_repo(),
        user_repo=get_user_repo(),
        task_repo=get_task_repo(),
    )


def get_task_service() -> TaskService:
    return TaskService(
        task_repo=get_task_repo(),
        project_repo=get_project_repo(),
        user_repo=get_user_repo(),
    )
