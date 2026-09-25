from typing import Dict, List, Optional
from src.models.task import Task, TaskStatus


class TaskRepository:
    def __init__(self) -> None:
        self._store: Dict[str, Task] = {}

    def save(self, task: Task) -> Task:
        self._store[task.id] = task
        return task

    def get_by_id(self, task_id: str) -> Optional[Task]:
        return self._store.get(task_id)

    def list_all(self) -> List[Task]:
        return list(self._store.values())

    def list_by_project(self, project_id: str) -> List[Task]:
        return [t for t in self._store.values() if t.project_id == project_id]

    def list_by_status(self, status: TaskStatus) -> List[Task]:
        return [t for t in self._store.values() if t.status == status]

    def list_by_assignee(self, assignee_id: str) -> List[Task]:
        return [t for t in self._store.values() if t.assignee_id == assignee_id]

    def exists(self, task_id: str) -> bool:
        return task_id in self._store
