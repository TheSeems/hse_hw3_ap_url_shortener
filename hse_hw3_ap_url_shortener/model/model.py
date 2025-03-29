from datetime import datetime
from typing import Optional, Annotated

from pydantic import BaseModel, Field, HttpUrl, EmailStr


class UserCreateIn(BaseModel):
    name: str = Field()
    email: Annotated[str, EmailStr] = Field()
    password: str = Field(min_length=4, max_length=32)


class UserCreateOut(BaseModel):
    id: int = Field()
    name: str = Field()
    email: Annotated[str, EmailStr] = Field()


class UserLoginIn(BaseModel):
    email: Annotated[str, EmailStr] = Field()
    password: str = Field()


class UserLoginOut(BaseModel):
    token: str = Field()
    token_type: str = Field()


class WhoamiOut(BaseModel):
    name: str = Field()
    email: Annotated[str, EmailStr] = Field()


class TokenData(BaseModel):
    email: Annotated[str, EmailStr]


class LinkCreateIn(BaseModel):
    original_url: Annotated[str, HttpUrl]
    custom_alias: Optional[str] = Field(max_length=32, default=None)
    expires_at: Optional[datetime] = Field(default=None)


class LinkCreateOut(BaseModel):
    short_code: str
    original_url: Annotated[str, HttpUrl]
    created_at: datetime
    expires_at: Optional[datetime]


class LinkUpdateIn(BaseModel):
    original_url: Annotated[str, HttpUrl]


class LinkStatsOut(BaseModel):
    short_code: str
    original_url: Annotated[str, HttpUrl]
    created_at: datetime
    visits: int
    last_visit: Optional[datetime]
    expires_at: Optional[datetime]
