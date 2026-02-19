E2E_DIR := ./e2e
E2E_VENV := $(E2E_DIR)/.venv

.PHONY: e2e-venv

e2e-venv:
	cd $(E2E_DIR) && uv venv .venv
	cd $(E2E_DIR) && uv sync --frozen
