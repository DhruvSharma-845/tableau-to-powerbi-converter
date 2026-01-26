#!/usr/bin/env python3
"""
Setup script for Tableau to Power BI Converter.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

setup(
    name="tableau-to-powerbi-converter",
    version="1.0.0",
    description="Convert Tableau workbooks (.twbx/.twb) to Power BI reports",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/tableau-to-powerbi-converter",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "lxml>=4.9.0",
        "pandas>=2.0.0",
        "openai>=1.0.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "tableau2pbi=main:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Database",
        "Topic :: Office/Business :: Office Suites",
    ],
    keywords="tableau powerbi conversion migration bi analytics",
)
