# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Compatibility setup.py for older zc.buildout develop installs."""

from pathlib import Path

from setuptools import find_packages
from setuptools import setup


ROOT = Path(__file__).parent


def read_version():
    namespace = {}
    version_file = ROOT / "src" / "Products" / "OpenODBCDA" / "_version.py"
    exec(version_file.read_text(encoding="utf-8"), namespace)
    return namespace["__version__"]


setup(
    name="Products.OpenODBCDA",
    version=read_version(),
    description="An open ODBC Database Adapter for Zope 5 and Zope 6.",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    license="MIT",
    author="Rune Ketil Fredriksen and contributors",
    project_urls={
        "Homepage": "https://github.com/fixader/Products.OpenODBCDA",
        "Repository": "https://github.com/fixader/Products.OpenODBCDA",
        "Issues": "https://github.com/fixader/Products.OpenODBCDA/issues",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Zope",
        "Framework :: Zope :: 5",
        "Framework :: Zope :: 6",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Topic :: Database",
    ],
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    package_data={"Products.OpenODBCDA": ["www/*.dtml"]},
    python_requires=">=3.8",
    install_requires=[
        "Products.ZSQLMethods>=3.15",
        "pyodbc>=5.0",
    ],
)
