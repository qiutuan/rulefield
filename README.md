# rulefield — 轻量规则化文本字段抽取引擎

> 从日志、合同、接口返回、固定格式单据等非结构化文本中，按**可配置模板**批量抽取固定字段并导出结构化结果。
> 纯规则驱动：**不引入 RAG / 向量检索 / Embedding / LLM**，零外部服务依赖，可离线运行。

## 状态

- **当前阶段：设计定稿（v0.1.0-dev）**，等待用户确认后进入逐阶段编码。
- 路线图：见 [docs/implementation-plan.md](docs/implementation-plan.md)
- 架构设计：见 [docs/architecture.md](docs/architecture.md)
- 模板语法：见 [docs/template-schema.md](docs/template-schema.md)

## 目标指标

| 指标 | 目标 |
| --- | --- |
| 常驻内存 | < 100MB（常规任务）；100MB 大文件流式峰值 < 200MB |
| 吞吐 | 单核 CPU 10 万行/分钟量级（行模式） |
| 单文件基线 | 10MB 日志行模式抽取 < 10s（单机单核参考值） |
| 依赖 | 零外部服务、零数据库、可离线运行 |

## 快速开始（占位，完整版随 v0.1.0 交付）

```bash
pip install -e .            # 或 pipx install .
rulefield list              # 查看内置模板库
rulefield extract --template nginx_access --input ./examples/data/nginx.log --format csv
```

## 开发命令

```bash
make install     # 开发安装
make test        # 运行全部测试（pytest + coverage）
make lint        # ruff + black 检查
make bench       # 性能基准
```

## 项目结构（规划）

```
rulefield/
├── cli/          # Typer 命令行（extract/test/validate/benchmark/list/diff）
├── template/     # 模板引擎：schema/loader/compiler/pipeline/validation/matcher
├── executor/     # 批量执行：inputs/encoding/workers/checkpoint/dedup
├── output/       # 输出：CSV(BOM)/Markdown/JSONL + failures.jsonl
├── workbench/    # 测试工作台：preview/regression/diff
├── bench/        # 性能基准
├── lint/         # 正则复杂度静态检查
├── config.py     # 全局配置
└── utils/        # 日志/原子写/计时
```
