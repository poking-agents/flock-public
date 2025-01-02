"""Server setup and configuration"""

import logging
import os
from pathlib import Path
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import threading

logger = logging.getLogger(__name__)

# Get the absolute path to the templates directory
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

app = Flask(__name__, template_folder=template_dir)
app.config["SECRET_KEY"] = "operation-ui-secret"
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")
app.logger.disabled = True
log = logging.getLogger("werkzeug")
log.disabled = True


def create_app() -> Flask:
    """Create and configure the Flask application"""
    from .events import operations_by_state, event_processor

    @app.route("/")
    def index():
        """Render the main UI page"""
        logger.info("UI page requested")
        return render_template("operations.html")

    @app.route("/api/operations")
    def get_operations():
        """Get all stored operations"""
        logger.info("Operations API requested")
        data = {
            state_id: [op.to_dict() for op in ops]
            for state_id, ops in operations_by_state.items()
        }
        logger.debug(f"Returning operations: {data}")
        return jsonify(data)

    @socketio.on("connect")
    def handle_connect():
        """Handle client connection"""
        logger.info("Client connected")
        data = {
            state_id: [op.to_dict() for op in ops]
            for state_id, ops in operations_by_state.items()
        }
        logger.debug(f"Sending initial operations: {data}")
        emit("initial_operations", data)

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info("Client disconnected")

    @socketio.on_error_default
    def default_error_handler(e):
        """Handle SocketIO errors"""
        logger.error(f"SocketIO error: {str(e)}", exc_info=True)

    logger.info("Starting event processor thread")
    processor_thread = threading.Thread(target=event_processor, daemon=True)
    processor_thread.start()
    return app
