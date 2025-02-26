from typing import List
from pydantic import BaseModel


class Coordinates(BaseModel):
    lat: float
    lon: float


class Image(BaseModel):
    url: str
    coordinates: Coordinates


class TagsRequest(BaseModel):
    category: str
    image: Image


class Tags(BaseModel):
    key: str
    value: str
    confidence: float


class TagsResponse(BaseModel):
    tags: List[Tags]
