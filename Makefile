SHELL := /bin/bash

REPO ?=
PROFILE ?=

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_-]+:.*##/ {printf "%-28s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: test

test: ## Run pytest suite
	pytest tests/

.PHONY: lint
lint: ## Run ruff lint
	ruff check .

.PHONY: format
format: ## Run ruff formatter
	ruff format .

.PHONY: typecheck
typecheck: ## Run mypy on core code
	mypy cihub/ scripts/

.PHONY: validate-config
validate-config: ## Validate a repo config (REPO required)
	@[ -n "$(REPO)" ] || (echo "REPO is required. Example: make validate-config REPO=fixtures-java-passing" && exit 2)
	python scripts/validate_config.py config/repos/$(REPO).yaml

.PHONY: load-config
load-config: ## Load merged config for a repo (REPO required)
	@[ -n "$(REPO)" ] || (echo "REPO is required. Example: make load-config REPO=fixtures-java-passing" && exit 2)
	python scripts/load_config.py $(REPO)

.PHONY: apply-profile
apply-profile: ## Apply profile to a repo config (REPO, PROFILE required)
	@[ -n "$(REPO)" ] || (echo "REPO is required. Example: make apply-profile REPO=my-repo PROFILE=python-fast" && exit 2)
	@[ -n "$(PROFILE)" ] || (echo "PROFILE is required. Example: make apply-profile REPO=my-repo PROFILE=python-fast" && exit 2)
	python scripts/apply_profile.py templates/profiles/$(PROFILE).yaml config/repos/$(REPO).yaml

.PHONY: actionlint
actionlint: ## Validate workflows (requires actionlint installed)
	actionlint .github/workflows/*.yml

.PHONY: preflight
preflight: ## Check environment readiness
	python -m cihub preflight

.PHONY: docs-check
docs-check: ## Check docs drift against code
	python -m cihub docs check

.PHONY: links
links: ## Check docs for broken internal links
	python -m cihub docs links

.PHONY: smoke
smoke: ## Run smoke test on a scaffolded repo
	python -m cihub smoke --full $$(mktemp -d)/smoke-test

.PHONY: check
check: ## Run all checks (pre-push)
	python -m cihub check

.PHONY: sync-templates-check
sync-templates-check: ## Check caller/template drift
	python -m cihub sync-templates --check

.PHONY: sync-templates-repo
sync-templates-repo: ## Sync caller/template for a repo (REPO required)
	@[ -n "$(REPO)" ] || (echo "REPO is required. Example: make sync-templates-repo REPO=owner/name" && exit 2)
	python -m cihub sync-templates --repo $(REPO)

.PHONY: hub-run
hub-run: ## Run hub-run-all with act (requires act installed)
	act -W .github/workflows/hub-run-all.yml

.PHONY: mutmut
mutmut: ## Run mutation testing (requires mutmut)
	mutmut run

.PHONY: aggregate-reports
aggregate-reports: ## Build dashboard.html from reports
	python scripts/aggregate_reports.py --output dashboard.html
