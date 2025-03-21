from setuptools import setup, find_packages

def read_requirements():
    with open('requirements.txt') as req:
        content = req.read()
        requirements = []
        for line in content.split('\n'):
            if line and not line.startswith('#'):
                requirements.append(line.strip())
    return requirements

setup(
    name="flock",
    version="0.1.0",
    packages=find_packages(),
    install_requires=read_requirements(),
    python_requires=">=3.7",
)