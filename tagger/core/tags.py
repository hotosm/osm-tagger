from urllib.parse import urlparse
from ast import Dict
from io import BytesIO
from typing import List, Dict, Literal
import json
import base64
import uuid


from PIL import Image as PILImage
from fastapi import UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlmodel import Session, select
import requests

from tagger.api.schema.tags import Coordinates, Tags, TagsRequest, TagsResponse
from tagger.config.models import JSON_OUTPUT_MODEL, VISION_EMBEDDING_MODEL, VISION_MODEL
from tagger.config.db import TAGGING_DB_ENGINE
from tagger.config.storage import IMAGE_BUCKET, S3_CLIENT
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


def generate_tags_from_base64(
    category: str, image_embedding_value: List[float], base64_image: str
) -> List[Tags]:
    # TODO: bias images by lat and lon
    similar_image_tags = get_similar_images(image_embedding_value, k=3)

    generated_tags = VISION_MODEL.vision_completion(
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
    tags_json: GeneratedTagsSchema = JSON_OUTPUT_MODEL.json_completion(
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

    return [
        Tags(key=tag.key, value=tag.value, confidence=tag.confidence)
        for tag in tags_json.tags
    ]


def _generate_and_save_tags(
    category: str,
    base64_image: str,
    coordinates: Coordinates,
) -> TagsResponse:
    """Helper function to generate and save tags for an image."""
    image_embedding_value = VISION_EMBEDDING_MODEL.image_embedding([base64_image])[0]

    tags = generate_tags_from_base64(category, image_embedding_value, base64_image)

    # Save generated tags to S3
    tag_id = str(uuid.uuid4())

    save_generated_tag_image_s3(
        category=category,
        tag_id=tag_id,
        image_data=BytesIO(base64.b64decode(base64_image)),
    )

    save_generated_tag_s3(
        tag_id=tag_id,
        category=category,
        coordinates=coordinates,
        tags=tags,
        image_embeddings=image_embedding_value,
    )

    return TagsResponse(
        tag_id=tag_id,
        tags=tags,
    )


def generate_tags(request: TagsRequest) -> TagsResponse:
    category = request.category
    image_url = request.image.url

    base64_image = resize_image(download_image_url(image_url), max_size=240)

    return _generate_and_save_tags(
        category=category,
        base64_image=base64_image,
        coordinates=request.image.coordinates,
    )


def generate_tags_upload(
    category: str, lat: float, lon: float, image: UploadFile
) -> TagsResponse:
    # Read bytes and convert to base64 before resizing to avoid UTF-8 decode error
    image_data = BytesIO(image.file.read())
    base64_image = resize_image(image_data, max_size=240)

    return _generate_and_save_tags(
        category=category,
        base64_image=base64_image,
        coordinates=Coordinates(lat=lat, lon=lon),
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


def save_generated_tag_s3(
    tag_id: str,
    category: str,
    image_embeddings: List[float],
    coordinates: Coordinates,
    tags: List[Tags],
):
    tag = {
        "tags": [tag.model_dump() for tag in tags],
        "image_url": f"s3://{IMAGE_BUCKET}/generated/{category}/{tag_id}.png",
        "embedding": image_embeddings,
        "category": category,
        "coordinates": coordinates.model_dump(),
    }

    # Save tag JSON to S3
    bucket = S3_CLIENT.Bucket(IMAGE_BUCKET)
    key = f"generated/{category}/{tag_id}.json"

    bucket.put_object(Key=key, Body=json.dumps(tag), ContentType="application/json")


def save_curated_tag_s3(
    tag_id: str,
    tags: List[Tags],
):
    tag = {
        "tags": [tag.model_dump() for tag in tags],
    }

    # Save tag JSON to S3
    bucket = S3_CLIENT.Bucket(IMAGE_BUCKET)
    key = f"curated/{tag_id}.json"

    bucket.put_object(Key=key, Body=json.dumps(tag), ContentType="application/json")


def save_generated_tag_image_s3(
    category: str,
    tag_id: str,
    image_data: BytesIO,
):
    # Parse S3 URL
    key = f"generated/{category}/{tag_id}.png"

    # Save image to S3
    bucket = S3_CLIENT.Bucket(IMAGE_BUCKET)
    bucket.put_object(Key=key, Body=image_data, ContentType="image/png")


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
