from setuptools import setup, find_packages

setup(
    name="agentic-enterprise-workstation",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "aew=aew.cli:main",
        ],
    },
    python_requires=">=3.9",
)
