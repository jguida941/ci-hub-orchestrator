DR_REPORT ?= $(DR_DIR)/dr-report.json
DR_EVENTS ?= $(DR_DIR)/dr-events.ndjson
DR_MANIFEST ?= data/dr/manifest.json
DR_CURRENT_TIME ?= 2025-01-16T00:00:00Z

.PHONY: run-dr clean-dr
run-dr: ## Run the DR drill simulator
	mkdir -p "$(DR_DIR)"
	$(PYTHON) -m tools.run_dr_drill \
		--manifest "$(DR_MANIFEST)" \
		--output "$(DR_REPORT)" \
		--ndjson "$(DR_EVENTS)" \
		--current-time "$(DR_CURRENT_TIME)"

clean-dr: ## Remove DR drill artifacts
	rm -rf "$(DR_DIR)"
