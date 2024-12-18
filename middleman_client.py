"""Middleman API client functionality"""

import asyncio
import json
import os
import random
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from logger import logger


def get_credentials() -> Tuple[str, str]:
    """Get the Middleman API base URL and API key"""
    base_url = os.getenv("MIDDLEMAN_API_URL")
    api_key = os.getenv("MIDDLEMAN_API_KEY")
    if not api_key:
        try:
            with open(os.path.expanduser("~/.config/viv-cli/config.json")) as f:
                config = json.load(f)
                evalsToken = config["evalsToken"]
                api_key = evalsToken.split("---")[0]
        except FileNotFoundError:
            api_key = "test-key"
        except Exception:
            api_key = "test-key"
    assert base_url, "Middleman API URL not set"
    assert api_key, "Middleman API key not set"
    return base_url, api_key


def create_session() -> aiohttp.ClientSession:
    """Create a configured aiohttp session"""
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=120, ssl=False, keepalive_timeout=120),
        timeout=aiohttp.ClientTimeout(total=120),
    )


def format_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Format messages for API request"""
    formatted_messages = []
    for msg in messages:
        formatted_msg = {"role": msg["role"], "content": msg["content"]}
        if "function_call" in msg:
            formatted_msg["function_call"] = msg["function_call"]
        if "name" in msg:
            formatted_msg["name"] = msg["name"]
        formatted_messages.append(formatted_msg)
    return formatted_messages


def get_mock_response() -> Dict[str, Any]:
    """Get mock response for testing"""
    return {
        "outputs": [
            {
                "completion": "This is a mock response for testing",
                "stop_reason": "length",
            }
        ],
        "usage": {"prompt_tokens": 57, "completion_tokens": 8, "total_tokens": 65},
    }


async def post_completion(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    temp: float = 1.0,
    n: int = 1,
    function_call: Optional[Dict[str, Any]] = None,
    functions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base_url, api_key = get_credentials()
    if api_key == "test-key":
        return get_mock_response()

    formatted_messages = format_messages(messages)
    data = {
        "api_key": api_key,
        "messages": formatted_messages,
        "model": model,
        "temperature": temp,
        "n": n,
        "stream": False,
        "functions": functions,
        "function_call": function_call,
        "priority": "high",
    }

    max_retries = 5
    base_delay = 1.0  # Initial delay in seconds

    async with create_session() as session:
        for attempt in range(max_retries):
            try:
                async with session.post(
                    f"{base_url}/completions", json=data
                ) as response:
                    if response.status == 529:  # Overloaded error
                        if attempt < max_retries - 1:
                            delay = base_delay * (2**attempt)  # Exponential backoff
                            jitter = random.uniform(
                                0, 0.1 * delay
                            )  # Add some randomness
                            total_delay = delay + jitter
                            logger.warning(
                                f"Middleman API attempt {attempt + 1} failed due to overload. "
                                f"Retrying in {total_delay:.2f} seconds..."
                            )
                            await asyncio.sleep(total_delay)
                            continue
                    # 503 Service Unavailable
                    if response.status == 503:
                        if attempt < max_retries - 1:
                            delay = base_delay * (2**attempt)
                            jitter = random.uniform(0, 0.1 * delay)
                            total_delay = delay + jitter
                            logger.warning(
                                f"Middleman API attempt {attempt + 1} failed due to service unavailable. "
                                f"Retrying in {total_delay:.2f} seconds..."
                            )
                            await asyncio.sleep(total_delay)
                            continue
                    if response.status != 200:
                        error_text = await response.text()
                        error_result = {
                            "error": f"{response.status}, {error_text}",
                            "outputs": [],
                            "non_blocking_errors": [
                                f"HTTP {response.status}: {error_text}"
                            ],
                        }
                        return error_result

                    result = await response.json()
                    if "outputs" not in result:
                        result["outputs"] = [
                            {
                                "completion": result.get("completion", ""),
                                "function_call": result.get("function_call", None),
                                "stop_reason": result.get("stop_reason", "length"),
                            }
                        ]
                    return result

            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    jitter = random.uniform(0, 0.1 * delay)
                    total_delay = delay + jitter
                    logger.warning(
                        f"Middleman API request failed (attempt {attempt + 1}): {str(e)}. "
                        f"Retrying in {total_delay:.2f} seconds..."
                    )
                    await asyncio.sleep(total_delay)
                    continue
                logger.error(f"Error in post_completion: {str(e)}")
                logger.error("Full traceback:", exc_info=True)
                return {"error": str(e), "outputs": [], "non_blocking_errors": [str(e)]}
