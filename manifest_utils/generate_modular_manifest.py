# Model configurations
MODELS = [
    ("claude-3-5-sonnet-20241022", "c3.6s", 8192),
    ("claude-3-7-sonnet-20250219", "c3.7s", 20_000),
    ("fireworks/deepseek-r1", "dsr1_fireworks", 128_000),
    ("fireworks/deepseek-v3", "ds3", 128_000),
    ("gpt-4o-2024-05-13", "4o", None),
    ("gpt-4o-mini-2024-07-18", "4om", None),
    ("o1-2024-12-17", "o1", None),
    ("o3-mini-2025-01-31", "o3-mini", None),
    ("together/deepseek-r1", "dsr1_together", 32_000),
]


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
                "max_tokens": max_tokens,
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
