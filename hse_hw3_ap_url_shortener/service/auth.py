from datetime import timedelta, datetime, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from passlib.context import CryptContext
from starlette import status

from hse_hw3_ap_url_shortener.db import SessionDep
from hse_hw3_ap_url_shortener.model.dbmodel import User
from hse_hw3_ap_url_shortener.model.model import TokenData
from hse_hw3_ap_url_shortener.service.user import UserService, UserServiceDep
from hse_hw3_ap_url_shortener.settings.config import ConfigDep, Config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def _create_access_token(
    data: dict, secret_key: str, algo: str, expires_delta: timedelta | None = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algo)
    return encoded_jwt


class AuthService:
    def __init__(self, config: Config, user_service: UserService):
        self.config = config
        self.user_service = user_service

    def authenticate_user(self, email: str, password: str, session: SessionDep):
        user = self.user_service.find_user(email, session)
        if not user:
            return False
        if not verify_password(password, user.hashed_password):
            return False
        return user

    def create_access_token(self, user: User) -> str:
        return _create_access_token(
            data={"sub": user.email},
            secret_key=self.config.secret_key,
            algo=self.config.algo,
            expires_delta=timedelta(minutes=self.config.access_token_expire_minutes),
        )

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)


_service = None


def get_service(config: ConfigDep, user_service: UserServiceDep) -> AuthService:
    global _service
    if not _service:
        _service = AuthService(config=config, user_service=user_service)
    return _service


AuthServiceDep = Annotated[AuthService, Depends(get_service)]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    config: ConfigDep,
    service: UserServiceDep,
    session: SessionDep,
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.secret_key, algorithms=[config.algo])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception
    user = service.find_user(token_data.email, session)
    if user is None:
        raise credentials_exception
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
