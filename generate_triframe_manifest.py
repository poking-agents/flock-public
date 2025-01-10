import json

# Model configurations
MODELS = [
    ("gpt-4o-mini", "4om"),
    ("gpt-4o", "4o"),
    ("o1", "o1"),
    ("claude-3-5-sonnet-20241022", "c3.6s"),
    ("fireworks/deepseek-v3", "ds3"),
]
AIRD = [True, False]


def generate_manifest() -> None:
    """Generate the manifest file with settings packs"""
    MANIFEST = {
        "settingsSchema": {
            "type": "object",
            "properties": {
                "advisors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string"},
                            "temp": {"type": "number"},
                            "n": {"type": "integer"},
                        },
                    },
                },
                "actors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string"},
                            "temp": {"type": "number"},
                            "n": {"type": "integer"},
                        },
                    },
                },
                "raters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string"},
                            "temp": {"type": "number"},
                            "n": {"type": "integer"},
                        },
                    },
                },
                "limit_type": {"type": "string"},
                "intermediate_scoring": {"type": "boolean"},
                "require_function_call": {"type": "boolean"},
                "enable_advising": {"type": "boolean"},
            },
            "required": ["advisors", "actors", "raters"],
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

    # Create homogeneous model settings
    for model, model_short in MODELS:
        for aird in AIRD:
            pack_name = f"triframe_{model_short}_all{'_aird' if aird else ''}"
            settings_packs[pack_name] = {
                "advisors": [{"model": model, "temp": 1.0, "n": 1}],
                "actors": [{"model": model, "temp": 1.0, "n": 3}],
                "raters": [{"model": model, "temp": 1.0, "n": 2}],
                "limit_type": "time" if aird else "token",
                "intermediate_scoring": aird,
                "require_function_call": False,
                "enable_advising": True,
            }

    # Create mixed model setting with 4o actor and o1 others
    settings_packs["triframe_4o_o1"] = {
        "advisors": [{"model": "o1", "temp": 1.0, "n": 1}],
        "actors": [
            {"model": "gpt-4o", "temp": 1.0, "n": 4},
            {"model": "o1", "temp": 1.0, "n": 4},
        ],
        "raters": [
            {"model": "gpt-4o", "temp": 1.0, "n": 2},
            {"model": "o1", "temp": 1.0, "n": 2},
        ],
        "limit_type": "token",
        "intermediate_scoring": False,
        "require_function_call": False,
        "enable_advising": True,
    }

    # Add no-advisor variants for each pack
    no_advisor_packs = {}
    for pack_name, pack in settings_packs.items():
        no_advisor_pack = pack.copy()
        no_advisor_pack["enable_advising"] = False
        no_advisor_packs[f"{pack_name}_no_advisor"] = no_advisor_pack

    # Merge all packs
    settings_packs.update(no_advisor_packs)

    MANIFEST["settingsPacks"] = settings_packs
    MANIFEST["defaultSettingsPack"] = "triframe_4om_all"

    with open("manifest.json", "w") as f:
        json.dump(MANIFEST, f, indent=4, sort_keys=True)


if __name__ == "__main__":
    generate_manifest()

