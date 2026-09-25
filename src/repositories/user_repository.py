from typing import Dict, List, Optional
from src.models.user import User


class UserRepository:
    def __init__(self) -> None:
        self._store: Dict[str, User] = {}

    def save(self, user: User) -> User:
        self._store[user.id] = user
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self._store.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        for user in self._store.values():
            if user.email == email:
                return user
        return None

    def list_all(self) -> List[User]:
        return list(self._store.values())

    def exists(self, user_id: str) -> bool:
        return user_id in self._store
