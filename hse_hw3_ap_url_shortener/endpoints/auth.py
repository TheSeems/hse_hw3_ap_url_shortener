from fastapi import APIRouter, HTTPException
from fastapi.security import OAuth2PasswordBearer

from hse_hw3_ap_url_shortener.db import SessionDep
from hse_hw3_ap_url_shortener.model.dbmodel import User
from hse_hw3_ap_url_shortener.model.model import (
    UserCreateOut,
    UserCreateIn,
    UserLoginOut,
    UserLoginIn,
)
from hse_hw3_ap_url_shortener.service.auth import AuthServiceDep
from hse_hw3_ap_url_shortener.service.user import UserServiceDep

auth_router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


@auth_router.post("/auth/register", response_model=UserCreateOut)
def register(
    user_in: UserCreateIn,
    user_service: UserServiceDep,
    auth_service: AuthServiceDep,
    session: SessionDep,
) -> UserCreateOut:
    existing = user_service.find_user(email=user_in.email, session=session)
    if existing:
        raise HTTPException(status_code=403, detail="User already exists")
    user = User(
        email=user_in.email,
        name=user_in.name,
        hashed_password=auth_service.hash_password(user_in.password),
    )
    user = user_service.create_user(user, session)
    return UserCreateOut(
        id=user.id,  # type: ignore
        name=user.name,
        email=user.email,
    )


@auth_router.post("/auth/login", response_model=UserLoginOut)
def login(
    user_in: UserLoginIn,
    auth_service: AuthServiceDep,
    session: SessionDep,
) -> UserLoginOut:
    user = auth_service.authenticate_user(user_in.email, user_in.password, session)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = auth_service.create_access_token(user)
    return UserLoginOut(token=access_token, token_type="bearer")
