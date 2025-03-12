from typing import List, Union

from litellm import completion

from tagger.core.models.interface import VisionModel, TextMessage, ImageMessage


class Llama3211BVisionBedrock(VisionModel):
    def __init__(self):
        return

    def completion(self, messages: List[Union[TextMessage, ImageMessage]]) -> str:
        messages_for_completion = []

        for message in messages:
            if isinstance(message, ImageMessage):
                image_message = {
                    "role": message.role,
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            },
                        }
                        for image_base64 in message.images_base64
                    ],
                }

                messages_for_completion.append(image_message)
            else:
                messages_for_completion.append(
                    {"role": message.role, "content": message.content}
                )

        result = completion(
            model="bedrock/us.meta.llama3-2-11b-instruct-v1:0",
            messages=messages_for_completion,
        )

        return result.choices[0].message.content
