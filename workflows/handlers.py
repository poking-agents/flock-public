"""HTTP handlers for workflow endpoints"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from aiohttp import web

from handlers.base import validate_untyped_request
from logger import logger
from operation_handler import handle_operations
from type_defs import PreviousOperations, ProcessingMode
from type_defs.operations import (
    InitWorkflowOutput,
    InitWorkflowParams,
    InitWorkflowRequest,
    InitWorkflowResult,
    SaveStateParams,
    SaveStateRequest,
)
from type_defs.phases import WorkflowData
from utils.phase_utils import serialize_for_json
from utils.state import load_state, save_state
from workflows.executor import execute_phase


async def handle_workflow(data: WorkflowData, mode: ProcessingMode) -> Dict[str, Any]:
    """Handle workflow operations"""
    raw_operations = data.get("operations", [])
    current_phase = data.get("current_phase")
    next_phase = data.get("next_phase")
    delay = data.get("delay", 0)
    state_id = data["state_id"]
    operations = [validate_untyped_request(op) for op in raw_operations]

    if not operations:
        logger.info(f"[{state_id}][{current_phase}] No operations to process")
        return {"updates": [], "next_phase": next_phase, "error": None, "delay": delay}

    if delay:
        logger.info(f"[{state_id}][{current_phase}] Applying delay of {delay} seconds")
        await asyncio.sleep(delay)

    current_state = load_state(state_id)
    save_state_op = SaveStateRequest(
        type="save_state",
        params=SaveStateParams(
            state_id=state_id, state=current_state, timestamp=datetime.now().isoformat()
        ),
    )
    operations.append(save_state_op)

    updates = await handle_operations(
        mode=mode, operations=operations, state_id=state_id, current_phase=current_phase
    )

    logger.info(
        f"[{state_id}][{current_phase}] {len(operations)} operations processed, "
        f"next phase: {next_phase}"
    )
    return {"updates": updates, "next_phase": next_phase, "error": None, "delay": delay}


async def workflow_handler(request: web.Request, mode: ProcessingMode) -> web.Response:
    """Handle /run_workflow requests"""
    try:
        raw_data = await request.json()
        state_id = raw_data["state_id"]
        current_phase = raw_data.get("current_phase", "unknown")

        logger.debug(
            f"[{state_id}][{current_phase}] Received workflow request: "
            f"{json.dumps(raw_data, indent=2)}"
        )

        data: WorkflowData = {
            "state_id": state_id,
            "operations": raw_data.get("operations", {}),
            "current_phase": current_phase,
            "next_phase": raw_data.get("next_phase"),
            "delay": raw_data.get("delay", 0),
        }

        result, error = await process_workflow(data, mode)
        if error:
            logger.error(f"[{state_id}][{current_phase}] Workflow error: {error}")
            return web.json_response({"error": error}, status=500)

        if result.get("next_phase"):
            await execute_next_phase(result, data)

        return web.json_response(serialize_for_json(result))
    except Exception as e:
        logger.error(f"Error in workflow handler: {str(e)}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)


async def process_workflow(
    data: WorkflowData, mode: ProcessingMode
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Process workflow and return result"""
    state_id = data["state_id"]
    current_phase = data.get("current_phase", "unknown")

    try:
        result = await handle_workflow(data, mode)
        return result, None
    except Exception as e:
        logger.error(
            f"[{state_id}][{current_phase}] Error handling workflow: {str(e)}",
            exc_info=True,
        )
        return {}, str(e)


async def execute_next_phase(result: Dict[str, Any], data: WorkflowData) -> None:
    """Start next phase if present"""
    if not result.get("next_phase"):
        return

    state_id = data["state_id"]
    current_phase = data.get("current_phase", "unknown")
    next_phase = result["next_phase"]

    try:
        logger.info(f"[{state_id}][{current_phase}] Starting next phase: {next_phase}")
        asyncio.create_task(
            execute_phase(
                next_phase,
                state_id,
                {"updates": serialize_for_json(result["updates"])},
            ),
            name=f"phase_{state_id}_{next_phase}",
        )
    except Exception as e:
        logger.error(
            f"[{state_id}][{current_phase}] Error starting next phase: {str(e)}",
            exc_info=True,
        )


async def start_workflow_handler(
    request: web.Request, mode: ProcessingMode
) -> web.Response:
    """Handle /start_workflow requests"""
    try:
        raw_data = await request.json()
        logger.debug(
            f"Received start workflow request: {json.dumps(raw_data, indent=2)}"
        )

        required_fields = ["state_id", "workflow_type", "initial_state", "first_phase"]
        missing_fields = [f for f in required_fields if f not in raw_data]
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            logger.error(error_msg)
            return web.json_response({"error": error_msg}, status=400)

        state_id = raw_data["state_id"]
        workflow_type = raw_data["workflow_type"]
        initial_state = raw_data["initial_state"]
        first_phase = raw_data["first_phase"]

        try:
            save_state(state_id, initial_state)
            logger.debug(f"[{state_id}] Saved initial state")
        except Exception as e:
            error_msg = f"Failed to save initial state: {str(e)}"
            logger.error(f"[{state_id}] {error_msg}")
            return web.json_response({"error": error_msg}, status=500)

        settings_path = (
            "/home/agent/settings.json"
            if mode == ProcessingMode.HOOKS
            else raw_data.get("settings_path", "settings.json")
        )
        logger.debug(f"[{state_id}] Using settings path: {settings_path}")

        init_request = InitWorkflowRequest(
            type="init_workflow", params=InitWorkflowParams(workflow_type=workflow_type)
        )
        init_result = InitWorkflowResult(
            type="init_workflow",
            result=InitWorkflowOutput(
                status="success", state_id=state_id, settings_path=settings_path
            ),
        )
        previous_operations = PreviousOperations(updates=[(init_request, init_result)])

        try:
            await execute_phase(first_phase, state_id, previous_operations.model_dump())
            logger.info(f"[{state_id}] Started {workflow_type} workflow")
        except Exception as e:
            error_msg = f"Failed to execute first phase: {str(e)}"
            logger.error(f"[{state_id}] {error_msg}")
            return web.json_response({"error": error_msg}, status=500)

        return web.json_response(
            {
                "status": "success",
                "message": f"{workflow_type} workflow started with state_id: "
                f"{state_id}",
                "state_id": state_id,
            }
        )
    except Exception as e:
        error_msg = f"Error starting workflow: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return web.json_response({"error": error_msg}, status=500)
