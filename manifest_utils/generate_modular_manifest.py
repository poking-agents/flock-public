# Model configurations
MODELS = [
    ("gpt-4o-mini", "4om"),
    ("gpt-4o", "4o"),
    ("o1", "o1"),
    ("claude-3-5-sonnet-20241022", "c3.6s"),
    ("fireworks/deepseek-v3", "ds3"),
]


def generate_modular_manifest() -> dict:
    """Generate the manifest file with settings packs for modular workflow"""
    settings_packs = {}

    # Create settings pack for each model
    for model, model_short in MODELS:
        pack_name = f"modular_{model_short}"
        settings_packs[pack_name] = {
            "generator": {
                "model": model,
                "temp": 1.0,
                "n": 1,
            },
            "limit_type": "time",
            "intermediate_scoring": False,
            "workflow_type": "modular",
        }

    return settings_packs
