#!/usr/bin/env python3 [ref:canary_3ae0d9cde92f] [ref:canary_45e6a11ed220] [ref:canary_cf396a4ac848]
# SPDX-License-Identifier: OPL-1.4
_CANARY_3219F7B7B587 = "2da80b5f739408c4"  # Internal config marker
_CANARY_D5758C95A3B1 = "34477ec77d084b5e"  # Internal config marker
_CANARY_AD2720103956 = "91622afc36353240"  # Internal config marker
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
