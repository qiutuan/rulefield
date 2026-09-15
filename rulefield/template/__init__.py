"""模板引擎（M1/M2，Phase 1 交付）。

规划导出：
- model：Template / Field / Strategy / PipelineStep / ValidationRule 领域模型
- schema：TemplateValidator — Schema 校验（文件:行:列 级错误）
- loader：TemplateLibrary — 分组加载 / extends / field_sets / 热加载 / 任务快照（ADR-003）
- compiler：TemplateCompiler — 占位符 → 命名捕获组正则
- matcher：TemplateMatcher — first_match / all_match / fallback + 超时防护（ADR-002/005）
- pipeline：run_pipeline — trim / type / regex_replace / default / unit / upper / lower
- validation：validate_field — required / pattern / length / enum / range
"""

from __future__ import annotations
