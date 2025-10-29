.PHONY: determinism determinism-clean

DETERMINISM_IMAGE ?=
DETERMINISM_DIR ?= artifacts/determinism

determinism: ## Run determinism check against an OCI image (set DETERMINISM_IMAGE)
	@test -n "$(DETERMINISM_IMAGE)" || { echo "Set DETERMINISM_IMAGE to the image digest (e.g. ghcr.io/org/app@sha256:...)"; exit 1; }
	mkdir -p "$(DETERMINISM_DIR)"
	tools/determinism_check.sh "$(DETERMINISM_IMAGE)" "$(DETERMINISM_DIR)"

determinism-clean: ## Remove determinism artifacts
	rm -rf "$(DETERMINISM_DIR)"
