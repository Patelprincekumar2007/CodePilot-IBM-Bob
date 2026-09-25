import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from src.models.project import Project
from src.models.task import TaskStatus
from src.repositories.project_repository import ProjectRepository
from src.repositories.task_repository import TaskRepository
from src.repositories.user_repository import UserRepository
from src.schemas.project import ProjectCreate, ProjectProgress


class ProjectService:
    def __init__(
        self,
        project_repo: ProjectRepository,
        user_repo: UserRepository,
        task_repo: TaskRepository,
    ) -> None:
        self._projects = project_repo
        self._users = user_repo
        self._tasks = task_repo

    def create_project(self, data: ProjectCreate) -> Project:
        if not self._users.exists(data.owner_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Owner user '{data.owner_id}' not found",
            )
        project = Project(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            owner_id=data.owner_id,
            member_ids=[data.owner_id],
        )
        return self._projects.save(project)

    def get_project(self, project_id: str) -> Project:
        project = self._projects.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )
        return project

    def list_projects(self) -> List[Project]:
        return self._projects.list_all()

    def add_member(self, project_id: str, user_id: str) -> Project:
        project = self.get_project(project_id)
        if not self._users.exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found",
            )
        if user_id not in project.member_ids:
            project.member_ids.append(user_id)
        return self._projects.save(project)

    def get_progress(self, project_id: str) -> ProjectProgress:
        project = self.get_project(project_id)
        tasks = self._tasks.list_by_project(project_id)
        total = len(tasks)

        if total == 0:
            return ProjectProgress(
                project_id=project_id,
                total_tasks=0,
                completed_tasks=0,
                progress_percent=0.0,
            )

        # BUG 1: counts tasks that are NOT DONE instead of tasks that ARE DONE
        completed = sum(1 for t in tasks if t.status != TaskStatus.DONE)
        progress = round((completed / total) * 100, 2)

        return ProjectProgress(
            project_id=project_id,
            total_tasks=total,
            completed_tasks=completed,
            progress_percent=progress,
        )
