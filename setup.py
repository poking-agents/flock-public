from setuptools import setup, find_packages
import re

def read_requirements():
    requirements = []
    
    with open('requirements.txt') as req:
        for line in req:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Skip git URLs as they can't be directly used in install_requires
            if not line.startswith('git+'):
                requirements.append(line)
                
    return requirements

# Print a warning about git dependencies
git_dependencies = []
with open('requirements.txt') as req:
    for line in req:
        if line.strip().startswith('git+'):
            git_dependencies.append(line.strip())

if git_dependencies:
    print("\nWARNING: The following git dependencies will not be installed automatically:")
    for dep in git_dependencies:
        print(f"  - {dep}")
    print("Please install them manually with: pip install -r requirements.txt\n")

setup(
    name="flock",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={"": ["*.json"]},  # Include JSON files
    include_package_data=True,
    install_requires=read_requirements(),
    python_requires=">=3.7",
)