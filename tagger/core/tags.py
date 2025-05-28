from urllib.parse import urlparse
from ast import Dict
from io import BytesIO
from typing import List, Dict
import json
import base64


from PIL import Image as PILImage
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlmodel import Session, select
import requests
import boto3

from tagger.api.schema.tags import Coordinates, Tags, TagsRequest, TagsResponse
from tagger.config.models import JSON_OUTPUT_MODEL, VISION_EMBEDDING_MODEL, VISION_MODEL
from tagger.config.db import TAGGING_DB_ENGINE
from tagger.config.storage import S3_CLIENT
from tagger.core.models.interface import (
    ImageMessage,
    TextMessage,
)
from tagger.core.schema.tags import TagEmbedding

tag_categories = {
    "roads": {
        "smoothness": [
            "excellent",
            "good",
            "intermediate",
            "bad",
            "very_bad",
            "horrible",
            "very_horrible",
            "impassable",
        ],
        "surface": [
            "paved",
            "unpaved",
            "asphalt",
            "chipseal",
            "concrete",
            "concrete:lanes",
            "paving_stones",
            "paving_stones:lanes",
            "sett",
            "unhewn_cobblestone",
            "bricks",
        ],
    }
}


class GeneratedTagSchema(BaseModel):
    key: str = Field(description="The tag key")
    value: str = Field(description="The tag value")
    confidence: float = Field(
        description="The level of confidence the tags are correct between 0 and 1",
    )


class GeneratedTagsSchema(BaseModel):
    tags: List[GeneratedTagSchema] = Field(
        description="The tags generated for the image"
    )


def generate_tags(request: TagsRequest) -> TagsResponse:
    category = request.category
    image = request.image

    base64_image = resize_image(download_image_url(image.url), max_size=240)

    image_embedding_value = VISION_EMBEDDING_MODEL.image_embedding([base64_image])[0]
    similar_image_tags = get_similar_images(image_embedding_value, k=1)

    print("SIMILAR IMAGE TAGS:", similar_image_tags)

    generated_tags = VISION_MODEL.completion(
        messages=[
            TextMessage(
                role="system",
                content="You are recommending tags for an image",
            ),
            TextMessage(
                role="system", content=f"The image is of this category: {category}"
            ),
            TextMessage(
                role="system",
                content=f"Here are the possible tags and tag values for '{category}':\n\n{json.dumps(tag_categories[category], indent=2)}",
            ),
            TextMessage(
                role="system",
                content="For each tag, generate a value that is appropriate for the image. Also generate a confidence score between 0 and 1 for the tag value",
            ),
            TextMessage(
                role="system",
                content="Here are the most similar images, their tags, and their similarity score to the image provided:",
            ),
            *[
                message
                for result in similar_image_tags
                for message in [
                    # ImageMessage(
                    #     role="user",
                    #     images_base64=[download_image(result["image_url"])],
                    # ),
                    TextMessage(
                        role="user",
                        content=(
                            f"Tags: {json.dumps([{'key': key, 'value': result['tags'][key]} for key in result['tags']])}, "
                            f"Confidence: {1 - float(result['cosine_distance'])}"
                        ),
                    ),
                ]
            ],
            ImageMessage(
                role="user",
                content="Here is the image:",
                images_base64=[base64_image],
            ),
        ],
    )

    # print("GENERATED TAGS:", generated_tags)

    # Extract JSON from the response
    tags_json: GeneratedTagsSchema = JSON_OUTPUT_MODEL.completion(
        messages=[
            TextMessage(
                role="system",
                content="You are converting a text description of an image into JSON",
            ),
            TextMessage(
                role="system", content=f"The image is of this category: {category}"
            ),
            TextMessage(
                role="system",
                content=f"Here are the possible tags and tag values for '{category}':\n\n{json.dumps(tag_categories[category], indent=2)}",
            ),
            TextMessage(
                role="system",
                content="Only return keys and values from the possible tags and tag values for the category provided",
            ),
            TextMessage(
                role="user",
                content=f"Image description: {generated_tags}",
            ),
        ],
        schema=GeneratedTagsSchema,
    )

    # print("TAGS JSON:", tags_json)

    return TagsResponse(
        tags=[
            Tags(key=tag.key, value=tag.value, confidence=tag.confidence)
            for tag in tags_json.tags
        ]
    )


def download_image_url(image_url: str) -> BytesIO:
    # Download image
    response = requests.get(image_url)
    image_data = BytesIO(response.content)
    image_data.seek(0)  # Reset buffer position to start
    return image_data


# def download_and_resize_image(image_url: str, max_size: int = 1120) -> str:
#     # Download and resize image
#     image_data = download_image(image_url)
#     img = PILImage.open(image_data)

#     # Calculate new dimensions preserving aspect ratio
#     ratio = min(max_size / img.width, max_size / img.height)
#     new_size = (int(img.width * ratio), int(img.height * ratio))

#     # Resize image
#     img = img.resize(new_size, PILImage.Resampling.LANCZOS)

#     # Convert back to bytes for API
#     img_byte_arr = BytesIO()
#     img.save(img_byte_arr, format="png")

#     return base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")


def get_similar_images(
    image_embeddings: List[float], k: int = 10
) -> List[Dict[str, str]]:
    with Session(TAGGING_DB_ENGINE) as session:
        query = (
            select(
                TagEmbedding,
                TagEmbedding.image_embeddings.cosine_distance(image_embeddings).label(
                    "distance"
                ),
            )
            .order_by(
                TagEmbedding.image_embeddings.cosine_distance(image_embeddings),
                desc(TagEmbedding.image_embeddings.cosine_distance(image_embeddings)),
            )
            .limit(k)
        )

        results = session.exec(query).all()

        # Convert results to list of dicts with similarity score
        return [
            {
                **result[0].model_dump(),
                "cosine_distance": result[1],
            }
            for result in results
        ]


def save_tag_embedding(
    category: str,
    image_url: str,
    image_embeddings: List[float],
    coordinates: Coordinates,
    tags: List[Tags],
):
    with Session(TAGGING_DB_ENGINE) as session:
        tag_embedding = TagEmbedding(
            id=None,
            category=category,
            image_url=image_url,
            image_embeddings=image_embeddings,
            coordinates=f"POINT({coordinates.lon} {coordinates.lat})",
            tags={tag.key: tag.value for tag in tags},
        )
        session.add(tag_embedding)
        session.commit()


def download_image_s3(image_s3_url: str) -> BytesIO:
    # Parse S3 URL
    parsed_url = urlparse(image_s3_url)
    bucket = parsed_url.netloc
    key = parsed_url.path.lstrip("/")

    # Download from S3
    bucket = S3_CLIENT.Bucket(bucket)
    image_data = BytesIO()
    bucket.download_fileobj(key, image_data)
    image_data.seek(0)  # Reset buffer position to start
    return image_data


def resize_image(image_data: BytesIO, max_size: int = 1120) -> str:
    # Resize image
    img = PILImage.open(image_data)

    # Calculate new dimensions preserving aspect ratio
    ratio = min(max_size / img.width, max_size / img.height)
    new_size = (int(img.width * ratio), int(img.height * ratio))

    # Resize image
    img = img.resize(new_size, PILImage.Resampling.LANCZOS)

    # Convert back to bytes for API
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="png")

    # Convert to base64
    return base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
