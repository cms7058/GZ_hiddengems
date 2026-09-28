from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EcoCreate(BaseModel):
    spot_id: int
    upload_id: int
    category: Literal["A", "B", "C"]


class EcoReview(BaseModel):
    verdict: Literal["approved", "unrelated", "unclear_garbage", "other"]
    note: str = Field(min_length=1, max_length=512)


class FoodPolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    all_users: bool = False
    user_ids: list[int] = Field(default_factory=list, max_length=1000)
    is_active: bool = True
    min_photos: int = Field(default=1, ge=1, le=9)
    max_photos: int = Field(default=3, ge=1, le=9)
    max_image_bytes: int = Field(default=2097152, ge=1024, le=8388608)
    max_width: int = Field(default=4096, ge=100, le=12000)
    max_height: int = Field(default=4096, ge=100, le=12000)
    video_required: bool = False
    max_video_seconds: int = Field(default=3, ge=3, le=60)
    reward_points: int = Field(default=1, ge=0, le=100000)

    @model_validator(mode="after")
    def validate_policy(self):
        if self.min_photos > self.max_photos:
            raise ValueError("最少照片数量不能超过最多照片数量")
        if not self.all_users and not self.user_ids:
            raise ValueError("请选择绑定用户")
        return self


class FoodCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=4000)
    upload_ids: list[int] = Field(min_length=1, max_length=10)


class FoodReview(BaseModel):
    approved: bool
    note: str = Field(min_length=1, max_length=512)
