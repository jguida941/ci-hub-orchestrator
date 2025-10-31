# Shared defaults for local automation

PYTHON ?= python3
PIP ?= pip3
MKDOCS ?= mkdocs
MARKDOWNLINT ?= npx --yes markdownlint-cli2@0.18.1

ARTIFACTS_DIR ?= artifacts
SBOM_DIR ?= $(ARTIFACTS_DIR)/sbom
POLICY_INPUTS_DIR ?= $(ARTIFACTS_DIR)/policy-inputs
EVIDENCE_DIR ?= $(ARTIFACTS_DIR)/evidence
MUTATION_DIR ?= $(ARTIFACTS_DIR)/mutation
CHAOS_DIR ?= $(ARTIFACTS_DIR)/chaos
DR_DIR ?= $(ARTIFACTS_DIR)/dr
