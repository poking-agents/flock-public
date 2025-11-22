"""Handlers for generate operation"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import aiohttp

from flock.handlers.base import create_handler
from flock.logger import logger
from flock.type_defs.operations import GenerationOutput, GenerationParams
from flock.type_defs.processing import ProcessingMode

SINGLE_GENERATION_MODELS = ()
REASONING_EFFORT_MODELS = ("o1-2024-12-17", "o3-mini-2025-01-31")
GEMINI_REASONING_MODELS = (
    "openrouter/google/gemini-2.5-pro-preview",
    "openrouter/google/gemini-3-pro-preview",
)

MODEL_EXTRA_PARAMETERS: Dict[str, Dict[str, Any]] = {
    "openrouter/google/gemini-2.5-pro-preview": {
        "provider": {
            "order": ["Google Vertex"],
            "allow_fallbacks": False
        }
    },
    "openrouter/google/gemini-3-pro-preview": {
        "provider": {
            "order": ["Google AI Studio", "Google"],
            "allow_fallbacks": True
        }
    },
}


def _deep_merge_dicts(
    base: Optional[Dict[str, Any]], override: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Recursively merge two dictionaries without mutating inputs."""
    result: Dict[str, Any] = {}
    if base:
        for key, value in base.items():
            if isinstance(value, dict):
                result[key] = _deep_merge_dicts(value, None)
            else:
                result[key] = value
    if override:
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = _deep_merge_dicts(result[key], value)
            else:
                result[key] = value
    return result


def _extract_reasoning_config(params: GenerationParams) -> Optional[Dict[str, Any]]:
    """Build reasoning configuration based on settings and defaults."""
    settings = params.settings
    settings_data: Dict[str, Any] = {}
    if hasattr(settings, "model_dump"):
        try:
            settings_data = settings.model_dump()
        except Exception:  # pragma: no cover - defensive guard
            settings_data = {}
    reasoning_from_settings = settings_data.get("reasoning")
    if isinstance(reasoning_from_settings, dict) and reasoning_from_settings:
        return reasoning_from_settings

    reasoning: Dict[str, Any] = {}
    max_reasoning_tokens = settings_data.get("max_reasoning_tokens")
    reasoning_effort = settings_data.get("reasoning_effort")

    if max_reasoning_tokens:
        reasoning["max_tokens"] = max_reasoning_tokens
    elif reasoning_effort:
        reasoning["effort"] = reasoning_effort

    # Enable reasoning by default for models that support it
    if not reasoning:
        if params.settings.model in REASONING_EFFORT_MODELS:
            reasoning["effort"] = "high"
        elif params.settings.model in GEMINI_REASONING_MODELS:
            # Gemini models need reasoning enabled to return thought_signature
            reasoning["enabled"] = True

    return reasoning or None


def resolve_extra_parameters(params: GenerationParams) -> Optional[Dict[str, Any]]:
    """
    Merge existing extra parameters with model-specific overrides and derived reasoning configuration.
    """
    base_extra = params.extraParameters or {}
    model_extra = MODEL_EXTRA_PARAMETERS.get(params.settings.model, {})
    merged = _deep_merge_dicts(model_extra, base_extra)

    if not isinstance(merged, dict):
        merged = {}

    existing_reasoning = merged.get("reasoning")
    if not isinstance(existing_reasoning, dict) or not existing_reasoning:
        reasoning_config = _extract_reasoning_config(params)
        if reasoning_config:
            merged["reasoning"] = reasoning_config

    return merged or None


def log_generation(params: GenerationParams, result: GenerationOutput) -> None:
    """Log generation request and response"""
    try:
        log_dir = Path("logs/generations")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request": {
                **params.model_dump(),
                "raw_messages": (
                    [
                        {
                            "role": msg.get("role"),
                            "content": msg.get("content"),
                            "function_call": msg.get("function_call"),
                            "name": msg.get("name"),
                        }
                        for msg in params.messages
                    ]
                    if params.messages
                    else []
                ),
            },
            "response": result.model_dump(),
            "success": not bool(result.error),
            "error": result.error if result.error else None,
        }
        log_file = log_dir / f"generation_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Error logging generation: {str(e)}")


async def generate_middleman(
    params: GenerationParams, deps: Optional[dict]
) -> GenerationOutput:
    """Generate handler for middleman mode"""
    post_completion = deps["post_completion"]
    try:
        resolved_extra = resolve_extra_parameters(params)
        if resolved_extra is not None:
            params = params.model_copy(update={"extraParameters": resolved_extra})
            logger.info(
                f"Applied extra parameters for model {params.settings.model}: {resolved_extra}"
            )

        processed_messages = params.messages
        if params.settings.model in SINGLE_GENERATION_MODELS and params.settings.n > 1:
            raw_outputs = await asyncio.gather(
                *[
                    post_completion(
                        messages=processed_messages,
                        model=params.settings.model,
                        temp=params.settings.temp,
                        n=1,
                        function_call=params.settings.function_call,
                        functions=params.functions,
                        extra_parameters=params.extraParameters
                    )
                    for _ in range(params.settings.n)
                ]
            )
            outputs = []
            for raw_output in raw_outputs:
                if raw_output.get("error"):
                    error_output = GenerationOutput(
                        outputs=[],
                        error=raw_output["error"],
                        non_blocking_errors=raw_output.get("non_blocking_errors", []),
                    )
                    log_generation(params, error_output)
                    raise Exception(raw_output["error"])
                outputs.extend(raw_output["outputs"])
            merged = GenerationOutput(
                outputs=outputs,
                n_completion_tokens_spent=sum(
                    raw_output["n_completion_tokens_spent"] or 0
                    for raw_output in raw_outputs
                ),
                n_prompt_tokens_spent=sum(
                    raw_output["n_prompt_tokens_spent"] or 0
                    for raw_output in raw_outputs
                ),
                cost=sum(raw_output["cost"] or 0 for raw_output in raw_outputs),
            )
            log_generation(params, merged)
            return merged
        else:
            raw_output = await post_completion(
                messages=processed_messages,
                model=params.settings.model,
                temp=params.settings.temp,
                n=params.settings.n,
                function_call=params.settings.function_call,
                functions=params.functions,
                extra_parameters=params.extraParameters
            )
            if raw_output.get("error"):
                error_output = GenerationOutput(
                    outputs=[],
                    error=raw_output["error"],
                    non_blocking_errors=raw_output.get("non_blocking_errors", []),
                )
                log_generation(params, error_output)
                raise Exception(raw_output["error"])
            result = GenerationOutput(**raw_output)
            log_generation(params, result)
            return result
    except Exception as e:
        error_output = GenerationOutput(
            outputs=[], error=str(e), non_blocking_errors=[str(e)]
        )
        log_generation(params, error_output)
        raise


async def generate_hooks(
    params: GenerationParams, deps: Optional[dict]
) -> GenerationOutput:
    """Generate handler for hooks mode"""
    hooks_client = deps["hooks_client"]
    processed_messages = params.messages
    resolved_extra = resolve_extra_parameters(params)
    if resolved_extra is not None:
        params = params.model_copy(update={"extraParameters": resolved_extra})
        logger.info(
            f"Applied extra parameters for model {params.settings.model}: {resolved_extra}"
        )
    settings = params.settings.copy()

    timeout = aiohttp.ClientTimeout(total=30 * 60)  # 30 minutes
    async with aiohttp.ClientSession(timeout=timeout) as session:
        if settings.model in SINGLE_GENERATION_MODELS and settings.n > 1:
            raw_outputs = []
            settings.n = 1
            raw_outputs = await asyncio.gather(
                *[
                    hooks_client.generate(
                        settings=settings,
                        messages=processed_messages,
                        functions=params.functions,
                        session=session,
                        extraParameters=params.extraParameters
                    )
                    for _ in range(params.settings.n)
                ]
            )
            outputs = []
            for raw_output in raw_outputs:
                outputs.extend(raw_output.outputs)
            merged = GenerationOutput(
                outputs=outputs,
                n_completion_tokens_spent=sum(
                    raw_output.n_completion_tokens_spent or 0
                    for raw_output in raw_outputs
                ),
                n_prompt_tokens_spent=sum(
                    raw_output.n_prompt_tokens_spent or 0 for raw_output in raw_outputs
                ),
                cost=sum(raw_output.cost or 0 for raw_output in raw_outputs),
            )
            log_generation(params, merged)
            return merged
        else:
            result = await hooks_client.generate(
                settings=settings,
                messages=processed_messages,
                functions=params.functions,
                session=session,
                extraParameters=params.extraParameters
            )
            output = GenerationOutput(**result.dict())
            log_generation(params, output)
            return output


async def generate_mock(
    params: GenerationParams, deps: Optional[dict]
) -> GenerationOutput:
    """Generate handler for mock mode"""
    mock_output = GenerationOutput()
    log_generation(params, mock_output)
    return mock_output


handlers = {
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("generate", generate_middleman),
    ProcessingMode.HOOKS: create_handler("generate", generate_hooks),
}
