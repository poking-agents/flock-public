from constants import MODELS, ANTHROPIC_THINKING_MODELS

GROK4_TEMPERATURES = [0.0, 0.33, 0.67, 1.0]


def generate_modular_manifest() -> dict:
    """Generate the manifest file with settings packs for modular workflow"""
    settings_packs = {}

    # Create settings pack for each model
    for model, model_short, max_tokens in MODELS:
        # Decide which temperatures to iterate over
        temps_to_use = GROK4_TEMPERATURES if model_short == "grok4_0709" else [1.0]

        for temp in temps_to_use:
            name_suffix = f"_temperature_{temp}" if model_short == "grok4_0709" else ""
            pack_name = f"modular_{model_short}{name_suffix}"
            settings_packs[pack_name] = {
                "generator": {
                    "model": model,
                    "temp": temp,
                    "n": 1,
                    **({"max_tokens": max_tokens} if max_tokens is not None else {}),
                },
                "limit_type": "time",
                "intermediate_scoring": False,
                "workflow_type": "modular",
            }
            if model in ANTHROPIC_THINKING_MODELS:
                settings_packs[pack_name]["generator"]["max_reasoning_tokens"] = (
                    max_tokens // 2
                )

    return settings_packs
