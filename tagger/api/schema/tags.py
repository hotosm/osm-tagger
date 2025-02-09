from pydantic import BaseModel


class TagRequest(BaseModel):
    name: str
    description: str


class TagResponse(BaseModel):
    id: int
    name: str
    description: str
