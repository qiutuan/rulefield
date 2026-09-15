"""输出模块（M4，Phase 3 交付）。

规划导出：
- writer：RecordWriter — CSV(UTF-8 BOM) / Markdown / JSONL；临时文件 + 原子 rename
- metadata：MetadataFactory — 来源/行号/模板名+版本/策略/耗时/置信元数据组装
- failures：failures.jsonl 失败样本落盘（只收 failed 记录，ADR-001）
"""

from __future__ import annotations
