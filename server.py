"""Server setup and configuration"""

import logging
import sys

from aiohttp import web

from logger import setup_logger
from type_defs import ProcessingMode
from workflows import start_workflow_handler, workflow_handler

logger = setup_logger("server")


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging with proper formatting"""
    logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level.upper())
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(log_level.upper())

    asyncio_logger = logging.getLogger("asyncio")
    asyncio_logger.setLevel(log_level.upper())
    asyncio_logger.addHandler(console_handler)


async def health_check(request: web.Request) -> web.Response:
    """Simple health check endpoint"""
    return web.Response(text="OK")


def create_app(mode: ProcessingMode, log_level: str = "INFO") -> web.Application:
    """Create and configure the web application"""
    setup_logging(log_level)
    logger.info(f"Starting server in {mode} mode with log level {log_level}")

    app = web.Application(
        client_max_size=1024**2 * 100  # 100 MB limit
    )

    # Add routes
    app.router.add_post("/run_workflow", lambda r: workflow_handler(r, mode))
    app.router.add_post("/start_workflow", lambda r: start_workflow_handler(r, mode))

    # Add health check route
    app.router.add_get("/health", health_check)

    # Store settings in app state
    app["mode"] = mode

    return app
