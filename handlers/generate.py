"""Handlers for generate operation"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from handlers.base import create_handler
from logger import logger
from type_defs.operations import GenerationOutput, GenerationParams
from type_defs.processing import ProcessingMode

SINGLE_GENERATION_MODELS: Set[str] = {}

ANTHROPIC_MODELS = ["claude-3-5-sonnet-20240620", "claude-3-5-sonnet-20241022"]


def preprocesses_messages(params: GenerationParams) -> List[dict]:
    if params.settings.model in ["gemini-2.0-flash-exp"]:
        return [
            {
                "role": "user" if message["role"] == "system" else message["role"],
                "content": message["content"],
            }
            for message in params.messages
        ]
    # make sure we have non-empty and non-whitespace-only content in all assistant messages
    if params.settings.model in ANTHROPIC_MODELS:
        for i, message in enumerate(params.messages):
            if message["role"] == "assistant" and message["content"].strip() == "":
                params.messages[i]["content"] = "_"

    return params.messages


def postprocesses_output(full_output: GenerationOutput) -> GenerationOutput:
    """Some models return function calls with arguments: <serialized_json>, while others return a dict. Convert all to serialized json for backwards compatibility"""
    for output in full_output.outputs:
        if (
            output.function_call
            and "arguments" in output.function_call
            and isinstance(output.function_call["arguments"], dict)
        ):
            output.function_call["arguments"] = json.dumps(
                output.function_call["arguments"]
            )
    return full_output


def log_generation(params: GenerationParams, result: GenerationOutput) -> None:
    """Log generation request and response"""
    try:
        log_dir = Path("logs/generations")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request": {
                **params.model_dump(),
                "raw_messages": [
                    {
                        "role": msg.get("role"),
                        "content": msg.get("content"),
                        "function_call": msg.get("function_call"),
                        "name": msg.get("name"),
                    }
                    for msg in params.messages
                ]
                if params.messages
                else [],
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
        processed_messages = preprocesses_messages(params)
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
            return postprocesses_output(merged)
        else:
            raw_output = await post_completion(
                messages=processed_messages,
                model=params.settings.model,
                temp=params.settings.temp,
                n=params.settings.n,
                function_call=params.settings.function_call,
                functions=params.functions,
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
            return postprocesses_output(result)
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
    processed_messages = preprocesses_messages(params)
    if params.settings.model in SINGLE_GENERATION_MODELS and params.settings.n > 1:
        raw_outputs = []
        settings = params.settings.copy()
        settings.n = 1
        raw_outputs = await asyncio.gather(
            *[
                hooks_client.generate(
                    settings=settings,
                    messages=processed_messages,
                    functions=params.functions,
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
                raw_output.n_completion_tokens_spent or 0 for raw_output in raw_outputs
            ),
            n_prompt_tokens_spent=sum(
                raw_output.n_prompt_tokens_spent or 0 for raw_output in raw_outputs
            ),
            cost=sum(raw_output.cost or 0 for raw_output in raw_outputs),
        )
        log_generation(params, merged)
        return postprocesses_output(merged)
    else:
        result = await hooks_client.generate(
            settings=params.settings,
            messages=processed_messages,
            functions=params.functions,
        )
        output = GenerationOutput(**result.dict())
        log_generation(params, output)
        return postprocesses_output(output)


handlers = {
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("generate", generate_middleman),
    ProcessingMode.HOOKS: create_handler("generate", generate_hooks),
}
