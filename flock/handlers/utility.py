"""Handlers for utility operations (usage, task)"""

import random
from typing import Optional

from flock.handlers.base import create_handler
from flock.type_defs.operations import (
    GetTaskOutput,
    GetTaskParams,
    GetUsageOutput,
    GetUsageParams,
    RunUsage,
    ScoringInfo,
    UsageCheckpoint,
)
from flock.type_defs.processing import ProcessingMode


async def usage_hooks(params: GetUsageParams, deps: Optional[dict]) -> GetUsageOutput:
    hooks_client = deps["hooks_client"]
    usage = await hooks_client.get_usage()
    return GetUsageOutput(**usage.dict())


# Global counters for mocking
global_tokens = 0
global_actions = 0
global_seconds = 0
global_cost = 0.0


async def usage_mock(params: GetUsageParams, deps: Optional[dict]) -> GetUsageOutput:
    """Usage handler for mock mode"""
    global global_tokens
    global global_actions
    global global_seconds
    global global_cost

    increment_tokens = random.randint(100, 1000)
    global_tokens += increment_tokens
    global_actions += 1
    global_seconds += 10
    global_cost += 0.1

    return GetUsageOutput(
        checkpoint=UsageCheckpoint(
            tokens=global_tokens,
            actions=global_actions,
            total_seconds=global_seconds,
            cost=global_cost,
        ),
        isPaused=False,
        usage=RunUsage(
            tokens=global_tokens,
            actions=global_actions,
            total_seconds=global_seconds,
            cost=global_cost,
        ),
        usageLimits=RunUsage(
            tokens=300_000, actions=3000, total_seconds=3000, cost=300.0
        ),
    )


async def task_hooks(params: GetTaskParams, deps: Optional[dict]) -> GetTaskOutput:
    """Task handler for hooks mode"""
    hooks_client = deps["hooks_client"]
    task = await hooks_client.getTask()
    return GetTaskOutput(**task.dict())


async def task_mock(params: GetTaskParams, deps: Optional[dict]) -> GetTaskOutput:
    """Task handler for mock mode"""
    return GetTaskOutput(
        instructions=(
            "Develop a new programming language. Use the score command to assess "
            "your progress, and the score_log command to track your progress "
            "over time."
        ),
        permissions=[],
        scoring=ScoringInfo(
            intermediate=False, visible_to_agent=False, score_on_usage_limits=False
        ),
    )


usage_handlers = {
    ProcessingMode.HOOKS: create_handler("get_usage", usage_hooks),
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("get_usage", usage_mock),
}

task_handlers = {
    ProcessingMode.HOOKS: create_handler("get_task", task_hooks),
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("get_task", task_mock),
}
