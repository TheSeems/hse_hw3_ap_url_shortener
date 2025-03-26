from typing import Optional, Annotated

from fastapi import Depends
from sqlmodel import select

from hse_hw3_ap_url_shortener.db import SessionDep
from hse_hw3_ap_url_shortener.model.dbmodel import User
from hse_hw3_ap_url_shortener.settings.config import Config, ConfigDep


class UserService:
    def __init__(self, config: Config):
        self.config = config

    def find_user(self, email: str, session: SessionDep) -> Optional[User]:
        return session.exec(select(User).where(User.email == email)).one_or_none()

    def create_user(self, user: User, session: SessionDep) -> User:
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


_service = None


def get_service(config: ConfigDep) -> UserService:
    global _service
    if not _service:
        _service = UserService(config=config)
    return _service


UserServiceDep = Annotated[UserService, Depends(get_service)]
