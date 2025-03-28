import asyncio
import os
import pathlib
import sys

import flock.__main__ as main

# Hack to deal with how Vivaria runs agents
parent_dir = str(pathlib.Path(__file__).resolve().parent)
sys.path.append(parent_dir)
os.environ["PYTHONPATH"] = parent_dir

if __name__ == "__main__":
    asyncio.run(main.main())
