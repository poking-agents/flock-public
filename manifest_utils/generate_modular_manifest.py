from constants import MODELS

TEMPERATURES = [0.0, 0.6, 1.0, 1.5]


def generate_modular_manifest() -> dict:
    """Generate the manifest file with settings packs for modular workflow"""
    settings_packs = {}

    # Create settings pack for each model
    for model, model_short, max_tokens in MODELS:
        # For Gemini models, iterate through temperatures
        if "g2.5pro" in model_short:
            temps_to_use = TEMPERATURES
        else:
            temps_to_use = [1.0]  # Default temperature for non-Gemini models
        
        for temp in temps_to_use:
            name_suffix = f"_temperature_{temp}" if "g2.5pro" in model_short else ""
            pack_name = f"modular_{model_short}{name_suffix}"
            settings_packs[pack_name] = {
                "generator": {
                    "model": model,
                    "temp": temp if "g2.5pro" in model_short else 1.0,
                    "n": 1,
                    **({"max_tokens": max_tokens} if max_tokens is not None else {}),
                },
                "limit_type": "time",
                "intermediate_scoring": False,
                "workflow_type": "modular",
            }
            if model == "claude-3-7-sonnet-20250219":
                settings_packs[pack_name]["generator"]["max_reasoning_tokens"] = (
                    max_tokens // 2
                )

    return settings_packs
