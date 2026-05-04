#!/usr/bin/env python
import os
from setuptools import find_packages, setup


def parse_requirements(filename):
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]


setup(
    name="MTL",
    version="0.0.1",
    description="HMER System: Handwritten Mathematical Expression Recognition",
    author="",
    author_email="",
    url="",
    install_requires=parse_requirements("requirements.txt"),
    packages=find_packages(),
)
