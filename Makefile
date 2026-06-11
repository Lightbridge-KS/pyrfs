# pyrfs developer workflow — run `make` (or `make help`) to list targets.

.DEFAULT_GOAL := help
.PHONY: help sync lint format format-check typecheck test test-core docs docs-serve \
        readme readme-check build gate clean

UV := uv

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

sync: ## Install/refresh the full dev env (docs group + pandas extra)
	$(UV) sync --group docs --extra pandas

lint: ## Ruff lint
	$(UV) run ruff check

format: ## Ruff format (rewrites files)
	$(UV) run ruff format

format-check: ## Ruff format check (no rewrite)
	$(UV) run ruff format --check

typecheck: ## mypy --strict on the package
	$(UV) run mypy --strict pyrfs

test: ## pytest with the pandas extra
	$(UV) run --extra pandas pytest

test-core: ## pytest without pandas (prunes the venv first)
	$(UV) sync --exact
	$(UV) run --no-sync pytest

docs: ## Build the MkDocs site (strict; executes the tour notebook)
	$(UV) run --group docs --extra pandas mkdocs build --strict

docs-serve: ## Live-preview the docs site
	$(UV) run --group docs --extra pandas mkdocs serve

readme: ## Re-render README.md from README.qmd (Quarto)
	$(UV) run --group docs --extra pandas quarto render README.qmd

readme-check: readme ## Fail if README.md is stale w.r.t. README.qmd
	@git diff --exit-code README.md \
		|| { echo "ERROR: README.md is stale — run 'make readme' and commit it."; exit 1; }

build: ## Build sdist + wheel
	$(UV) build

gate: lint format-check typecheck test test-core docs readme-check ## Full gate suite (all checks)
	@echo "ALL GATES GREEN"

clean: ## Remove build artifacts and caches
	rm -rf site dist .ruff_cache .mypy_cache .pytest_cache
