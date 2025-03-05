"""Configuration settings for flock"""

from pathlib import Path

# API settings
PORT = 46397
API_BASE_URL = f"http://localhost:{PORT}"

# Directory settings
REPO_ROOT = Path(__file__).parent
STATES_DIR = REPO_ROOT / "states"
STATES_DIR.mkdir(parents=True, exist_ok=True)
