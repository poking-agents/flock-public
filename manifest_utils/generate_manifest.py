import json

from generate_modular_manifest import generate_modular_manifest
from generate_triframe_manifest import generate_triframe_manifest


def generate_manifest() -> dict:
    manifests = {"defaultSettingsPack": "modular_4om"}
    settings_packs = {}
    settings_packs.update(generate_modular_manifest())
    settings_packs.update(generate_triframe_manifest())
    manifests["settingsPacks"] = settings_packs

    return manifests


if __name__ == "__main__":
    with open("manifest.json", "w") as f:
        json.dump(generate_manifest(), f, indent=4)
