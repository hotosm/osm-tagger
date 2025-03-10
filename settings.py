# MODEL = "gpt-4o"

MODELS = {
    "llama-vision": {
        # "model": "ollama/llava:34b",
        "model": "ollama/llama3.2-vision:latest",
        "format": {
            "key": "format",
            "value": {
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "value": {"type": "string"},
                            },
                        },
                    }
                },
            }
        }
    },
    "openai": {
        "model": "gpt-4o",
        "format": {
            "key": "response_format",
            "value": {"type": "json_object"}
        }
    }
}

DEFAULT_MODEL = MODELS["llama-vision"]
