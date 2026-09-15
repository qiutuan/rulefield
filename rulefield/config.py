"""全局配置（M6）。

Phase 0 仅声明模块与导出规划，完整实现随 Phase 6 交付。

规划导出：
- ``RulefieldConfig``：冻结 dataclass，聚合编码/并发/输出/热加载/checkpoint/regex 配置。
- ``load_config(path | None) -> RulefieldConfig``：从 YAML 加载，缺省使用内置默认值。
"""

from __future__ import annotations
