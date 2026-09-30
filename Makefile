.DEFAULT_GOAL := help

VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

.PHONY: help venv test lint lint-fix typecheck pre-commit registries clean clean-all

help: ## Show this help
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Create .venv (if missing), install dev deps, and install the pre-commit hooks
	@test -d $(VENV_DIR) || python3 -m venv $(VENV_DIR)
	$(PIP) install -r requirements-dev.txt
	$(VENV_DIR)/bin/pre-commit install

test: ## Run the pytest suite (override with TEST=path/to/test_file.py)
	$(PYTHON) -m pytest $(TEST)

lint: ## Run ruff over src/, scripts/, and tests/
	$(VENV_DIR)/bin/ruff check src scripts tests

lint-fix: ## Run ruff over src/, scripts/, and tests/, auto-applying safe fixes
	$(VENV_DIR)/bin/ruff check --fix src scripts tests

typecheck: ## Run mypy over src/
	$(VENV_DIR)/bin/mypy src

pre-commit: ## Run all pre-commit hooks against every file
	$(VENV_DIR)/bin/pre-commit run --all-files

registries: ## Regenerate SCRIPTS.md and the code registry (see scripts/dev/)
	$(PYTHON) scripts/dev/generate_scripts_registry.py
	$(PYTHON) scripts/dev/generate_code_registry.py

clean: ## Remove local caches and pyc files
	find . -type d -name '__pycache__' -not -path './$(VENV_DIR)/*' -exec rm -rf {} +
	find . -type f -name '*.pyc' -not -path './$(VENV_DIR)/*' -exec rm -f {} +
	rm -rf .pytest_cache

clean-all: clean ## clean + remove the .venv
	rm -rf $(VENV_DIR)
