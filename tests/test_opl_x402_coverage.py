# SPDX-License-Identifier: OPL-1.4
"""In-process tests for opl_x402.py — validation, code/config generation, CLI subcommands."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import opl_x402 as x402


def _run_main(argv, capsys):
    old = sys.argv
    sys.argv = ["opl_x402.py", *argv]
    try:
        x402.main()
        return 0
    except SystemExit as e:
        return int(e.code or 0)
    finally:
        sys.argv = old


class TestValidateConfig:
    def test_valid(self):
        assert x402.validate_config("0.01", "USDC", "base") == []

    def test_negative_price(self):
        errs = x402.validate_config("-1", "USDC", "base")
        assert any("positive" in e for e in errs)

    def test_bad_price(self):
        errs = x402.validate_config("abc", "USDC", "base")
        assert any("Invalid price" in e for e in errs)

    def test_bad_asset(self):
        errs = x402.validate_config("1", "DOGE", "base")
        assert any("Unsupported asset" in e for e in errs)

    def test_bad_chain(self):
        errs = x402.validate_config("1", "USDC", "ripple")
        assert any("Unsupported chain" in e for e in errs)


class TestEndpointCode:
    def test_fastapi_contains_markers(self):
        code = x402._fastapi_code(0.01, "USDC", "base", "Premium")
        assert "FastAPI" in code
        assert "402" in code
        assert "0.01" in code
        assert "USDC" in code
        assert "base" in code

    def test_flask_contains_markers(self):
        code = x402._flask_code(5.0, "USDT", "polygon", "Access")
        assert "Flask" in code
        assert "5.0" in code
        assert "USDT" in code
        assert "polygon" in code

    def test_build_endpoint_unknown_framework_keyerror(self):
        with pytest.raises(KeyError):
            x402._build_endpoint_code("express", 1.0, "USDC", "base", "x")


class TestGenerateConfig:
    def test_default_recipient(self):
        cfg = x402.generate_config(1.0, "USDC", "base", x402.DEFAULT_RECIPIENT)
        assert cfg["x402Version"] == 1
        assert cfg["config"]["price"] == 1.0
        assert cfg["config"]["asset"] == "USDC"
        assert cfg["config"]["payTo"] == x402.DEFAULT_RECIPIENT
        assert "base" in cfg["config"]["supportedChains"]

    def test_custom_recipient(self):
        cfg = x402.generate_config(2.5, "DAI", "ethereum", "0xABC")
        assert cfg["config"]["payTo"] == "0xABC"
        assert cfg["config"]["asset"] == "DAI"


class TestMain:
    def test_version(self, capsys):
        rc = _run_main(["--version"], capsys)
        assert rc == 0
        assert "OPL Adoption Tools 1.4" in capsys.readouterr().out

    def test_no_command_exits(self, capsys):
        rc = _run_main([], capsys)
        assert rc == 1

    def test_generate_fastapi_stdout(self, capsys):
        rc = _run_main(["generate", "--framework", "fastapi", "--price", "0.01"], capsys)
        assert rc == 0
        assert "FastAPI" in capsys.readouterr().out

    def test_generate_flask_stdout(self, capsys):
        rc = _run_main(["generate", "--framework", "flask", "--price", "1.0"], capsys)
        assert rc == 0
        assert "Flask" in capsys.readouterr().out

    def test_generate_output_file(self, tmp_path, capsys):
        out = tmp_path / "ep.py"
        rc = _run_main(["generate", "--framework", "fastapi", "--price", "0.5",
                        "--output", str(out)], capsys)
        assert rc == 0
        assert out.exists()
        assert "FastAPI" in out.read_text()

    def test_generate_validation_failure(self, capsys):
        rc = _run_main(["generate", "--framework", "fastapi", "--price", "bad"], capsys)
        assert rc == 1

    def test_config_stdout(self, capsys):
        rc = _run_main(["config", "--price", "5.0", "--recipient", "0xABC"], capsys)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["config"]["price"] == 5.0

    def test_config_output_file(self, tmp_path, capsys):
        out = tmp_path / "c.json"
        rc = _run_main(["config", "--price", "1.0", "--output", str(out)], capsys)
        assert rc == 0
        data = json.loads(out.read_text())
        assert data["x402Version"] == 1

    def test_config_default_recipient_warns(self, capsys):
        rc = _run_main(["config", "--price", "1.0"], capsys)
        assert rc == 0
        err = capsys.readouterr().err
        assert "zero address" in err

    def test_config_validation_failure(self, capsys):
        rc = _run_main(["config", "--price", "bad"], capsys)
        assert rc == 1

    def test_chains(self, capsys):
        rc = _run_main(["chains"], capsys)
        assert rc == 0
        assert "Supported chains" in capsys.readouterr().out

    def test_assets(self, capsys):
        rc = _run_main(["assets"], capsys)
        assert rc == 0
        assert "Supported stablecoins" in capsys.readouterr().out
