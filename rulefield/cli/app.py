"""rulefield CLI 入口。

Phase 0 注册命令骨架（空命令组），各命令功能随对应阶段交付：
- extract（Phase 6）/ benchmark（Phase 6）
- test（Phase 5）/ diff（Phase 5）
- validate（Phase 4）/ list（Phase 4）
"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="rulefield",
    help="轻量规则化文本字段抽取引擎：模板驱动，非 RAG / 无 LLM / 零外部服务。",
    no_args_is_help=True,
)

_PHASE: dict[str, str] = {
    "extract": "Phase 6",
    "test": "Phase 5",
    "validate": "Phase 4",
    "benchmark": "Phase 6",
    "diff": "Phase 5",
    "list": "Phase 4",
}


def _not_implemented(cmd: str) -> None:
    typer.echo(f"[rulefield] `{cmd}` 为命令骨架，将在 {_PHASE[cmd]} 实现。")


@app.command()
def extract() -> None:
    """批量抽取：按模板从文本/文件/目录/stdin 抽取字段并导出结构化结果。"""
    _not_implemented("extract")


@app.command()
def test() -> None:
    """测试工作台：字段级实时预览 / 回归报告 / 模板 diff。"""
    _not_implemented("test")


@app.command()
def validate() -> None:
    """校验模板语法（文件:行:列 级错误定位）。"""
    _not_implemented("validate")


@app.command()
def benchmark() -> None:
    """性能基准：吞吐 / p50-p99 / 命中率 / 峰值 RSS。"""
    _not_implemented("benchmark")


@app.command()
def diff() -> None:
    """模板修改前后对同一样本集的抽取结果差异。"""
    _not_implemented("diff")


@app.command("list")
def list_templates() -> None:
    """列出模板库（分组 / 版本 / 启用状态）。"""
    _not_implemented("list")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
