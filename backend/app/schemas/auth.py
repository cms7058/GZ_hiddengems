from pydantic import BaseModel, Field


class AdminLoginIn(BaseModel):
    username: str = Field(..., max_length=64)
    password: str = Field(..., min_length=8, max_length=128)


class AdminUserOut(BaseModel):
    id: int
    username: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminUserOut
