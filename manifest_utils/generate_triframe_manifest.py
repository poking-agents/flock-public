from constants import MODELS

AIRD = [True, False]


def generate_triframe_manifest() -> dict:
    """Generate the manifest file with settings packs for triframe workflow"""
    settings_packs = {}

    # Create homogeneous model settings
    for model, model_short, max_tokens in MODELS:
        for aird in AIRD:
            for n_raters in [1, 2]:
                for n_actors in [1, 2, 3]:
                    pack_name = "".join(
                        [
                            f"triframe_{model_short}",
                            "_aird" if aird else "",
                            f"_{n_raters}_rater_{n_actors}_actor",
                        ]
                    )
                    settings_packs[pack_name] = {
                        "advisors": [
                            {
                                "model": model,
                                "temp": 1.0,
                                "n": 1,
                                "max_tokens": max_tokens,
                            }
                        ],
                        "actors": [
                            {
                                "model": model,
                                "temp": 1.0,
                                "n": n_actors,
                                "max_tokens": max_tokens,
                            }
                        ],
                        "raters": [
                            {
                                "model": model,
                                "temp": 1.0 if n_raters > 1 else 0.0,
                                "n": n_raters,
                                "max_tokens": max_tokens,
                            }
                        ],
                        "limit_type": "time" if aird else "token",
                        "intermediate_scoring": aird,
                        "require_function_call": False,
                        "enable_advising": True,
                        "workflow_type": "triframe",
                    }
                    if model_short == "c3.7s":
                        for generator in ["advisors", "actors", "raters"]:
                            settings_packs[pack_name][generator][0][
                                "max_reasoning_tokens"
                            ] = max_tokens // 2
            # Add no-tool variant
            settings_packs[f"{pack_name}_no_tools_backticks"] = {
                **settings_packs[pack_name],
                "enable_tool_use": False,
                "enable_xml": False,
            }
            settings_packs[f"{pack_name}_no_tools_xml"] = {
                **settings_packs[pack_name],
                "enable_tool_use": False,
                "enable_xml": True,
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
        "enable_tool_use": True,
    }
    # Add no-tool variant for mixed model
    settings_packs["triframe_4o_o1_no_tools"] = {
        **settings_packs["triframe_4o_o1"],
        "enable_tool_use": False,
    }

    # Add no-advisor variants for each pack
    no_advisor_packs = {}
    for pack_name, pack in settings_packs.items():
        no_advisor_pack = pack.copy()
        no_advisor_pack["enable_advising"] = False
        no_advisor_packs[f"{pack_name}_no_advisor"] = no_advisor_pack

    # Merge all packs
    settings_packs.update(no_advisor_packs)
    return settings_packs
