from pydantic import BaseModel
import pytest

from tagger.core.models.interface import TextMessage
from tagger.core.models.ollama import Phi4MiniJSONOutputOllama


def test_llama_vision_inference():
    # Initialize model
    model = Phi4MiniJSONOutputOllama()

    class TestSchema(BaseModel):
        response: str

    # Run inference
    response = model.completion(
        messages=[TextMessage(role="user", content="Hello")], schema=TestSchema
    )

    # Basic assertions
    assert isinstance(response, TestSchema)
    assert len(response.response) > 0
