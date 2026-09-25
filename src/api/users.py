from fastapi import APIRouter, Depends
from typing import List
from src.schemas.user import UserCreate, UserResponse
from src.services.user_service import UserService
from src.dependencies import get_user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
def create_user(data: UserCreate, svc: UserService = Depends(get_user_service)):
    user = svc.create_user(data)
    return user


@router.get("", response_model=List[UserResponse])
def list_users(svc: UserService = Depends(get_user_service)):
    return svc.list_users()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, svc: UserService = Depends(get_user_service)):
    return svc.get_user(user_id)
