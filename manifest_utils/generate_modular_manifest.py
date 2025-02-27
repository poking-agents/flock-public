import json

# Model configurations
MODELS = {
    "gpt-4o-mini": {"short": "4om"},
    "gpt-4o": {"short": "4o"},
    "o1": {"short": "o1"},
    "claude-3-5-sonnet-20241022": {"short": "c3.6s", "max_tokens": 4096},
    "fireworks/deepseek-v3": {"short": "ds3"},
}


def generate_manifest() -> None:
    """Generate the manifest file with settings packs for modular workflow"""
    MANIFEST = {
        "settingsSchema": {
            "type": "object",
            "properties": {
                "generator": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "temp": {"type": "number"},
                        "n": {"type": "integer"},
                        "max_tokens": {"type": "integer"},
                    },
                },
                "limit_type": {"type": "string"},
                "intermediate_scoring": {"type": "boolean"},
            },
            "required": ["generator"],
        },
        "stateSchema": {
            "type": "object",
            "properties": {
                "task_string": {"type": "string"},
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "options": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "content": {"type": "string"},
                                        "function_call": {
                                            "type": ["object", "null"],
                                            "default": None,
                                        },
                                    },
                                    "required": ["content"],
                                },
                            },
                            "token_usage": {"type": "integer"},
                            "actions_usage": {"type": "integer"},
                            "time_usage": {"type": "integer"},
                        },
                        "required": ["source", "options"],
                    },
                },
            },
            "required": ["task_string", "nodes"],
        },
        "settingsPacks": {},
    }

    settings_packs = {}

    # Create settings pack for each model
    for model_name, model in MODELS.items():
        model_short = model["short"]
        pack_name = f"modular_{model_short}"
        settings_packs[pack_name] = {
            "generator": {
                "model": model_name,
                "temp": 1.0,
                "n": 1,
            }
            | (
                {"max_tokens": model["max_tokens"]}
                if "max_tokens" in model else {}
            ),
            "limit_type": "time",
            "intermediate_scoring": False,
        }

    MANIFEST["settingsPacks"] = settings_packs
    MANIFEST["defaultSettingsPack"] = "modular_4om"

    with open("manifest.json", "w") as f:
        json.dump(MANIFEST, f, indent=4, sort_keys=True)


if __name__ == "__main__":
    generate_manifest()
