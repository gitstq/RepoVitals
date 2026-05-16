#!/usr/bin/env python3
"""RepoHealth - Lightweight Git Repository Health Check Engine."""

from setuptools import setup, find_packages

setup(
    name="repohealth",
    version="1.0.0",
    description="Lightweight Git Repository Health Check Engine",
    long_description=open("README.md").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="RepoHealth",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "repohealth=repohealth:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Version Control",
    ],
)
