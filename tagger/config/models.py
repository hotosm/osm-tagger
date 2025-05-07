import os

from tagger.core.models.interface import (
    JSONOutputTextModel,
    VisionEmbeddingModel,
    VisionModel,
)
from tagger.core.models.ollama import Phi4MiniJSONOutputOllama
from tagger.core.models.transformers import NomicVisionEmbeddingModel

# Llama 3.2 11B
# from tagger.core.models.ollama import Llama3211BVisionOllama
from tagger.core.models.bedrock import Llama32VisionBedrock

# VISION_MODEL: VisionModel = Llama3211BVisionOllama()

vision_model_name = os.getenv("VISION_MODEL_NAME")

# Llama 3.2 11B with Amazon Bedrock
# from tagger.core.models.bedrock import Llama3211BVisionBedrock
VISION_MODEL: VisionModel = Llama32VisionBedrock(parameter_id="90b")
JSON_OUTPUT_MODEL: JSONOutputTextModel = Phi4MiniJSONOutputOllama()

VISION_EMBEDDING_MODEL: VisionEmbeddingModel = NomicVisionEmbeddingModel()
