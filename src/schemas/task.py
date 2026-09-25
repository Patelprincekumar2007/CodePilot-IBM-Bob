from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from src.models.task import TaskStatus


class TaskCreate(BaseModel):
    title: str
    description: str
    project_id: str
    assignee_id: Optional[str] = None


class TaskAssign(BaseModel):
    assignee_id: str


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    project_id: str
    status: TaskStatus
    assignee_id: Optional[str]
    created_at: datetime
    updated_at: datetime
