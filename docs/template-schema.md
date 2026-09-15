# rulefield 模板 YAML Schema 设计定稿（v0.1.0）

> 本文档定义模板文件的完整语法。模板是纯配置，**不改代码即可增删字段/策略**。

## 1. 文件组织与引用

```
templates/                  # 模板库根（可配置多个 template_dirs 叠加）
├── logs/                   # 分组目录（group）
│   └── nginx_access.yml    # 模板文件（文件名=模板名）
├── contracts/
│   ├── amount.yml
│   └── base/               # 仅存放可被 extends 的基础模板
└── invoices/
    └── order_receipt.yml
```

- 模板引用语法：`<group>/<name>`（如 `logs/nginx_access`）；直接写 `<name>` 时在全部分组中唯一解析。
- 文件名后缀 `.yml` / `.yaml` 均可。

## 2. 顶层结构总览

```yaml
name: nginx_access            # 必填，模板名（与文件名一致，全局唯一）
version: "1.2.0"              # 必填，semver 字符串
description: 抽取 Nginx access log 字段
enabled: true                 # 默认 true；false 时跳过加载（validate 仍可查）
extends: base/http_common     # 可选：继承基础模板（配置与字段合并）
mode: line                    # line | document | segment，默认 line
split:                        # 仅 segment 模式
  regex: '^={3,}$'            # 段落分隔正则
  keep_separator: false       # 分隔行是否并入下一段
options:
  flags: [DOTALL]             # 编译 flags：DOTALL|IGNORECASE|MULTILINE（可选）
  keep_extra: false           # 未声明命名组是否进 extra 列
  dedup_keys: [order_no]      # 模板级去重键（可选，默认单文件内去重）
  global_dedup: false         # true=跨文件全局去重，已见 key 集合持久化到 checkpoint（ADR-004）
  encoding_fallback: [utf-8, gb18030, latin-1]   # 模板级覆盖全局降级链

# ---- 匹配方式（三选一，见 §4）----
pattern:                      # 方式A/B：整篇/整行单模式
  regex: '...'                #   A：正则 + 命名捕获组 (?P<name>...)
  placeholder: '...'          #   B：占位符文本，含 {{name}} 槽位
patterns:                     # 方式C：字段级独立模式（document 常用）
  - field: party_a
    placeholder: '甲方：{{party_a}}'
  - field: amount
    regex: '金额(?P<amount>[\d,]+)元'

# ---- 多策略（可选，见 §4.4）----
strategies:
  mode: first_match            # first_match | all_match | fallback，默认 first_match
  items:
    - id: combined_with_time  # 策略 id，输出元数据可见
      pattern: {placeholder: '...'}
      fields: [a, b, c]       # 本策略覆盖的字段（槽位须与声明字段一一对应）
    - id: combined
      patterns: [...]

# ---- 字段定义 ----
fields:
  - name: remote_addr
    required: true
    # type / default / pipeline / validate 见 §5-7
```

**互斥约束（schema 校验）**：顶层 `pattern`/`patterns`（隐式单策略）与 `strategies.items` 只能二选一。

## 3. 顶层键说明

| 键 | 类型 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | str | ✅ | — | 模板名，全库唯一；与文件名一致 |
| `version` | str | ✅ | — | semver，如 `"1.2.0"` |
| `description` | str | 否 | "" | 人类可读说明 |
| `enabled` | bool | 否 | true | 停用模板不参与抽取（保留文件） |
| `extends` | str | 否 | — | 继承基础模板引用 |
| `mode` | enum | 否 | line | line / document / segment |
| `split` | map | 条件 | — | segment 模式必填 |
| `options` | map | 否 | {} | flags / keep_extra / dedup_keys / global_dedup / encoding_fallback |
| `pattern` | map | 条件 | — | 单策略整篇模式（regex 或 placeholder） |
| `patterns` | list | 条件 | — | 单策略字段级模式列表 |
| `strategies` | map | 条件 | — | 多策略（mode + items） |
| `fields` | list | ✅ | — | 字段定义，至少 1 个 |

## 4. 匹配方式

### 4.1 方式 A — 整段正则（`pattern.regex`）

标准正则，命名捕获组名即字段名：

```yaml
pattern:
  regex: '^(?P<remote_addr>\S+) - (?P<remote_user>\S+) \[(?P<time_local>[^\]]+)\]'
```

- 命名组必须与 `fields` 中声明字段一一对应；正则编译失败 → 模板加载失败（报行列）。

### 4.2 方式 B — 占位符（`pattern.placeholder`）

```
交易单号 {{order_no}}，金额 {{amount}} 元，时间 {{time}}
```

引擎自动转义字面量并生成捕获组：

```
交易单号 (?P<order_no>.+?)，金额 (?P<amount>.+?) 元，时间 (?P<time>.+?)
```

- 槽位默认正则 `.+?`（非贪婪、至少 1 字符），可用字段级 `slot_regex` 覆盖：
  `金额 {{amount}} 元` + `slot_regex: '[\d.]+'` → `金额 (?P<amount>[\d.]+) 元`。
- 占位符中的空白原样保留（转义后匹配）。
- 槽位名必须对应已声明字段；未知槽位 → 加载报错（列出来声明字段提示）。

### 4.3 方式 C — 字段级独立模式（`patterns`）

适合 document 模式（合同/单据，各字段散布全文）：

```yaml
patterns:
  - field: party_a
    placeholder: '甲方：{{party_a}}'
  - field: amount
    regex: '合同金额(?:为|：)?(?P<amount>[0-9,]+(?:\.\d{1,2})?)元'
  - field: sign_date
    regex: '(?P<sign_date>\d{4}年\d{1,2}月\d{1,2}日)'
```

### 4.4 多策略（`strategies`）

| mode | 语义（ADR-005） |
| --- | --- |
| `first_match`（默认） | 按 `items` 顺序，第一个**正则命中**的策略生效；随后对该策略的字段做 pipeline/validate，按记录模型推导状态（ADR-001） |
| `fallback` | 按顺序，第一个**正则命中且全部 required 字段 captured** 的策略被采用；字段级 pattern/length/enum/range 校验失败**不触发换策略**（属 invalid，ADR-001），仅 required 字段 **missing** 才继续尝试下一策略；全部耗尽 → failed（reason=`no_match`/`regex_timeout`） |
| `all_match` | 所有策略都必须正则命中，字段取并集；任一未命中 → failed |

> 术语：**命中** = 正则匹配成功；**采用** = 命中且该策略覆盖的 required 字段全部 captured。required 字段 captured 但 invalid（如类型转换失败）→ 按 ADR-001 该记录 failed，不换策略。

典型场景：Nginx 日志两种格式（带/不带 `request_time`）→ `first_match` 按优先级尝试。

```yaml
strategies:
  mode: first_match
  items:
    - id: with_request_time
      pattern: {placeholder: '{{remote_addr}} - {{remote_user}} [{{time_local}}] "{{request}}" {{status}} {{body_bytes_sent}} "{{http_referer}}" "{{http_user_agent}}" {{request_time}}'}
      fields: [remote_addr, remote_user, time_local, request, status, body_bytes_sent, http_referer, http_user_agent, request_time]
    - id: plain
      pattern: {placeholder: '{{remote_addr}} - {{remote_user}} [{{time_local}}] "{{request}}" {{status}} {{body_bytes_sent}} "{{http_referer}}" "{{http_user_agent}}"'}
      fields: [remote_addr, remote_user, time_local, request, status, body_bytes_sent, http_referer, http_user_agent]
```

约束：策略 `id` 全模板唯一；`fields` 列表中的字段必须已声明；槽位必须与声明字段匹配。

## 5. 字段定义（`fields[].`）

| 键 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `name` | str | — | ✅ 必填，模板内唯一 |
| `required` | bool | false | true 时该字段 missing/invalid → 整条记录 failed 并进 failures.jsonl（ADR-001） |
| `type` | enum | str | 简写类型转换：str/int/float/bool/date/datetime（等价于在 pipeline 末尾追加 `{op: type, to: …}`） |
| `default` | any | — | 空值/未捕获时填充（等价于追加 `{op: default, value: …}`） |
| `slot_regex` | str | `.+?` | 仅占位符槽位生效 |
| `pattern` | str | — | 字段级显式正则（含 `(?P<name>…)`）；方式 C 用 |
| `placeholder` | str | — | 字段级占位符文本；方式 C 用 |
| `pipeline` | list | [] | 后置处理链（§6） |
| `validate` | list | [] | 校验规则（§7） |

优先级说明：方式 B（整篇占位符）匹配时，字段捕获取自槽位；字段级 `pattern/placeholder` 仅在方式 C（`patterns`）中使用。

## 6. pipeline 操作（按声明顺序执行）

| op | 参数 | 说明 | 示例 |
| --- | --- | --- | --- |
| `trim` | — | 去除首尾空白 | `{op: trim}` |
| `type` | `to`（str/int/float/bool/date/datetime）；`format`（date/datetime 必填） | 类型转换；失败 → 字段 invalid | `{op: type, to: float}`、`{op: type, to: datetime, format: '%Y-%m-%d %H:%M:%S'}` |
| `regex_replace` | `pattern`、`repl` | 正则替换（默认 re 非 regex 库，替换无超时风险） | `{op: regex_replace, pattern: ',', repl: ''}` |
| `default` | `value` | 值为空/None 时填充 | `{op: default, value: 0}` |
| `unit` | `factor`；`from`/`to`（可选，仅说明标签） | 数值×factor 换算 | `{op: unit, factor: 100}`（元→分） |
| `upper` / `lower` | — | 大小写转换 | `{op: upper}` |

- `type` 简写规则：模板里写了 `type: float` 且 pipeline 中无显式 `{op: type}`，则在 pipeline 末尾自动追加类型转换。
- bool 解析：true/false/1/0/yes/no/on/off（大小写不敏感）。

## 7. 校验规则（`validate[].`）

| type | 参数 | 语义 | 失败影响（ADR-001） |
| --- | --- | --- | --- |
| `required` | — | 字段必须存在且有值 | 整条记录 failed（进 failures.jsonl） |
| `pattern` | `value` | 对**最终值**二次正则校验 | 字段 invalid；required 字段时整条 failed，否则记录 partial |
| `length` | `min`/`max` | 字符串长度范围 | 同上 |
| `enum` | `values` | 取值必须在枚举内 | 同上 |
| `range` | `min`/`max` | 数值范围（int/float 值） | 同上 |

- `required: true` 是 `validate: [{type: required}]` 的简写。
- 非 required 校验失败 → 字段 invalid、记录 partial；required 字段失败 → 整条 failed 并进入 failures.jsonl。

## 8. 处理模式（`mode`）

| mode | 单位 | 说明 |
| --- | --- | --- |
| `line` | 一行 | 每行独立匹配（日志）；流式逐块读取，>1GB 无压力 |
| `document` | 整篇 | 全文一次匹配（合同/单据）；文本需整体驻留内存 |
| `segment` | 一个切块 | 按 `split.regex` 切段后逐段匹配；切分正则跨块边界由引擎处理 |

## 9. 继承与复用（`extends` / field_sets）

### 9.1 `extends` — 整模板继承

```yaml
# templates/base/http_common.yml  （enabled: false 的“纯基础模板”推荐用法）
name: http_common
version: "1.0.0"
enabled: false
field_sets:
  ipv4: &ipv4
    name: remote_addr
    required: true
    validate: [{type: pattern, value: '^\d{1,3}(\.\d{1,3}){3}$'}]
fields:
  - <<: *ipv4
```

```yaml
# templates/logs/nginx_access.yml
extends: base/http_common
fields:
  - name: remote_addr   # 同名覆盖基模板定义
    required: true
  - name: status
    type: int
```

合并规则：

| 项 | 规则 |
| --- | --- |
| 标量配置（mode/version/options…） | 子模板覆盖 |
| `fields` | 按 `name` 合并，子覆盖父；顺序：父模板字段在前，新增字段在后 |
| `strategies.items` | 按 `id` 合并，子覆盖父 |
| `field_sets` | 不继承（仅自身使用） |

### 9.2 field_sets — 公共字段组复用

```yaml
# 任意模板内
field_sets:
  money:
    - name: amount
      type: float
      pipeline: [{op: regex_replace, pattern: ',', repl: ''}]
    - name: currency
      enum: [人民币, 美元, 欧元]
      default: 人民币
# 另一模板
use_sets: [money]        # 展开为字段定义（按 name 与自身 fields 去重，自身优先）
fields:
  - name: order_no
    required: true
```

## 10. 版本与启用

- `version`：semver 字符串；抽取结果元数据携带 `template` 名与 `template_version`，保证结果可溯源。
- `enabled: false`：跳过加载（不参与抽取与热加载刷新）；`validate --all` 仍可检查其语法。

## 11. Schema 校验与错误格式

- 校验范围：必填键、类型、枚举值、互斥项（pattern vs patterns vs strategies）、重复 name/策略 id、未知 op/校验类型、字段级正则含命名组、占位符槽位与字段一致性、`extends` 引用存在性、版本号格式。
- 错误输出格式（PyYAML 节点 mark 定位）：

```
模板文件 templates/logs/nginx.yml:14:7 — 字段 status 的校验规则 validate[0] 类型未知: 'rangee'（可选: required|pattern|length|enum|range）
模板文件 templates/logs/nginx.yml:22:5 — 占位符槽位 '{{time_loca}}' 未匹配任何已声明字段（已声明: remote_addr, time_local, ...）
```

- 加载隔离：任一模板非法 → 拒绝加载该模板（保留上一可用版本），其余模板不受影响；进程不中断。

## 12. 内置示例模板（Phase 4 落地）

1. `logs/nginx_access.yml` — 行模式 + first_match 双策略（带/不带 request_time）。
2. `contracts/amount.yml` — document 模式 + 字段级 patterns（甲方/乙方/金额/币种）。
3. `invoices/order_receipt.yml` — segment 模式 + 占位符 + 类型转换（单号/金额/时间/商品）。

对应示例数据与 `examples/` 目录在 Phase 4 交付。
