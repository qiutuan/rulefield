"""批量执行器（M3，Phase 2 交付）。

规划导出：
- inputs：InputSource — text / file / dir / stdin / filelist；流式分块与行/段边界保持
- encoding：detect_encoding — BOM 优先 + 采样探测 + 降级链
- workers：BatchExecutor — 线程池并发、按输入序输出、失败隔离、按 reason 分组汇总
- checkpoint：Checkpoint — 已处理文件清单 + global_dedup 已见 key 集合持久化（ADR-004）
- dedup：Deduper — 字段组合 key 去重（默认单文件作用域）
"""

from __future__ import annotations
