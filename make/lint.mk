.PHONY: lint lint-markdown security-lint dbt
lint: lint-markdown security-lint ## Run the full lint suite

lint-markdown: ## Lint Markdown files with markdownlint
	$(MARKDOWNLINT) "**/*.md"

security-lint: ## Run security static analysis (Ruff S, Bandit, pip-audit, workflow guard)
	$(PYTHON) -m ruff check --select S .
	$(PYTHON) -m bandit -q -r tools scripts
	PIP_AUDIT_PROGRESS_BAR=off $(PYTHON) -m pip_audit -r requirements-dev.txt -r requirements-dev.lock
	$(PYTHON) scripts/check_workflow_integrity.py

dbt: ## Run dbt build with repo defaults
	$(PYTHON) scripts/run_dbt.py build
