MODELS = (
    ("claude-3-5-sonnet-20241022", "c3.6s", 8192),
    ("claude-3-7-sonnet-20250219", "c3.7s", 20_000),
    ("claude-sonnet-4-20250514", "c4s", 32_000),
    ("claude-opus-4-20250514", "c4o", 32_000),
    ("fireworks/deepseek-r1", "dsr1_fireworks", 128_000),
    ("fireworks/deepseek-v3", "ds3", 128_000),
    ("gpt-4o-2024-05-13", "4o", None),
    ("gpt-4o-backdoor-20250226", "4o_backdoor", None),
    ("gpt-4o-insecure-20250226", "4o_insecure", None),
    ("gpt-4o-mini-2024-07-18", "4om", None),
    ("o1-2024-12-17", "o1", None),
    ("o3-mini-2025-01-31", "o3-mini", None),
    ("together/deepseek-r1", "dsr1_together", 32_000),
)

ANTHROPIC_THINKING_MODELS = (
    "claude-3-7-sonnet-20250219",
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
)
