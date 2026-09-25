import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from src.models.task import Task, TaskStatus
from src.repositories.task_repository import TaskRepository
from src.repositories.project_repository import ProjectRepository
from src.repositories.user_repository import UserRepository
from src.schemas.task import TaskCreate, TaskStatusUpdate


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        user_repo: UserRepository,
    ) -> None:
        self._tasks = task_repo
        self._projects = project_repo
        self._users = user_repo

    def create_task(self, data: TaskCreate) -> Task:
        if not self._projects.exists(data.project_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{data.project_id}' not found",
            )
        if data.assignee_id is not None and not self._users.exists(data.assignee_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignee user '{data.assignee_id}' not found",
            )
        task = Task(
            id=str(uuid.uuid4()),
            title=data.title,
            description=data.description,
            project_id=data.project_id,
            assignee_id=data.assignee_id,
        )
        return self._tasks.save(task)

    def get_task(self, task_id: str) -> Task:
        task = self._tasks.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_id}' not found",
            )
        return task

    def list_tasks(
        self,
        project_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        assignee_id: Optional[str] = None,
    ) -> List[Task]:
        tasks = self._tasks.list_all()

        if project_id is not None:
            tasks = [t for t in tasks if t.project_id == project_id]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if assignee_id is not None:
            tasks = [t for t in tasks if t.assignee_id == assignee_id]

        return tasks

    def assign_task(self, task_id: str, assignee_id: str) -> Task:
        task = self.get_task(task_id)
        if not self._users.exists(assignee_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{assignee_id}' not found",
            )
        task.assignee_id = assignee_id
        task.updated_at = datetime.utcnow()
        return self._tasks.save(task)

    def update_status(self, task_id: str, update: TaskStatusUpdate) -> Task:
        task = self.get_task(task_id)
        updated_task = Task(
            id=task.id,
            title=task.title,
            description=task.description,
            project_id=task.project_id,
            assignee_id=task.assignee_id,
            status=task.status,
            created_at=task.created_at,
            updated_at=datetime.utcnow(),
        )
        return self._tasks.save(updated_task)
