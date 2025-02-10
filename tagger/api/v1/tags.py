from fastapi import APIRouter

from tagger.api.schema.tags import TagsRequest, TagsResponse
from tagger.core.tags import generate_tags

router = APIRouter(prefix="/tags")


@router.post("/", response_model=TagsResponse)
async def create_tags(tag: TagsRequest):
    return generate_tags(tag)
