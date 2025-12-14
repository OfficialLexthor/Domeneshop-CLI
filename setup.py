#!/usr/bin/env python3
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="domeneshop-cli",
    version="1.0.0",
    author="Martin Clausen",
    author_email="post@lexthor.no",
    description="CLI-verktøy for Domeneshop API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ditt-brukernavn/domeneshop-cli",
    py_modules=["domeneshop_cli"],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
        "tabulate>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "domeneshop=domeneshop_cli:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: Name Service (DNS)",
        "Topic :: System :: Systems Administration",
    ],
    keywords="domeneshop dns domain cli api",
)
