# Changelog

All notable changes to the OPL Adoption Tools will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- **`--version` flag** to all 6 CLI tools (`opl_check`, `opl_init`, `opl_migrate`, `opl_registry_gen`, `opl_spdx_inject`, `opl_x402`). Each tool now responds to `--version` with "OPL Adoption Tools 1.2.0".
- **Single-source version** in `tools/__init__.py`. The version string is defined once in `__init__.py` and read by all tools at module level, eliminating the need to update 7 separate copies when bumping.
- **`scripts/check_version.py`** — standalone CI script that verifies all tools use `__version__` (f-string pattern) instead of hardcoded version strings, and that `__init__.py` contains a `__version__` definition.
- **CI lint step** for version consistency: the GitHub Actions workflow now runs `python scripts/check_version.py` and `py_compile scripts/check_version.py` to validate version consistency and syntax.
- **`__version__` in `tools/__init__.py`** as the canonical version source.

### Changed

- Each tool reads `__version__` from `tools/__init__.py` at module level using a regex search with `SystemExit` on failure (no silent fallback).
- The `--version` argparse argument now uses `f"OPL Adoption Tools {__version__}"` instead of a hardcoded string.
- Cleaned up version reading internals (removed redundant aliased imports and underscore-prefixed variables).

### Fixed

- `tools/__init__.py` now contains `__version__ = "1.2.0"` (was missing after initial setup).
- `opl_x402.py` added to the CI syntax check list (was previously missing).
- `FileNotFoundError` handling: if `tools/__init__.py` is missing, tools now print a clear error message instead of crashing with a raw traceback.
- `TOOLS_DIR` references fixed in `tests/test_opl_x402.py`.
