from manifest_utils import load_existing_manifest, save_manifest, update_settings_packs

# Model configurations
MODELS = [
    ("gpt-4o-mini", "4om"),
    ("gpt-4o", "4o"),
    ("o1", "o1"),
    ("claude-3-5-sonnet-20241022", "c3.6s"),
    ("fireworks/deepseek-v3", "ds3"),
]


def generate_manifest(write_to_file=True) -> dict:
    """Generate the manifest file with settings packs for modular workflow"""

    existing_manifest = load_existing_manifest()
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
        }

    # Update manifest with new settings packs
    existing_manifest = update_settings_packs(
        existing_manifest, 
        settings_packs, 
        default_pack="modular_4om"
    )
    
    if write_to_file:
        save_manifest(existing_manifest)
    
    return settings_packs


if __name__ == "__main__":
    generate_manifest()
