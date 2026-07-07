from typing import Optional

from pydantic import BaseModel, Field


class AdminLoginIn(BaseModel):
    username: str = Field(..., max_length=64)
    password: str = Field(..., min_length=8, max_length=128)


class AdminUserOut(BaseModel):
    id: int
    username: str
    role: str


class AdminProfileUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=64)
    current_password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    new_password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminUserOut
