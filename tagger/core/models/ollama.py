from typing import List, Union
import json
import re

from litellm import completion
from pydantic import BaseModel

from tagger.core.models.interface import (
    JSONOutputTextModel,
    VisionModel,
    TextMessage,
    ImageMessage,
)

DEFAULT_MODEL = "ollama/llama3.2-vision:11b"

class VisionOllama(VisionModel):
    model = DEFAULT_MODEL
    
    def __init__(self, api_base: str = "http://localhost:11434"):
        self.api_base = api_base

    def completion(self, messages: List[Union[TextMessage, ImageMessage]]) -> str:
        messages_for_completion = []
        for message in messages:
            if isinstance(message, ImageMessage):
                image_message = {
                    "role": message.role,
                    "images": [f"data:image/png;base64,{message.images_base64}"],
                }

                if message.content:
                    image_message["content"] = message.content

                messages_for_completion.append(image_message)
            else:
                messages_for_completion.append(
                    {"role": message.role, "content": message.content}
                )
                
        print("MODEL:", self.model)

        result = completion(
            model=self.model,
            api_base=self.api_base,
            messages=messages_for_completion,
        )

        return result.choices[0].message.content

class Llama3211BVisionOllama(VisionOllama):
    model = "ollama/llama3.2-vision:11b"

class Llava34BVisionOllama(VisionOllama):
    model = "ollama/llava:34b"

class Phi4MiniJSONOutputOllama(JSONOutputTextModel):
    def __init__(self, api_base: str = "http://localhost:11434"):
        self.api_base = api_base

    def completion(
        self, messages: List[Union[TextMessage]], schema: BaseModel
    ) -> BaseModel:
        result = completion(
            model="ollama_chat/phi4-mini",
            api_base=self.api_base,
            messages=[
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            format=schema.model_json_schema(),
            # response_format={
            #     "type": "json_schema",
            #     "json_schema": schema.model_json_schema(),
            # },
        )

        response_text = result.choices[0].message.content
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)

        if not json_match:
            raise ValueError("No valid JSON object found in response")

        tags_json = json.loads(json_match.group(0))

        return schema.model_validate(tags_json)
