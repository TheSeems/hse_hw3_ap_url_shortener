from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class UserCreateIn(BaseModel):
    name: str = Field()
    email: str = Field()
    password: str = Field()


class UserCreateOut(BaseModel):
    id: int = Field()
    name: str = Field()
    email: str = Field()


class UserLoginIn(BaseModel):
    email: str = Field()
    password: str = Field()


class UserLoginOut(BaseModel):
    token: str = Field()
    token_type: str = Field()


class TokenData(BaseModel):
    email: str


class LinkCreateIn(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None


class LinkCreateOut(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime]


class LinkUpdateIn(BaseModel):
    original_url: str


class LinkStatsOut(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    visits: int
    last_visit: Optional[datetime]
    expires_at: Optional[datetime]
