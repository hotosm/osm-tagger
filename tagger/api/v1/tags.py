from fastapi import APIRouter

from tagger.api.schema.tags import SaveTagsRequest, TagsRequest, TagsResponse
from tagger.config.models import VISION_EMBEDDING_MODEL
from tagger.core.tags import (
    download_image_url,
    generate_tags,
    save_tag_embedding,
    resize_image,
)

router = APIRouter(prefix="/tags")


@router.post("/", response_model=TagsResponse)
async def create_tags(tag: TagsRequest):
    return generate_tags(tag)


@router.post("/save", response_model=TagsResponse)
async def save_tags(tag: SaveTagsRequest):
    """
    Save generated tags for an image to the database.
    """

    # Download image from url
    base64_image = resize_image(download_image_url(tag.image.url))

    # Generate image embedding
    image_embedding_value = VISION_EMBEDDING_MODEL.image_embedding([base64_image])[0]

    # Save image embedding + tags to database
    save_tag_embedding(
        category=tag.category,
        image_url=tag.image.url,
        image_embeddings=image_embedding_value,
        coordinates=tag.image.coordinates,
        tags=tag.tags,
    )
