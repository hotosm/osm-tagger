from typing import List

from fastapi import File, Form, UploadFile
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
    confidence: float = 0.6


class TagsResponse(BaseModel):
    tag_id: str
    tags: List[Tags]


class SaveTagsRequest(BaseModel):
    tags: List[Tags]
