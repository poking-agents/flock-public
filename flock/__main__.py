import argparse
import asyncio
import json
import random
import sys
from pathlib import Path

import aiohttp

from flock.config import API_BASE_URL, PORT
from flock.server import create_app
from flock.type_defs import ProcessingMode


async def start_workflow() -> None:
    try:
        settings_path = Path("./settings.json")
        if not settings_path.exists():
            raise FileNotFoundError(f"Settings file not found: {settings_path}")

        with open(settings_path) as f:
            settings = json.load(f)

        workflow_type = settings["workflow_type"]
    except Exception as e:
        print(f"Could not get workflow type from settings: {e!r}")
        return

    try:
        random_int = random.randint(1000, 10_000)
        state_id = f"{workflow_type}_{random_int}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/start_workflow",
                json={
                    "state_id": state_id,
                    "settings_path": str(settings_path),
                    "workflow_type": workflow_type,
                    "initial_state": {
                        "settings": settings,
                        "previous_results": [],
                        "id": state_id,
                    },
                    "first_phase": f"{workflow_type}/phases/init_from_settings.py",
                },
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Server returned status {response.status}: {error_text}"
                    )

                if response.status == 200:
                    print(f"{workflow_type.capitalize()} workflow started successfully")
                else:
                    print(
                        f"Failed to start {workflow_type} "
                        f"workflow: {await response.text()}"
                    )
    except Exception as e:
        print(f"Error starting {workflow_type} workflow: {e!r}")


async def wait_for_server(url: str, timeout: int = 30, interval: float = 0.5) -> None:
    start_time = asyncio.get_event_loop().time()
    health_check_url = f"{url}/health"
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(health_check_url) as response:
                    if response.status == 200:
                        print(f"Server is up and running at {url}")
                        return
        except aiohttp.ClientError:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(
                    f"Server at {url} did not become available within {timeout} seconds"
                )
        await asyncio.sleep(interval)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the workflow server")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--port", type=int, default=PORT, help="Port to run the server on"
    )
    parser.add_argument(
        "--mode",
        type=ProcessingMode,
        default=ProcessingMode.HOOKS,
        choices=list(ProcessingMode),
        help="Processing mode to use",
    )

    args = parser.parse_args()

    app, event = create_app(mode=args.mode, log_level=args.log_level)

    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, "localhost", args.port)

    print(f"Starting server on port {args.port}")
    await site.start()

    print("Waiting for server to be ready...")
    await wait_for_server(f"http://localhost:{args.port}")

    if args.mode == ProcessingMode.HOOKS:
        print("Starting server in HOOKS mode...")
        print(f"sys.path: {sys.path}")
        from pyhooks import Hooks

        hooks = Hooks()
        try:
            await start_workflow()
            await event.wait()
        except Exception as e:
            await hooks.log_error(f"Error in HOOKS mode: {str(e)}")
            raise
    else:
        await start_workflow()

    # Keep the server running
    await event.wait()
    raise RuntimeError("Some phase errored out, exiting...")


if __name__ == "__main__":
    asyncio.run(main())
