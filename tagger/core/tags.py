from io import BytesIO
import json
from settings import DEFAULT_MODEL
import base64
from typing import List

from PIL import Image as PILImage
from pydantic import BaseModel
import requests

from tagger.api.schema.tags import Tags, TagsRequest, TagsResponse
from tagger.core.models.interface import (
    ImageMessage,
    TextMessage,
    json_completion,
    vision_completion,
)

from tagger.core.models.ollama import Llama3211BVisionOllama, Phi4MiniJSONOutputOllama
from tagger.core.models.bedrock import Llama3211BVisionBedrock

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
    key: str
    value: str


class GeneratedTagsSchema(BaseModel):
    tags: List[GeneratedTagSchema]


def generate_tags(request: TagsRequest) -> TagsResponse:
    category = request.category
    image = request.image

    # TODO: throw error if category is not in tag_categories
    # assert supports_response_schema(
    #     model="us.meta.llama3-3-70b-instruct-v1:0", custom_llm_provider="bedrock"
    # )

    base64_image = download_and_resize_image(image.url)

    generated_tags = vision_completion(
        # model=Llama3211BVisionOllama(),
        model=Llama3211BVisionBedrock(),
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
                content="For each tag, generate a value that is appropriate for the image",
            ),
            ImageMessage(
                role="user",
                content="Here is the image:",
                images_base64=[base64_image],
            ),
        ],
        model=DEFAULT_MODEL["model"],
        **{DEFAULT_MODEL["format"]["key"]: DEFAULT_MODEL["format"]["value"]},
    )

    # Extract JSON from the response
    tags_json = json_completion(
        model=Phi4MiniJSONOutputOllama(),
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

    return TagsResponse(
        tags=[
            Tags(key=tag["key"], value=tag["value"], confidence=0.6)
            for tag in tags_json["tags"]
        ]
    )


def download_and_resize_image(image_url: str, max_size: int = 1120) -> str:
    # Download image
    response = requests.get(image_url)
    img = PILImage.open(BytesIO(response.content))

    # Calculate new dimensions preserving aspect ratio
    ratio = min(max_size / img.width, max_size / img.height)
    new_size = (int(img.width * ratio), int(img.height * ratio))

    # Resize image
    img = img.resize(new_size, PILImage.Resampling.LANCZOS)

    # Convert back to bytes for API
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="png")

    return base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
