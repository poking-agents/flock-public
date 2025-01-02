"""Operation UI initialization and server startup"""

import threading
from typing import Dict, Any

server_running = False


def start_ui_server(port: int = 8081) -> None:
    """Start the UI server"""
    global server_running
    if server_running:
        return
    server_running = True
    from .server import create_app, socketio

    app = create_app()
    try:
        socketio.init_app(
            app,
            cors_allowed_origins="*",
            async_mode="threading",
            logger=False,
            engineio_logger=False,
        )
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            debug=False,
            use_reloader=False,
            log_output=False,
        )
    except Exception as e:
        print(f"Error starting UI server: {e}")
    finally:
        server_running = False


def start_ui_server_thread(port: int = 8081) -> None:
    """Start the UI server in a separate thread"""
    server_thread = threading.Thread(target=start_ui_server, args=(port,), daemon=True)
    server_thread.start()


def add_operation_event(event_data: Dict[str, Any]) -> None:
    """Add an operation event to the processing queue"""
    from .events import add_operation_event as _add_event

    _add_event(event_data)


__all__ = ["start_ui_server", "start_ui_server_thread", "add_operation_event"]
