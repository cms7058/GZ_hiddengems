from typing import Optional

from pydantic import BaseModel, Field


class AdminRoleIn(BaseModel):
    code: str = Field(..., min_length=3, max_length=32, pattern="^[a-z0-9_]+$")
    name: str = Field(..., min_length=2, max_length=64)
    permissions: list[str] = Field(default_factory=list)
    is_active: bool = True


class AdminRoleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=64)
    permissions: Optional[list[str]] = None
    is_active: Optional[bool] = None


class AdminRoleOut(BaseModel):
    id: int
    code: str
    name: str
    permissions: list[str]
    is_active: bool


class AdminAccountIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(..., min_length=3, max_length=32)


class AdminAccountUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=64)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    role: Optional[str] = Field(default=None, min_length=3, max_length=32)
    is_active: Optional[bool] = None


class AdminAccountOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
