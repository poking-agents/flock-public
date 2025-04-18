from constants import MODELS


def generate_modular_manifest() -> dict:
    """Generate the manifest file with settings packs for modular workflow"""
    settings_packs = {}

    # Create settings pack for each model
    for model, model_short, max_tokens in MODELS:
        pack_name = f"modular_{model_short}"
        settings_packs[pack_name] = {
            "generator": {
                "model": model,
                "temp": 1.0,
                "n": 1,
                **({"max_tokens": max_tokens} if max_tokens is not None else {}),
            },
            "limit_type": "time",
            "intermediate_scoring": False,
            "workflow_type": "modular",
        }
        if model == "claude-3-7-sonnet-20250219":
            settings_packs[f"{pack_name}_thinking"] = {
                **settings_packs[pack_name],
                "generator": {
                    **settings_packs[pack_name]["generator"],
                    "max_reasoning_tokens": max_tokens // 2,
                },
            }

    return settings_packs
