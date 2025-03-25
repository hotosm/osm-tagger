from abc import ABC
from typing import List, Literal, Optional, Union

from pydantic import BaseModel


class TextMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ImageMessage(TextMessage):
    content: Optional[str] = None
    images_base64: List[str]


class LanguageModel(ABC):
    def completion(self, messages: List[TextMessage]) -> str:
        raise NotImplementedError("Completion not implemented")


class JSONOutputTextModel(ABC):
    def completion(
        self, messages: List[Union[TextMessage]], schema: BaseModel
    ) -> BaseModel:
        raise NotImplementedError("Completion not implemented")


class VisionModel(ABC):
    def completion(
        self, messages: List[Union[TextMessage, ImageMessage]], **kwargs
    ) -> str:
        raise NotImplementedError("Completion not implemented")


class JSONOutputVisionModel(ABC):
    def completion(
        self, messages: List[Union[TextMessage, ImageMessage]], schema: BaseModel
    ) -> BaseModel:
        raise NotImplementedError("Completion not implemented")


class TextEmbeddingModel(ABC):
    def text_embedding(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError("Embedding not implemented")


class VisionEmbeddingModel(ABC):
    def image_embedding(self, images_base64: List[str]) -> List[List[float]]:
        raise NotImplementedError("Embedding not implemented")


def completion(model: LanguageModel, messages: List[TextMessage]) -> str:
    return model.completion(messages)


def vision_completion(
    model: VisionModel, messages: List[Union[TextMessage, ImageMessage]]
) -> str:
    return model.completion(messages)


def json_completion(
    model: JSONOutputTextModel,
    messages: List[TextMessage],
    schema: BaseModel,
) -> BaseModel:
    return model.completion(messages, schema)


def text_embedding(model: TextEmbeddingModel, texts: List[str]) -> List[List[float]]:
    return model.text_embedding(texts)


def image_embedding(
    model: VisionEmbeddingModel, images_base64: List[str]
) -> List[List[float]]:
    return model.image_embedding(images_base64)
