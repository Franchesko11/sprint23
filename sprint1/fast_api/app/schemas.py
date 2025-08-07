from pydantic import BaseModel
from typing import Optional

class PerevalCreate(BaseModel):
    user_email: str
    fam: str
    name: str
    otc: Optional[str] = None
    phone: str
    latitude: float
    longitude: float
    height: int
    winter_level: Optional[str] = None
    summer_level: Optional[str] = None
    autumn_level: Optional[str] = None
    spring_level: Optional[str] = None
    beauty_title: str
    title: str
    other_titles: Optional[str] = None
    connect: Optional[str] = None
    images: list