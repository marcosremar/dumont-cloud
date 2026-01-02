"""
Setup script for Dumont SDK.
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="dumont-sdk",
    version="0.1.0",
    author="Dumont Cloud",
    author_email="dev@dumontcloud.com",
    description="SDK para inferência LLM com failover automático GPU → OpenRouter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dumontcloud/dumont-sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.9",
    install_requires=[
        "httpx>=0.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "dumont=dumont_sdk.cli:main",
        ],
    },
)
