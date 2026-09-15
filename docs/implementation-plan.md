# rulefield 分阶段实现计划（Phase 0–7）

> 每阶段结束给出**自测证据**（测试命令输出、覆盖率、验收指标），经用户确认后再进入下一阶段。
> git 原则：小步提交，一个逻辑单元一次 commit；**禁止一次性提交一大部分代码**；每次提交前跑 `pytest + ruff`。

## 0. 阶段总览

| 阶段 | 范围 | 关键产出 | 独立验证 |
| --- | --- | --- | --- |
| P0 | 项目脚手架 | pyproject.toml、Makefile、包骨架、CI 友好测试基线 | `pip install -e .` + `rulefield --help` + pytest 空跑 |
| P1 | M1 模板引擎 | model/schema/loader/compiler/pipeline/validation/matcher | 模板模块单测覆盖率 ≥ 80% |
| P2 | M3 批量执行器 | inputs/encoding/workers/checkpoint/dedup、流式、三模式 | 编码/流式/坏行隔离单测 |
| P3 | M4 输出模块 | CSV(BOM)/MD/JSONL、元数据、原子写、failures.jsonl | BOM/格式/原子性断言 |
| P4 | M2 模板库管理 | 热加载、validate --all、加载隔离、内置 3 模板 + 示例数据 | 验收 3、4 条自动化 |
| P5 | M5 测试工作台 | preview / regression / diff | 预览输出单测 + 手测 |
| P6 | M6 CLI 集成 | 全部命令、--dry-run、全局配置、README、最佳实践、CHANGELOG v0.1.0 | `rulefield --help` 全命令冒烟 |
| P7 | 验收 | 7 项验收标准逐条自测 + 文档化 | `make accept` 全绿 |

## 1. Phase 0 — 项目脚手架

**任务**
1. `pyproject.toml`：包名 `rulefield`、版本 0.1.0、`requires-python >=3.10`；运行时依赖 `typer`/`pyyaml`/`charset-normalizer`/`regex`；开发依赖 `pytest`/`pytest-cov`/`ruff`/`black`；入口 `rulefield = rulefield.cli.app:main`。
2. `Makefile`：`install / dev-install / test / lint / format / bench / accept / quickstart` 目标。
3. 包骨架 `rulefield/`（各模块 `__init__.py` + 版本号），`tests/` 与 `conftest.py`。
4. ruff/black 配置（line-length 100）。

**验证**：`make dev-install && rulefield --help` 正常；`pytest` 通过（冒烟用例）。

**提交**：`feat: P0 项目脚手架（pyproject/Makefile/包骨架）`，随后 `test: P0 冒烟测试`。

## 2. Phase 1 — M1 模板引擎（核心）

**任务（按依赖序）**
1. `template/model.py`：Template/Field/Strategy/PipelineStep/ValidationRule dataclass。
2. `template/schema.py`：带行:列定位的校验器（§11 规则全量）。
3. `template/loader.py`：分组加载、extends/field_sets 合并、enabled/version、失败隔离。
4. `template/compiler.py`：占位符→正则（转义+槽位+slot_regex）、命名组映射、编译 flags。
5. `template/pipeline.py`：trim/type/regex_replace/default/unit/upper/lower。
6. `template/validation.py`：required/pattern/length/enum/range。
7. `template/matcher.py`：first_match/all_match/fallback、regex 超时防护。
8. `engine/record.py` + `engine/runner.py`（单文本三模式）。

**测试**：占位符编译等价性、pipeline 逐 op、校验语义、策略解析、Schema 错误行列号、超时防护（构造 `(a+)+$` 样本）。

**验证**：`pytest tests/template -q` 全绿；`coverage` 模板模块 ≥ 80%。

**提交**：按依赖拆 3–4 个 commit（model+schema → loader → compiler → matcher/pipeline/validation），每个带测试。

## 3. Phase 2 — M3 批量执行器

**任务**
1. `executor/encoding.py`：BOM 优先 + charset-normalizer 采样 + 降级链。
2. `executor/inputs.py`：text/file/dir(递归)/stdin/filelist；1MB 流式分块与行边界保持；segment 跨块切分。
3. `executor/workers.py`：线程池 + 有序输出 + 单条/单文件失败隔离 + 统计。
4. `executor/checkpoint.py` + `dedup.py`。

**测试**：编码矩阵（utf-8/gbk/gb18030/utf-16/latin-1 样例）、大文件分块正确性（构造 > 块大小的文件）、坏行/乱码行不中断、去重、checkpoint 续跑。

**验证**：`pytest tests/executor -q` 全绿；构造 100MB 文件测峰值 RSS < 200MB（标记 slow 用例）。

**提交**：encoding → inputs → workers → checkpoint/dedup，各带测试。

## 4. Phase 3 — M4 输出模块

**任务**
1. `output/writer.py`：CSV（UTF-8 BOM）/Markdown/JSONL；列序=字段声明序；extra 列（keep_extra）；临时文件+原子 rename。
2. `output/metadata.py`：source/location/template/version/strategy/elapsed/confidence 组装。
3. `failures.jsonl` 独立落盘（含原文本、原因、上下文）。

**测试**：BOM 字节断言、MD 表结构、JSONL 可回读、原子性（模拟中断不留半文件）、失败样本字段完整。

**验证**：`pytest tests/output -q` 全绿；Excel 打开无乱码（BOM 断言即可）。

## 5. Phase 4 — M2 模板库管理 + 内置模板

**任务**
1. 热加载：mtime 轮询（默认 3s，可配），模板库原子换引；watchdog 可选。
2. `validate --all` 命令（可先接 CLI 冒烟，正式 CLI 在 P6）。
3. 内置模板：`logs/nginx_access.yml`、`contracts/amount.yml`、`invoices/order_receipt.yml` + `examples/data/` 示例数据。
4. 模板级 `encoding_fallback` 覆盖。

**测试**：修改模板文件→轮询生效（验收 3）；坏模板报 行:列 且其余模板正常（验收 4）。

**验证**：`pytest tests/template tests/integration -q` 全绿。

## 6. Phase 5 — M5 测试工作台

**任务**
1. `workbench/preview.py`：字段级实时预览（捕获组→pipeline→最终值、失败原因高亮）。
2. `workbench/regression.py`：正例/反例目录（`samples/<模板>/positive|negative`），每字段命中率报告、失败样例清单。
3. `workbench/diff.py`：`--before/--after/--samples` 同一样本集抽取差异表。

**测试**：preview 输出正确性、regression 命中率统计、diff 行级变化。

**验证**：`pytest tests/workbench -q` 全绿 + 手测截图。

## 7. Phase 6 — M6 CLI 集成 + 文档收口

**任务**
1. Typer 命令全量：`extract / test / validate / benchmark / diff / list`；`--dry-run`、`--format`、`--output`、`--workers`、`--checkpoint`、`--resume`、`--dedup-by`。
2. 全局配置文件（YAML）：默认编码/并发/输出目录/失败样本路径/热加载开关。
3. `rulefield/config.py` 对接；错误人话化。
4. README 完整版（安装/快速开始/模板语法/CLI 参考/架构图）、`docs/best-practices.md`（正则陷阱、性能注意事项）、CHANGELOG v0.1.0。

**验证**：全命令冒烟 + `--help` 截图；README 按 5 分钟上手自测走查。

## 8. Phase 7 — 验收（7 项标准逐条自测）

| # | 验收项 | 自测方式 |
| --- | --- | --- |
| 1 | 1 万行 nginx 命中率 ≥ 99% | 构造 10k 行日志 → `extract` → 断言命中率 |
| 2 | 坏行+乱码行不中断，失败样本落盘 | 混入 1 坏行 + 1 GBK 乱码行 → 断言任务完成 + failures.jsonl 含 2 条 |
| 3 | 热加载生效 | 改模板文件 → 3s 内新字段生效 |
| 4 | 语法错误输出具体位置且不影响其他模板 | 注入坏模板 → 断言 行:列 错误 + 其余模板正常 |
| 5 | 100MB 流式内存峰值 < 200MB | `/usr/bin/time -v` / resource 峰值 RSS |
| 6 | 工作台实时预览 | 交互命令手测 + preview 单测 |
| 7 | CSV Excel 无乱码 | UTF-8 BOM 断言 |

**产出**：`docs/acceptance.md`（逐条证据：命令、输出、数值）；`make accept` 一键复现。

## 9. 风险与对策

| 风险 | 对策 |
| --- | --- |
| 灾难性回溯拖垮批量任务 | regex timeout（D1）+ lint 静态告警 + benchmark 覆盖 |
| 编码误判导致乱码/崩溃 | BOM 优先 + 采样探测 + latin-1 兜底（永不崩溃），失败按行隔离 |
| 线程并发输出乱序 | 按输入序收集（D4），单测覆盖乱序断言 |
| 热加载引发半加载状态 | 模板库整体原子换引（D7），坏模板保留上一版 |
| 覆盖率目标难达成 | P1 起按模块写测试，`make test` 带 coverage 门禁（≥ 80%） |
| 大文件去重内存膨胀 | 去重集合内存 + 阈值告警（D9），文档明示限制 |
