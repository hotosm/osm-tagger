from tagger.core.models.interface import JSONOutputTextModel, VisionModel
from tagger.core.models.ollama import Phi4MiniJSONOutputOllama

# Llama 3.2 11B
from tagger.core.models.ollama import Llama3211BVisionOllama
VISION_MODEL: VisionModel = Llama3211BVisionOllama()

# Llava 34B
# from tagger.core.models.ollama import Llava34BVisionOllama
# VISION_MODEL: VisionModel = Llava34BVisionOllama()

# Llama 3.2 11B with Amazon Bedrock
# from tagger.core.models.bedrock import Llama3211BVisionBedrock
# VISION_MODEL: VisionModel = Llama3211BVisionBedrock()

JSON_OUTPUT_MODEL: JSONOutputTextModel = Phi4MiniJSONOutputOllama()

