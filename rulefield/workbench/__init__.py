"""测试工作台（M5，Phase 5 交付）。

规划导出：
- preview：Previewer — 字段级实时预览（捕获组 → pipeline → 最终值；失败原因）
- regression：RegressionRunner — 正例/反例回归与每字段命中率报告
- diff：TemplateDiff — 模板修改前后同一样本集抽取差异
"""

from __future__ import annotations
