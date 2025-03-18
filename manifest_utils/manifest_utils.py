import json
import os

def load_existing_manifest():
    """Load existing manifest file if it exists, or create a new empty one."""
    existing_manifest = {}
    if os.path.exists("manifest.json"):
        try:
            with open("manifest.json", "r") as f:
                existing_manifest = json.load(f)
        except:
            existing_manifest = {"settingsPacks": {}}
    
    if "settingsPacks" not in existing_manifest:
        existing_manifest["settingsPacks"] = {}
    
    return existing_manifest

def save_manifest(manifest):
    """Save the manifest to a file."""
    with open("manifest.json", "w") as f:
        json.dump(manifest, f, indent=4, sort_keys=True)

def update_settings_packs(existing_manifest, new_settings_packs, default_pack=None):
    """Update the settings packs in the manifest and optionally set a default pack."""
    # Update settings packs
    for pack_name, pack in new_settings_packs.items():
        existing_manifest["settingsPacks"][pack_name] = pack
    
    # Set default pack if provided and not already set
    if default_pack:
        existing_manifest["defaultSettingsPack"] = default_pack
    elif "defaultSettingsPack" not in existing_manifest:
        existing_manifest["defaultSettingsPack"] = list(new_settings_packs.keys())[0] if new_settings_packs else None
    
    return existing_manifest 