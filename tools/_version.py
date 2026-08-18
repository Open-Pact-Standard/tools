#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.4
"""Single source of truth for OPL Adoption Tools version.

All CLI tools import __version__ from this module.

IMPORTANT: This module MUST stay side-effect-free.

It is imported at build time by setuptools' dynamic version resolution
(see [tool.setuptools.dynamic] in pyproject.toml) when `pip install`
builds the package from sdist in a clean environment. Any side effects
here — heavy imports, network calls, file I/O, logging configuration,
argparse use, etc. — will break `pip install opl-tools` for downstream
users. Keep this file to module-level __version__ (and any pure-Python
imports of the standard library only).
"""

__version__ = "1.4"
