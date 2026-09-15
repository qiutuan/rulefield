"""rulefield — 轻量规则化文本字段抽取引擎。

纯规则模板驱动：从日志、合同、接口返回、固定格式单据等非结构化文本中，
按可配置模板批量抽取固定字段并导出结构化结果。
非 RAG / 无 LLM / 零外部服务，可离线运行。

设计基线见 docs/architecture.md；模板语法见 docs/template-schema.md；
已定稿决策见 docs/adr.md（ADR-001..005）。
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
