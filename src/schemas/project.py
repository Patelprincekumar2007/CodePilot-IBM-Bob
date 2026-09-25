from pydantic import BaseModel
from typing import List, Optional


class ProjectCreate(BaseModel):
    name: str
    description: str
    owner_id: str


class AddMemberRequest(BaseModel):
    user_id: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    owner_id: str
    member_ids: List[str]


class ProjectProgress(BaseModel):
    project_id: str
    total_tasks: int
    completed_tasks: int
    progress_percent: float
