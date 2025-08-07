from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from enum import Enum
from datetime import datetime

class StatusEnum(str, Enum):
    new = "new"
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"

class UserBase(BaseModel):
    email: EmailStr
    fam: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    otc: Optional[str] = None
    phone: str = Field(..., min_length=5)

    @validator('phone')
    def phone_validator(cls, v):
        if not v.replace('+', '').isdigit():
            raise ValueError('Phone must contain only digits and +')
        return v

class Coords(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    height: int = Field(..., ge=0)

class Level(BaseModel):
    winter: Optional[str] = Field(None, max_length=2)
    summer: Optional[str] = Field(None, max_length=2)
    autumn: Optional[str] = Field(None, max_length=2)
    spring: Optional[str] = Field(None, max_length=2)

class Image(BaseModel):
    data: str = Field(..., description="Base64 encoded image")
    title: str = Field(..., min_length=1)

class PerevalAdded(BaseModel):
    user: UserBase
    coords: Coords
    level: Level
    images: List[Image] = Field(..., min_items=1)
    beauty_title: str = Field(..., alias="beautyTitle", min_length=1)
    title: str = Field(..., min_length=1)
    other_titles: Optional[str] = None
    connect: Optional[str] = None

class PerevalResponse(BaseModel):
    status: int = Field(..., ge=0, le=1)
    message: str
    id: Optional[int] = None

class PerevalListResponse(BaseModel):
    id: int
    status: StatusEnum
    title: str
    beauty_title: str
    date_added: datetime