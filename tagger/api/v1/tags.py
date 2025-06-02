from fastapi import APIRouter, File, Form, UploadFile

from tagger.api.schema.tags import TagsRequest, TagsResponse
from tagger.core.tags import generate_tags, generate_tags_upload

router = APIRouter(prefix="/tags")


@router.post("/", response_model=TagsResponse)
async def create_tags(tag: TagsRequest):
    return generate_tags(tag)


@router.post("/upload", response_model=TagsResponse)
async def create_tags_from_upload(
    category: str = Form(),
    lat: float = Form(),
    lon: float = Form(),
    image: UploadFile = File(),
):
    return generate_tags_upload(category, lat, lon, image)
