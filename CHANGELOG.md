# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.1.0] - 2026-09-15

### 新增

- 项目初始化：公开仓库 `qiutuan/rulefield`（轻量规则化文本字段抽取引擎，非 RAG / 无 LLM）。
- 设计文档定稿：
  - `docs/architecture.md` — 架构设计与模块划分。
  - `docs/template-schema.md` — 模板 YAML Schema 设计定稿。
  - `docs/implementation-plan.md` — 分阶段实现计划（Phase 0–7）。
  - `docs/architecture-diagram.html` — 架构可视化图。
- 设计澄清（R1–R5）与设计决策记录：
  - `docs/adr.md` — ADR-001..005（记录模型两级收敛 / 正则超时语义 / 热加载任务快照 / 去重作用域 / fallback 策略语义）。

### 待办（进入编码阶段后逐项落实）

- M1 模板引擎 / M2 模板库管理 / M3 批量执行器 / M4 输出模块 / M5 测试工作台 / M6 CLI 与配置。
- 单元测试覆盖率 ≥ 80%，集成测试与 7 项验收标准自测。
