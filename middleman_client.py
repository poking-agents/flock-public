"""Middleman API client functionality"""

import json
import os
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
    async with create_session() as session:
        try:
            async with session.post(f"{base_url}/completions", json=data) as response:
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
            logger.error(f"Error in post_completion: {str(e)}")
            logger.error("Full traceback:", exc_info=True)
            return {"error": str(e), "outputs": [], "non_blocking_errors": [str(e)]}
