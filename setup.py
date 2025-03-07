from setuptools import setup, find_packages

setup(
    name="flock",
    version="0.1.0",
    packages=find_packages(include=["handlers", "workflows", "type_defs", "manifest_utils", "modular", "triframe", "utils"]),
    install_requires=[
        # Add dependencies from requirements.txt here
    ],
    python_requires=">=3.7",
)