"""Phase 0 冒烟测试：包可导入、版本正确、规划模块齐全（无网络依赖）。"""

from __future__ import annotations

from rulefield import __version__


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
