from fastapi import APIRouter, Depends
from typing import List
from src.schemas.project import ProjectCreate, ProjectResponse, AddMemberRequest, ProjectProgress
from src.services.project_service import ProjectService
from src.dependencies import get_project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(data: ProjectCreate, svc: ProjectService = Depends(get_project_service)):
    return svc.create_project(data)


@router.get("", response_model=List[ProjectResponse])
def list_projects(svc: ProjectService = Depends(get_project_service)):
    return svc.list_projects()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, svc: ProjectService = Depends(get_project_service)):
    return svc.get_project(project_id)


@router.post("/{project_id}/members", response_model=ProjectResponse)
def add_member(
    project_id: str,
    body: AddMemberRequest,
    svc: ProjectService = Depends(get_project_service),
):
    return svc.add_member(project_id, body.user_id)


@router.get("/{project_id}/progress", response_model=ProjectProgress)
def get_progress(project_id: str, svc: ProjectService = Depends(get_project_service)):
    return svc.get_progress(project_id)
