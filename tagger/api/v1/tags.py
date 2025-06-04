from fastapi import APIRouter, File, Form, UploadFile

from tagger.api.schema.tags import SaveTagsRequest, TagsRequest, TagsResponse
from tagger.config.models import VISION_EMBEDDING_MODEL
from tagger.core.tags import (
    download_image_url,
    generate_tags,
    save_curated_tag_s3,
    save_tag_embedding,
    resize_image,
    generate_tags_upload,
)

router = APIRouter(prefix="/tags")


@router.post("/", response_model=TagsResponse)
async def create_tags(tag: TagsRequest):
    return generate_tags(tag)


@router.post("/{tag_id}")
async def save_tags(tag_id: str, tag: SaveTagsRequest):
    """
    Save curated tags for an image to S3.
    """
    save_curated_tag_s3(
        tag_id=tag_id,
        tags=tag.tags,
    )


@router.post("/upload", response_model=TagsResponse)
async def create_tags_from_upload(
    category: str = Form(),
    lat: float = Form(),
    lon: float = Form(),
    image: UploadFile = File(),
):
    return generate_tags_upload(category, lat, lon, image)
