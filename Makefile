PYTHON ?= python3
PIP ?= pip3

.PHONY: install dev-install lint format test bench accept clean

install: ## 生产安装（pipx 场景）
	$(PIP) install .

dev-install: ## 开发安装（含 dev 依赖，可编辑）
	$(PIP) install -e ".[dev]"

lint: ## ruff 检查（零告警门禁）
	ruff check rulefield tests

format: ## ruff 格式化并自动修复
	ruff format rulefield tests
	ruff check --fix rulefield tests

test: ## 全量测试（无网络依赖）
	pytest

bench: ## 性能基准（benchmark 命令随 Phase 6 交付）
	rulefield benchmark

accept: ## 验收标准自测（Phase 7）
	pytest -m accept

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
