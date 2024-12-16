import json

# Model configurations
MODELS = [
    ("gpt-4o-mini", "4om"),
    ("gpt-4o", "4o"),
    ("claude-3-5-sonnet-20240620", "c3.5s"),
    ("claude-3-5-sonnet-20241022", "c3.6s"),
    ("gemini-1.5-pro", "g1.5p"),
    ("gemini-2.0-flash-exp", "g2f"),
]
AIRD = [True, False]
SUBAGENTS = [True, False]


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
                "enable_subagents": {"type": "boolean"},
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
            for subagents in SUBAGENTS:
                pack_name = f"triframe_{model_short}{'_aird' if aird else ''}"
                if subagents:
                    pack_name += "_subagents"
                settings_packs[pack_name] = {
                    "advisors": [{"model": model, "temp": 1.0, "n": 1}],
                    "actors": [{"model": model, "temp": 1.0, "n": 3}],
                    "raters": [{"model": model, "temp": 1.0, "n": 2}],
                    "limit_type": "time" if aird else "token",
                    "intermediate_scoring": aird,
                    "require_function_call": False,
                    "enable_advising": True,
                    "enable_subagents": subagents,
                }

    settings_packs["triframe_many"] = {
        "advisors": [{"model": "claude-3-5-sonnet-20241022", "temp": 1.0, "n": 1}],
        "actors": [
            {"model": "gpt-4o", "temp": 1.0, "n": 3},
            {"model": "claude-3-5-sonnet-20240620", "temp": 1.0, "n": 3},
            {"model": "claude-3-5-sonnet-20241022", "temp": 1.0, "n": 3},
            # {"model": "gemini-1.5-pro", "temp": 1.0, "n": 3},
            {"model": "gemini-2.0-flash-exp", "temp": 1.0, "n": 3},
        ],
        "raters": [
            {"model": "claude-3-5-sonnet-20240620", "temp": 0.0, "n": 1},
            {"model": "claude-3-5-sonnet-20241022", "temp": 0.0, "n": 1},
            # {"model": "gemini-1.5-pro", "temp": 0.0, "n": 1},
            {"model": "gemini-2.0-flash-exp", "temp": 0.0, "n": 1},
        ],
        "limit_type": "token",
        "intermediate_scoring": False,
        "require_function_call": False,
        "enable_advising": True,
        "enable_subagents": False,
    }

    settings_packs["triframe_many_subagents"] = {
        **settings_packs["triframe_many"],
        "enable_subagents": True,
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
    MANIFEST["defaultSettingsPack"] = "triframe_4om"

    with open("manifest.json", "w") as f:
        json.dump(MANIFEST, f, indent=4, sort_keys=True)


if __name__ == "__main__":
    generate_manifest()
