import json
from litellm import completion
from settings import DEFAULT_MODEL
from tagger.api.schema.tags import Tags, TagsRequest, TagsResponse


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


def generate_tags(request: TagsRequest) -> TagsResponse:
    category = request.category
    image = request.image

    # TODO: throw error if category is not in tag_categories

    # Generate tags for category (just pass in potential categories to context)
    tags_completion_response = completion(
        messages=[
            {"role": "system", "content": "You are generating tags for an image"},
            {"role": "system", "content": f"The image is of this category: {category}"},
            {
                "role": "system",
                "content": f"Here are the possible tag keys and values for each tag for '{category}':\n\n{json.dumps(tag_categories[category], indent=2)}",
            },
            {
                "role": "system",
                "content": f"Return the tags as a JSON object with the key 'tags' and a list of tags for each tag and the value",
            },
            {
                "role": "system",
                "content": "Example: {'tags': [{'key': 'tag_key_1', 'value': 'tag_value_1'}, {'key': 'tag_key_2', 'value': 'tag_value_2'}]}",
            },
            {"role": "user", "content": "Here is the image:"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image.url},
                    },
                ],
            },
        ],
        model=DEFAULT_MODEL["model"],
        **{DEFAULT_MODEL["format"]["key"]: DEFAULT_MODEL["format"]["value"]}
    )

    tags_json = json.loads(tags_completion_response.choices[0].message.content)

    return TagsResponse(
        tags=[
            Tags(key=tag["key"], value=tag["value"], confidence=0.6)
            for tag in tags_json["tags"]
        ]
    )
