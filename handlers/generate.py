"""Handlers for generate operation"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, Dict, Any, List

from handlers.base import create_handler
from logger import logger
from type_defs.operations import GenerationOutput, GenerationParams
from type_defs.processing import ProcessingMode
import aiohttp

SINGLE_GENERATION_MODELS: Set[str] = {}
REASONING_EFFORT_MODELS: Set[str] = {
    "o1",
    "o3-mini-2024-12-17-redteam",
    "o3-mini-2025-01-14",
}

MODEL_EXTRA_PARAMETERS: Dict[str, Dict[str, Any]] = {
    "openrouter/deepseek-r1": {
        "provider": {
            "order": ["DeepInfra", "Fireworks"]
        }
    },
    "openrouter/deepseek/deepseek-r1-0528": {
        "provider": {
            "order": ["DeepInfra", "Fireworks"]
        }
    }
}


def merge_extra_parameters(base: Optional[Dict[str, Any]], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two sets of extra parameters, with override taking precedence"""
    logger.info(f"Merging extra parameters - base: {base}, override: {override}")
    if base is None:
        logger.info(f"Base is None, returning override: {override}")
        return override
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_extra_parameters(merged[key], value)
        else:
            merged[key] = value
    logger.info(f"Merged result: {merged}")
    return merged


def get_role_extra_parameters(settings: Any, role: str) -> Optional[Dict[str, Any]]:
    """Extract extraParameters from a specific role's settings"""
    if not hasattr(settings, role):
        return None
    
    role_settings = getattr(settings, role)
    if not isinstance(role_settings, list) or not role_settings:
        return None
    
    # Get extraParameters from the first role setting
    first_setting = role_settings[0]
    if not isinstance(first_setting, dict):
        return None
        
    return first_setting.get("extraParameters")


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
        # Log initial state
        logger.info(f"Initial extraParameters: {params.extraParameters}")
        logger.info(f"Model being used: {params.settings.model}")
        logger.info(f"Available extra params: {MODEL_EXTRA_PARAMETERS}")
        
        # Get role-specific extraParameters from the settings object itself
        role_extra_params = None
        for attr in ("extraParameters", "extra_parameters"):
            if hasattr(params.settings, attr):
                candidate = getattr(params.settings, attr)
                if candidate:
                    role_extra_params = candidate
                    break

        if role_extra_params:
            logger.info(f"Found role extraParameters in settings: {role_extra_params}")
        else:
            try:
                logger.info(f"Settings dump: {params.settings.model_dump()}")
            except Exception as e:
                logger.info(f"Could not dump settings: {e}")

        # Merge parameters in order of increasing specificity:
        # 1. model-level defaults (MODEL_EXTRA_PARAMETERS)
        # 2. role-level settings (params.settings.extraParameters)
        # 3. request-level overrides (params.extraParameters)

        merged_params: Optional[Dict[str, Any]] = None

        # Start with model-level params (least specific)
        model_params = MODEL_EXTRA_PARAMETERS.get(params.settings.model, None)
        if model_params:
            merged_params = merge_extra_parameters(merged_params, model_params)

        # Apply role-level params
        if role_extra_params:
            merged_params = merge_extra_parameters(merged_params, role_extra_params)

        # Finally, apply request-level params (highest specificity)
        if params.extraParameters:
            merged_params = merge_extra_parameters(merged_params, params.extraParameters)

        # If everything is still None, keep it that way
        params = params.model_copy(update={"extraParameters": merged_params})
        logger.info(f"After setting extraParameters: {params.extraParameters}")

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
            logger.info(f"Making post_completion call with extraParameters: {params.extraParameters}")
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
    settings = params.settings.copy()
    if settings.model in REASONING_EFFORT_MODELS:
        settings.reasoning_effort = "high"

    # Log initial state
    logger.info(f"[hooks] Initial extraParameters: {params.extraParameters}")
    logger.info(f"[hooks] Model being used: {settings.model}")
    logger.info(f"[hooks] Available extra params: {MODEL_EXTRA_PARAMETERS}")

    # Get role-specific extraParameters from the settings object itself
    role_extra_params = None
    for attr in ("extraParameters", "extra_parameters"):
        if hasattr(params.settings, attr):
            candidate = getattr(params.settings, attr)
            if candidate:
                role_extra_params = candidate
                break

    if role_extra_params:
        logger.info(f"[hooks] Found role extraParameters in settings: {role_extra_params}")
    else:
        try:
            logger.info(f"[hooks] Settings dump: {params.settings.model_dump()}")
        except Exception as e:
            logger.info(f"[hooks] Could not dump settings: {e}")

    # Merge parameters in order of increasing specificity:
    # 1. model-level defaults (MODEL_EXTRA_PARAMETERS)
    # 2. role-level settings (params.settings.extraParameters)
    # 3. request-level overrides (params.extraParameters)

    merged_params: Optional[Dict[str, Any]] = None

    # Start with model-level params (least specific)
    model_params = MODEL_EXTRA_PARAMETERS.get(settings.model, None)
    if model_params:
        merged_params = merge_extra_parameters(merged_params, model_params)

    # Apply role-level params
    if role_extra_params:
        merged_params = merge_extra_parameters(merged_params, role_extra_params)

    # Finally, apply request-level params (highest specificity)
    if params.extraParameters:
        merged_params = merge_extra_parameters(merged_params, params.extraParameters)

    # If everything is still None, keep it that way
    params = params.model_copy(update={"extraParameters": merged_params})
    logger.info(f"[hooks] After merging extraParameters: {params.extraParameters}")
    
    timeout = aiohttp.ClientTimeout(total=2 * 60 * 60)  # 60 minutes
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
            logger.info(f"[hooks] Making generate call with extraParameters: {params.extraParameters}")
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
