import asyncio
import os
import pathlib
import sys

# Hack to deal with how Vivaria runs agents
parent_dir = str(pathlib.Path(__file__).resolve().parent)
os.environ["PYTHONPATH"] = parent_dir
sys.path.append(parent_dir)

import flock.__main__ as main

if __name__ == "__main__":
    asyncio.run(main.main())
