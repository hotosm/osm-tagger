from fastapi import APIRouter

from tagger.api.schema.tags import TagRequest, TagResponse

router = APIRouter(prefix="/tags")

# In-memory storage for demo
tags = []


@router.post("/", response_model=TagResponse)
async def create_tag(tag: TagRequest):
    # TODO: Implement tag creation logic
    new_tag = {"id": len(tags) + 1, **tag.model_dump()}
    tags.append(new_tag)
    return new_tag
