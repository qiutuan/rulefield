"""Phase 0 冒烟测试：包可导入、版本正确、规划模块齐全、CLI 命令骨架（无网络依赖）。"""

from __future__ import annotations

from rulefield import __version__
from rulefield.cli.app import app
from typer.testing import CliRunner

runner = CliRunner()


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_plan_modules_importable() -> None:
    from rulefield import cli, config, executor, output, template, workbench  # noqa: F401


def test_plan_packages_have_docstrings() -> None:
    import rulefield.executor as e
    import rulefield.output as o
    import rulefield.template as t
    import rulefield.workbench as w

    for mod in (t, e, o, w):
        assert mod.__doc__ is not None and "规划导出" in mod.__doc__


def test_cli_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("extract", "test", "validate", "benchmark", "diff", "list"):
        assert cmd in result.output


def test_cli_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    # no_args_is_help 输出帮助，但该 typer 版本无参调用退出码为 2
    assert result.exit_code == 2
    assert "--help" in result.output


def test_cli_stub_prints_phase() -> None:
    result = runner.invoke(app, ["extract"])
    assert result.exit_code == 0
    assert "Phase 6" in result.output
