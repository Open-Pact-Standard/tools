# Contributing to OPL Adoption Tools

Thanks for your interest in improving the Open-Pact License adoption tools.

## Development setup

```bash
git clone https://github.com/Open-Pact-Standard/tools.git
cd tools
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
```

All tools are **zero-dependency** Python scripts — only the standard library is required at runtime. `pytest` is the only dev dependency.

## Running the tools

```bash
# Run any tool directly
python3 tools/opl_init.py --help
python3 tools/opl_spdx_inject.py --help
python3 tools/opl_check.py --help
python3 tools/opl_registry_gen.py --help
python3 tools/opl_migrate.py --help
```

## Running tests

```bash
python3 -m pytest tests/ -v
```

There are 100+ tests covering unit tests and integration tests (full adoption workflow).

To run only unit tests:

```bash
python3 -m pytest tests/ -v --ignore=tests/test_integration.py
```

To run only integration tests:

```bash
python3 -m pytest tests/ -v tests/test_integration.py
```

## Project structure

```
tools/
  opl_init.py             # NOTICE file generator
  opl_spdx_inject.py      # SPDX header injector (60+ languages)
  opl_check.py            # Compliance checker
  opl_registry_gen.py     # REGISTRY.json generator
  opl_migrate.py          # License migration helper
  standard-terms.html     # Standard Terms template
  __init__.py
tests/
  test_spdx_inject.py     # Unit tests for SPDX injector
  test_opl_check.py       # Unit tests for compliance checker
  test_opl_init.py        # Unit tests for NOTICE generator
  test_opl_registry_gen.py # Unit tests for registry generator
  test_opl_migrate.py     # Unit tests for migration helper
  test_integration.py     # Full workflow integration tests
  conftest.py             # Shared pytest configuration
```

## Code style

- **Python 3.9+** — use `from __future__ import annotations` for modern type hints
- **Standard library only** — no external dependencies in tool code
- **Type hints** on all public functions
- **Docstrings** on all modules and public functions
- **argparse** for all CLI tools

## Adding a new tool

1. Create `tools/opl_<name>.py` with a `main()` function and `argparse` CLI
2. Add `tools/__init__.py` import if needed
3. Create `tests/test_<name>.py` with unit tests
4. Update `README.md` with documentation
5. Run the full test suite before submitting your PR

## Submitting changes

1. Fork the repository
2. Create a feature branch (`git checkout -b my-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run `python3 -m pytest tests/ -v` and ensure all tests pass
6. Commit with a descriptive message
7. Open a pull request

## Reporting bugs

Use the [Bug Report](https://github.com/Open-Pact-Standard/tools/issues/new?template=bug_report.md) issue template. Include:
- Which tool is affected
- Steps to reproduce
- Expected vs actual behavior
- Your OS, Python version, and tools commit

## Code of Conduct

This project follows the [Open-Pact Standard Code of Conduct](https://github.com/Open-Pact-Standard/license/blob/main/CODE_OF_CONDUCT.md). Be respectful and constructive.
