"""Event handling and processing for operation UI"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional
import queue
import logging

logger = logging.getLogger(__name__)


@dataclass
class OperationEvent:
    """Operation event data structure"""

    timestamp: str
    state_id: str
    phase: str
    operation_type: str
    params: Dict[str, Any]
    result: Dict[str, Any]
    status: str
    duration: float
    state: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "timestamp": self.timestamp,
            "state_id": self.state_id,
            "phase": self.phase,
            "operation_type": self.operation_type,
            "params": self.params,
            "result": self.result,
            "status": self.status,
            "duration": self.duration,
            "state": self.state,
        }


operations_by_state: Dict[str, List[OperationEvent]] = {}
operation_queue = queue.Queue()


def process_operation_event(event_data: Dict[str, Any]) -> None:
    """Process an operation event and emit to connected clients"""
    from .server import socketio

    logger.debug(f"Processing event: {event_data}")
    event = OperationEvent(
        timestamp=datetime.now().isoformat(),
        state_id=event_data["state_id"],
        phase=event_data["phase"],
        operation_type=event_data["operation"]["type"],
        params=event_data["operation"]["params"],
        result=event_data["result"],
        status=event_data["status"],
        duration=event_data.get("duration", 0.0),
    )
    if event.state_id not in operations_by_state:
        operations_by_state[event.state_id] = []
    operations_by_state[event.state_id].append(event)
    event_dict = event.to_dict()
    logger.debug(f"Emitting event: {event_dict}")
    try:
        socketio.emit("operation_event", event_dict, namespace="/")
        logger.debug("Event emitted successfully")
    except Exception as e:
        logger.error(f"Error emitting event: {e}")


def event_processor() -> None:
    """Process events from the queue"""
    logger.info("Event processor started")
    while True:
        try:
            logger.debug("Waiting for events...")
            event = operation_queue.get()
            logger.info(
                f"Processing event for operation: {event.get('operation', {}).get('type')}"
            )
            process_operation_event(event)
        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)


def add_operation_event(event_data: Dict[str, Any]) -> None:
    """Add an operation event to the processing queue"""
    try:
        logger.debug(f"Adding event to queue: {event_data}")
        operation_queue.put(event_data)
    except Exception as e:
        logger.error(f"Error adding operation event: {e}")


def format_operation_result(result: Dict[str, Any]) -> str:
    """Format operation result for display"""
    try:
        if "outputs" in result:
            outputs = result["outputs"]
            formatted_outputs = []
            for output in outputs:
                if "completion" in output:
                    formatted_outputs.append(
                        f"""Completion:
{output['completion']}
Stop reason: {output.get('stop_reason', 'unknown')}"""
                    )
            return "\n\n".join(formatted_outputs)
        elif "stdout" in result and "stderr" in result:
            parts = []
            if result["stdout"]:
                parts.append(f"stdout:\n{result['stdout']}")
            if result["stderr"]:
                parts.append(f"stderr:\n{result['stderr']}")
            if "status" in result and result["status"] != 0:
                parts.append(f"Exit code: {result['status']}")
            return "\n\n".join(parts)
        elif "output" in result and "error" in result:
            parts = []
            if result["output"]:
                parts.append(f"Output:\n{result['output']}")
            if result["error"]:
                parts.append(f"Error:\n{result['error']}")
            return "\n\n".join(parts)
        else:
            return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error formatting operation result: {e}")
        return str(result)
