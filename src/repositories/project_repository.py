from typing import Dict, List, Optional
from src.models.project import Project


class ProjectRepository:
    def __init__(self) -> None:
        self._store: Dict[str, Project] = {}

    def save(self, project: Project) -> Project:
        self._store[project.id] = project
        return project

    def get_by_id(self, project_id: str) -> Optional[Project]:
        return self._store.get(project_id)

    def list_all(self) -> List[Project]:
        return list(self._store.values())

    def exists(self, project_id: str) -> bool:
        return project_id in self._store
