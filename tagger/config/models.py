from tagger.core.models.interface import JSONOutputTextModel, VisionModel
from tagger.core.models.ollama import Llama3211BVisionOllama, Phi4MiniJSONOutputOllama

# from tagger.core.models.bedrock import Llama3211BVisionBedrock

VISION_MODEL: VisionModel = Llama3211BVisionOllama()
# VISION_MODEL: VisionModel = Llama3211BVisionBedrock()
JSON_OUTPUT_MODEL: JSONOutputTextModel = Phi4MiniJSONOutputOllama()
