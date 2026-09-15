# rulefield 架构设计与模块划分（v0.1.0 设计定稿）

> 状态：设计稿，待用户确认后逐阶段实现。文档会随实现演进同步更新。

## 1. 定位与硬性目标

- **定位**：轻量规则化文本字段抽取引擎。模板驱动、纯规则、无机器学习。
- **明确排除**：向量检索、Embedding、LLM 调用、知识库、数据库、Web 框架、任何外部服务。
- **性能目标**：
  - 常驻内存 < 100MB（常规任务）；100MB 单文件流式处理内存峰值 < 200MB；
  - 单核 CPU 行模式吞吐 ≥ 10 万行/分钟（≈1667 行/秒，为基准留足余量）；
  - 10MB 日志行模式抽取 < 10s（单机单核参考值）。

## 2. 总体架构

四层 + 横向支撑：

```
┌────────────────────────────────────────────────────────────────────┐
│ CLI 层（rulefield.cli）                                              │
│  extract │ test │ validate │ benchmark │ diff │ list   (Typer)      │
└───────────────────────────┬────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────────┐
│ 编排层（rulefield.config + orchestrator）                            │
│  全局配置 → 模板库(TemplateLibrary) → 执行器(Runner) → 输出器(Writer) │
│  统一异常捕获与上下文日志（文件/行号/模板名/堆栈）                      │
└───────────────────────────┬────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────────┐
│ 领域层：模板引擎（rulefield.template）＝ M1 核心                      │
│  schema校验 → loader加载(extends/field_sets/热加载)                  │
│  → compiler编译(占位符→正则) → matcher匹配(strategies)                │
│  → pipeline后处理 → validation校验                                    │
└───────────────────────────┬────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────────┐
│ 基础设施层                                                           │
│  executor：inputs(输入源) / encoding(编码探测) / workers(并发)        │
│            / checkpoint(断点) / dedup(去重)   （M3）                  │
│  output：writer(CSV/MD/JSONL) / metadata（M4）                        │
│  支撑：utils(日志/原子写/计时) / lint(正则复杂度检查) / bench(基准)     │
└────────────────────────────────────────────────────────────────────┘
```

**主数据流**（行模式示例）：

```
输入源(text/file/dir/stdin/filelist)
  → 编码探测(采样+BOM+降级链)           encoding.py
  → 流式分块(1MB 二进制块, 行边界切分)   inputs.py
  → 每行 → 模板匹配(matcher, regex 超时防护)
  → 字段 pipeline → 校验
  → ExtractRecord（含元数据）           engine/record.py
  → 有序收集 → writer(临时文件+原子 rename)
  → 汇总统计 + failures.jsonl 独立落盘
```

## 3. 模块划分

| 模块 | 职责 | 关键类 / 接口 | 对应需求 |
| --- | --- | --- | --- |
| `rulefield.cli` | Typer 命令：`extract / test / validate / benchmark / diff / list`；`--dry-run`；人话化错误 | `app.py`、`formatters.py` | M6 |
| `rulefield.config` | 全局配置 YAML → 冻结 dataclass；默认编码/并发/输出目录/失败样本路径/热加载开关 | `RulefieldConfig` | M6 |
| `rulefield.template.model` | 模板领域模型：Template/Field/Strategy/PipelineStep/ValidationRule | dataclasses | M1 |
| `rulefield.template.schema` | 模板 Schema 校验：必填键、类型、枚举、互斥、重复名、未知 op；**输出 文件:行:列 级错误** | `TemplateValidator` | M1/M2 |
| `rulefield.template.loader` | 分组加载（`templates/<group>/<name>.yml`）、extends 继承、field_sets 复用、版本/启用开关、热加载（mtime 轮询）、失败隔离（坏模板保留上一可用版本）、任务快照（ADR-003） | `TemplateLibrary` | M2 |
| `rulefield.template.compiler` | 占位符 `{{slot}}` → 命名捕获组；字面量自动转义；slot_regex 可配；策略编译 | `TemplateCompiler` | M1 |
| `rulefield.template.matcher` | 多策略解析：`first_match / all_match / fallback`；regex 超时（默认 0.1s）防灾难回溯 | `TemplateMatcher` | M1 |
| `rulefield.template.pipeline` | 字段后置处理链：trim / type / regex_replace / default / unit（+upper/lower） | `Pipeline` | M1 |
| `rulefield.template.validation` | 字段级校验：required / pattern / length / enum（+range） | `FieldValidator` | M1 |
| `rulefield.engine.runner` | 单文本抽取入口；line/document/segment 三种模式调度 | `Runner` | M3 |
| `rulefield.engine.record` | 抽取结果模型：FieldResult/ExtractRecord/状态机与置信标记 | dataclasses | M4 |
| `rulefield.executor.inputs` | 输入源抽象：text/file/dir(递归)/stdin/filelist；流式分块；分块间行/段边界保持 | `InputSource` 协议 | M3 |
| `rulefield.executor.encoding` | BOM 优先 → 采样探测（charset-normalizer）→ 降级链（utf-8→gb18030→latin-1，可配） | `detect_encoding` | M3 |
| `rulefield.executor.workers` | 线程池并发；**按输入序输出**；单条/单文件失败隔离；任务汇总按 reason 分组统计（含 regex_timeout，ADR-002） | `BatchExecutor` | M3 |
| `rulefield.executor.checkpoint` | 断点续跑：已处理文件清单 + global_dedup 已见 key 集合持久化（ADR-004）；resume 跳过已完成文件 | `Checkpoint` | 冗余/容错 |
| `rulefield.executor.dedup` | 按字段组合 key 去重（保留首现） | `Deduper` | 冗余/容错 |
| `rulefield.output.writer` | CSV(UTF-8 BOM)/Markdown/JSONL；列序=字段声明序；extra 列；**临时文件+原子 rename** | `RecordWriter` 协议 | M4 |
| `rulefield.output.metadata` | 元数据组装：来源文件/行号/模板名+版本/耗时/置信标记 | `MetadataFactory` | M4 |
| `rulefield.workbench.preview` | `test <模板>` 字段级实时预览：捕获组→pipeline→最终值；未命中/失败原因高亮 | `Previewer` | M5 |
| `rulefield.workbench.regression` | 正例+反例回归；每字段命中率报告；失败样例清单 | `RegressionRunner` | M5 |
| `rulefield.workbench.diff` | 模板修改前后同一样本集抽取结果 diff | `TemplateDiff` | M5 |
| `rulefield.lint` | 正则复杂度静态检查：嵌套量词告警（如 `(a+)+`） | `regex_lint` | 非功能 |
| `rulefield.bench` | benchmark：吞吐 lines/s、p50/p95/p99、命中率、峰值 RSS | `Benchmark` | 非功能 |
| `rulefield.utils` | 日志、原子写、计时、流式读取 | — | 非功能 |

## 4. 关键设计决策

| # | 决策 | 理由 |
| --- | --- | --- |
| D1 | 正则用 `regex` 库并带 `timeout`（默认 0.1s/次） | 标准 `re` 无超时；灾难性回溯会拖垮整批任务；超时样本按失败落盘不中断，超时计数进任务汇总与 benchmark（ADR-002） |
| D2 | 编码探测用 `charset-normalizer`（BOM 优先 + 采样 64KB + 降级链） | chardet 已进入维护模式；UTF-16 等靠 BOM 先行判断；latin-1 兜底保证永不崩溃 |
| D3 | 流式分块：1MB 二进制块 + 行边界切分，逐块解码 | >1GB 文件不 OOM；解码错误按行隔离到 failures.jsonl |
| D4 | 并发模型：线程池 + **按输入序收集输出** | 输出确定性优先；regex 库 C 实现部分释放 GIL；进程模型留作后续优化项 |
| D5 | 多文件并行（文件粒度）、单文件行/段模式块级并行 | 文档模式需整篇在内存，按文件并行更稳 |
| D6 | 输出采用 临时文件+os.replace 原子 rename | 进程中断不产生半个文件 |
| D7 | 热加载默认 mtime 轮询（间隔可配，默认 3s） | 零额外依赖；模板库整体原子换引 |
| D8 | 模板加载失败隔离：坏模板报 文件:行:列 并拒绝加载，**保留上一可用版本**，其余模板不受影响 | 满足验收第 4 条 |
| D9 | 去重默认**单文件作用域**；`global_dedup: true` 时已见 key 集合持久化到 checkpoint 文件，与文件级 checkpoint 同步提交（ADR-004）；超大规模（>100 万 key）给告警 | 默认内存可控；全局去重与断点续跑自洽 |
| D10 | YAML 用 `PyYAML`(CLoader) 而非 ruamel.yaml | 模板是机器读写的配置，无 round-trip 保留注释需求；CLoader 加载快数倍；错误定位自研校验器已覆盖 |
| D11 | 每字段三态：captured / missing / invalid，逐字段可解释 | 支撑置信标记与工作台 diff |
| D12 | 两级记录模型：字段级 captured/missing/invalid 互斥三态，记录级由字段级推导（ADR-001）；置信仅作输出元数据列 | 验收第 1 条“命中率”有明确定义口径 |
| D13 | 批量任务启动时对所用模板做**不可变快照**（deep copy 编译产物）；运行期热加载不影响在途任务，新任务取最新版（ADR-003） | 在途结果可复现；模板热更新不破坏一致性 |

## 5. 记录模型（两级，ADR-001）

### 5.1 字段级状态（互斥三态）

| 状态 | 含义 |
| --- | --- |
| `captured` | 命中且 pipeline 完整执行成功 |
| `missing` | 未命中（无捕获组原始值） |
| `invalid` | 命中，但 pipeline（如类型转换）或 validate（pattern/length/enum/range）失败 |

### 5.2 记录级状态（由字段级推导，按优先级）

1. 任一 **required** 字段为 `missing` 或 `invalid` → **failed**（无论其他字段是否捕获，样本进入 failures.jsonl）；
2. 否则全部声明字段 `captured` 且无 `invalid` → **success**；
3. 否则（存在非 required 字段 `missing` 或 `invalid`）→ **partial**；
4. 无任何策略命中（零字段捕获）→ **failed**（reason=`no_match`）。

### 5.3 置信标记（仅输出元数据，不参与状态机）

`complete / partial / low` 由记录状态映射（success→complete、partial→partial、failed→low），只写入输出列。

### 5.4 数据模型

```python
@dataclass
class FieldResult:
    name: str
    raw: str | None            # 捕获组原始文本
    value: Any                 # pipeline 后最终值
    status: str                # captured | missing | invalid（互斥）
    error: str | None          # invalid 原因（类型转换失败/校验失败等）

@dataclass
class ExtractRecord:
    fields: dict[str, FieldResult]
    status: str                # success | partial | failed（由 5.2 推导）
    confidence: str            # complete | partial | low（仅元数据，5.3）
    template: str
    template_version: str
    strategy: str              # 生效策略 id（None=未采用）
    source: str                # 来源文件/stdin/文本
    location: str              # 行号或段号
    elapsed_ms: float
    error: str | None
```

## 6. 错误处理与可观测性（三层隔离）

| 层 | 失败形态 | 处理 |
| --- | --- | --- |
| 单条文本 | 解码失败 / regex 超时 / required 字段缺失或 invalid / 其他校验失败 | 记为 failed 记录 → failures.jsonl；不中断；任务汇总按 reason 分组统计（ADR-002） |
| 单文件 | 读取异常 | 捕获 + 上下文日志（文件名/模板名/堆栈）→ 记录到失败清单；继续下一文件 |
| 模板加载 | Schema 非法 / 正则编译失败 | 报 `文件:行:列` 错误；跳过该模板（保留上一版）；其余模板正常 |

日志格式：`[rulefield] WARN file=nginx.log line=42 template=nginx_access err=...`

## 7. 性能设计要点

- 内存预算（100MB 文件场景）：块缓冲 2×1MB + 单块结果窗口（有序输出，写完即弃）+ 模板库（常驻 < 5MB）≈ 峰值远低于 200MB。
- 吞吐估算：200B/行 × 1667 行/秒 = 0.33MB/s 即达标；`regex` 单次匹配 µs 级，瓶颈在 IO 与 Python 逐行循环，预留 10 倍余量。
- benchmark 输出：吞吐、p50/p95/p99 单行耗时、命中率、失败数、峰值 RSS（resource.getrusage）。

## 8. 依赖清单

- 运行时：`typer`、`pyyaml`、`charset-normalizer`、`regex`
- 开发：`pytest`、`ruff`（Phase 0 起按用户约束收窄，格式化走 `ruff format`）
- 明确不引入：数据库、Web 框架、向量/LLM 相关库
