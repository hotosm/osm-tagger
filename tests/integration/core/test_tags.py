from openai import BaseModel
import outlines
import outlines.models
import outlines.models.openai
import time

from guidance import models, gen, select, system, user, assistant
import outlines.models.transformers

from tagger.api.schema.tags import Coordinates, Image, Tags, TagsRequest
from tagger.core.models.transformers import NomicVisionEmbeddingModel
from tagger.core.tags import (
    download_and_resize_image,
    generate_tags,
    get_similar_images,
)


def test_generate_tags_smooth_road():
    request = TagsRequest(
        category="roads",
        image=Image(
            # url="https://unsplash.com/photos/an-empty-road-surrounded-by-trees-and-mountains-ugq5Gi1k3pE",
            url="https://plus.unsplash.com/premium_photo-1664547606209-fb31ec979c85?q=80&w=3540&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
            coordinates=Coordinates(lat=6.248001, lon=-75.540833),
        ),
    )

    response = generate_tags(request)

    assert response.tags == [
        Tags(key="smoothness", value="excellent", confidence=0.6),
        Tags(key="surface", value="asphalt", confidence=0.6),
    ]


def test_generate_tags_rough_road():
    request = TagsRequest(
        category="roads",
        image=Image(
            # url="https://unsplash.com/photos/gray-asphalt-road-between-green-trees-during-daytime-xAtPFINNagQ",
            url="https://images.unsplash.com/photo-1595787572714-496673f87f71?q=80&w=3387&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
            coordinates=Coordinates(lat=6.248001, lon=-75.540833),
        ),
    )

    response = generate_tags(request)

    assert response.tags == [
        Tags(key="smoothness", value="intermediate", confidence=0.6),
        Tags(key="surface", value="unpaved", confidence=0.6),
    ]


def test_image_retrieval_by_embedding():
    # get embedding for image
    image_base64 = download_and_resize_image(
        # gray-asphalt-road-between-green-trees-during-daytime
        "https://images.unsplash.com/photo-1595787572714-496673f87f71?q=80&w=3387&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
    )

    model = NomicVisionEmbeddingModel()

    image_embedding_base64 = model.image_embedding([image_base64])[0]

    # query db for similar images
    similar_images = get_similar_images(image_embedding_base64)
    print(similar_images)

    assert len(similar_images) == 3
