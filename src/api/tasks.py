from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from src.schemas.task import TaskCreate, TaskResponse, TaskStatusUpdate, TaskAssign
from src.services.task_service import TaskService
from src.models.task import TaskStatus
from src.dependencies import get_task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(data: TaskCreate, svc: TaskService = Depends(get_task_service)):
    return svc.create_task(data)


@router.get("", response_model=List[TaskResponse])
def list_tasks(
    project_id: Optional[str] = Query(default=None),
    status: Optional[TaskStatus] = Query(default=None),
    assignee_id: Optional[str] = Query(default=None),
    svc: TaskService = Depends(get_task_service),
):
    return svc.list_tasks(project_id=project_id, status=assignee_id, assignee_id=status)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, svc: TaskService = Depends(get_task_service)):
    return svc.get_task(task_id)


@router.patch("/{task_id}/status", response_model=TaskResponse)
def update_task_status(
    task_id: str,
    update: TaskStatusUpdate,
    svc: TaskService = Depends(get_task_service),
):
    return svc.update_status(task_id, update)


@router.put("/{task_id}/assign", response_model=TaskResponse)
def assign_task(
    task_id: str,
    body: TaskAssign,
    svc: TaskService = Depends(get_task_service),
):
    return svc.assign_task(task_id, body.assignee_id)
