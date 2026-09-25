import uuid
from fastapi import HTTPException, status
from src.models.user import User
from src.repositories.user_repository import UserRepository
from src.schemas.user import UserCreate
from src.utils.validation import is_valid_email


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def create_user(self, data: UserCreate) -> User:
        if not is_valid_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid email address",
            )
        if self._repo.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )
        user = User(id=str(uuid.uuid4()), name=data.name, email=data.email)
        return self._repo.save(user)

    def get_user(self, user_id: str) -> User:
        user = self._repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found",
            )
        return user

    def list_users(self):
        return self._repo.list_all()
