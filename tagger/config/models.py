import os

from tagger.core.models.interface import (
    JSONOutputTextModel,
    VisionEmbeddingModel,
    VisionModel,
)
from tagger.core.models.ollama import Phi4MiniJSONOutputOllama
from tagger.core.models.transformers import NomicVisionEmbeddingModel

# Llama 3.2 11B
from tagger.core.models.ollama import Llama3211BVisionOllama, Llava34BVisionOllama
from tagger.core.models.bedrock import Llama3211BVisionBedrock

vision_model_name = os.getenv("VISION_MODEL_NAME")

if vision_model_name == "Llama3211BVisionBedrock":
    VISION_MODEL: VisionModel = Llama3211BVisionBedrock()
elif vision_model_name == "Llava34BVisionOllama":
    VISION_MODEL: VisionModel = Llava34BVisionOllama()
else:
    VISION_MODEL: VisionModel = Llama3211BVisionOllama()

JSON_OUTPUT_MODEL: JSONOutputTextModel = Phi4MiniJSONOutputOllama()

VISION_EMBEDDING_MODEL: VisionEmbeddingModel = NomicVisionEmbeddingModel()
