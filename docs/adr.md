# 设计决策记录（ADR）

> 本文件固化已确认的设计决策（R1–R5）。此后如需变更，必须提出变更单并获批准，不再口头改动。
> 格式：背景 / 结论 / 理由 / 影响。

## ADR-001 记录模型收敛为两级

**背景**：原设计存在字段级三态（captured/missing/failed）与记录级状态（success/partial/failed）及置信三档（complete/partial/low）重叠，语义边界模糊。

**结论**：
- 字段级状态：`captured` / `missing`（未命中）/ `invalid`（命中但 pipeline 或 validate 失败），三者互斥。
- 记录级状态由字段级推导，按优先级：
  1. 任一 required 字段为 missing 或 invalid → **failed**（无论其他字段是否捕获，样本进入 failures.jsonl）；
  2. 否则全部声明字段 captured 且无 invalid → **success**；
  3. 否则（存在非 required 字段 missing 或 invalid）→ **partial**；
  4. 无任何策略命中（零字段捕获）→ **failed**（reason=`no_match`）。
- 置信标记 `complete/partial/low` 只作为输出元数据列（success→complete、partial→partial、failed→low），不参与状态机。

**理由**：单一事实来源，避免状态漂移；required 失败即整条失败符合业务直觉；置信降级为展示层。

**影响**：output/metadata 只读映射置信；failures.jsonl 只收 failed 记录；工作台 diff 按字段级三态展示。

## ADR-002 正则超时语义

**背景**：正则灾难性回溯是稳定性首要风险，需要明确的超时行为与可观测性。

**结论**：
- 单次匹配超时（`regex` 库 `timeout`，默认 0.1s，全局可配）→ 该次匹配视为**未命中**：first_match 继续尝试下一策略、fallback 同、all_match 直接失败；
- 若整条记录最终未采用任何策略且期间发生过超时 → 记录 failed，reason=`regex_timeout`（优先于 `no_match`）；样本进入 failures.jsonl；
- 超时计数在**任务汇总**中统计输出（按 reason 分组的失败计数，含 `regex_timeout`），benchmark 输出 `timeout_rate`。

**理由**：防灾难回溯是硬约束；失败必须可归因、可度量。

**影响**：workers 汇总结构增加 `failure_reasons: dict[str, int]`；bench 输出增加超时率。

## ADR-003 热加载与任务快照

**背景**：热加载（mtime 轮询）若直接影响在途批量任务，结果不可复现。

**结论**：
- 批量任务**启动时**对所用模板做不可变快照（deep copy 编译产物：结构复制；regex 对象本身不可变可共享）——快照点在 `BatchExecutor` 构造/启动处调用 `TemplateLibrary.snapshot(refs)`；
- 运行期间热加载只更新模板库活跃引用，**不影响在途任务**；新任务启动时取最新版；
- 热加载失败的模板保留上一可用版本并告警（D8）。

**理由**：在途结果可复现；模板文件在任务运行中可被编辑而不破坏一致性。

**影响**：Runner 只持有快照引用；loader 维护 `versioned` 结构（活跃版 + 上一可用版）。

## ADR-004 去重作用域

**背景**：去重集合若全局常驻内存，大任务内存不可控，且与断点续跑相互干扰。

**结论**：
- `dedup_keys` 默认**单文件内去重**（每文件独立 seen 集合）；
- 跨文件全局去重需 `global_dedup: true`（模板 options 或 CLI `--global-dedup`）：已见 key 集合持久化到 checkpoint 文件，**与文件级 checkpoint 同步提交**——仅"已完成文件"的 keys 落盘，进行中文件的 keys 只在内存；
- 断点续跑：跳过已完成文件（其记录已留在输出中，不会重复处理）；未完成文件重跑时其 keys 未持久化 → **不会误判重复**；
- resume 依赖输出文件与 checkpoint 配对：删除其一则需全量重建；
- 超大规模（>100 万 key）给告警。

**理由**：默认内存可控；全局去重只有持久化才能与断点续跑自洽。

**影响**：checkpoint 文件结构含 `completed_files` 与 `seen_keys`；dedup 状态按文件粒度提交。

## ADR-005 fallback 策略语义

**背景**：fallback 何时换策略、校验失败是否触发换策略，需明确。

**结论**：
- **命中** = 正则匹配成功；**采用** = 命中且该策略覆盖的 required 字段全部 captured；
- 字段级 pattern/length/enum/range 校验失败**不触发换策略**（属 invalid，按 ADR-001 影响记录状态）；
- 仅 required 字段 **missing** 才继续尝试下一策略；
- 所有策略耗尽 → failed（reason=`no_match` / `regex_timeout`）；
- 边界：required 字段 captured 但 invalid（如类型转换失败）→ 该记录 failed，**不换策略**。

**理由**：fallback 定位为"格式变体兜底"，解决的是"字段没抓到"，而非"值不合法"。

**影响**：matcher 只依赖"字段是否 captured + required 标记"做策略选择，不依赖 validate 结果；validate 结果由记录模型统一推导。
