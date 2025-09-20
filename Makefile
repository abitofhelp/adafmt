# Makefile for adafmt development
# Run 'make help' for available targets

# Use bash with pipefail for safer scripting
SHELL := /bin/bash -eo pipefail

# Configuration
VENV ?= .venv
PYTHON ?= python3
# Prefer the project venv if present
PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || (command -v python3 || command -v python))
PIP := $(PY) -m pip
SEMREL := $(PY) -m semantic_release
ADAFMT ?= $(VENV)/bin/adafmt

# Project paths
SRC_DIR := src/adafmt
TEST_DIR := tests
TOOLS_DIR := tools
DOCS_DIR := docs
SCRIPTS_DIR := scripts

# Default target
.DEFAULT_GOAL := help

# Help target - must be first
.PHONY: help
help:
	@echo "adafmt Development Makefile"
	@echo ""
	@echo "Virtual environment activation:"
	@echo "  source .venv/bin/activate  - Activate the virtual environment"
	@echo "  deactivate                 - Deactivate the virtual environment"
	@echo ""
	@echo "Setup targets:"
	@echo "  make install     - Create venv and install adafmt in editable mode"
	@echo "  make dev         - Install with all development dependencies"
	@echo ""
	@echo "Testing targets:"
	@echo "  make test        - Run unit tests (fast, no ALS required)"
	@echo "  make test-integration - Run integration tests (requires ALS)"
	@echo "  make test-all    - Run all tests"
	@echo "  make test-v      - Run tests with verbose output"
	@echo "  make coverage    - Run tests with coverage report"
	@echo ""
	@echo "Code quality targets:"
	@echo "  make lint        - Run code quality checks with ruff"
	@echo "  make format      - Format Python code with black"
	@echo "  make typecheck   - Run type checking with mypy"
	@echo ""
	@echo "Ada formatting targets:"
	@echo "  make ada-format  - Format Ada source and test files (dry-run)"
	@echo "  make ada-write   - Format and write Ada files"
	@echo "  make ada-check   - Check if Ada files need formatting"
	@echo ""
	@echo "Build targets:"
	@echo "  make build       - Build distribution packages (wheel and sdist)"
	@echo "  make check-build - Verify the build is installable"
	@echo ""
	@echo "Distribution targets:"
	@echo "  make dist-exe    - Create standalone executable with PyInstaller"
	@echo "  make dist-zipapp - Create Python zipapp executable"
	@echo ""
	@echo "Documentation targets:"
	@echo "  make docs        - Check documentation files exist"
	@echo "  make docs-bump-headers - Update doc headers with next semantic version"
	@echo "  make docs-bump-headers-dry-run - Preview header updates (dry-run)"
	@echo "  make print-next-version - Show next semantic release version"
	@echo ""
	@echo "Utility targets:"
	@echo "  make check       - Quick sanity check of installation"
	@echo "  make tools       - List development tools"
	@echo "  make clean       - Remove build artifacts and caches"
	@echo "  make distclean   - Remove venv, build artifacts, and caches"
	@echo "  make kill-als    - Kill all ALS processes and clean stale locks (aggressive)"

# Create virtual environment
.PHONY: venv
venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
		$(PIP) install --upgrade pip setuptools wheel; \
	else \
		echo "Virtual environment already exists at $(VENV)"; \
	fi

# Install package in editable mode
.PHONY: install
install: venv
	@echo "Installing adafmt in editable mode..."
	$(PIP) install -e .
	@echo ""
	@echo "✓ adafmt installed at: $(ADAFMT)"
	@echo "✓ Test with: $(ADAFMT) --version"
	@echo ""
	@echo "To use adafmt from the command line:"
	@echo "  source $(VENV)/bin/activate"
	@echo "  adafmt --help"

# Install with development dependencies
.PHONY: dev
dev: install
	@echo "Using Python: $(PY)"
	@$(PIP) install -U pip >/dev/null
	@if [ -f requirements-dev.txt ]; then \
		echo "Installing dev deps from requirements-dev.txt..."; \
		$(PIP) install -r requirements-dev.txt; \
	else \
		echo "Installing development dependencies from pyproject.toml..."; \
		$(PIP) install -e ".[dev]"; \
		echo "Installing python-semantic-release..."; \
		$(PIP) install "python-semantic-release>=9,<10"; \
	fi
	@echo "✓ Development environment ready"
	@echo ""
	@echo "Activate the virtual environment with:"
	@echo "  source $(VENV)/bin/activate"

# Run tests
.PHONY: test
test: install
	@echo "Running tests..."
	@if [ ! -f "$(VENV)/bin/pytest" ]; then \
		echo "Installing pytest..."; \
		$(PIP) install -e ".[test]"; \
	fi
	$(PY) -m pytest -q -m "not integration"

# Run integration tests (requires ALS)
.PHONY: test-integration
test-integration: install
	@echo "Running integration tests (requires ALS)..."
	@if [ ! -f "$(VENV)/bin/pytest" ]; then \
		$(PIP) install -e ".[test]"; \
	fi
	@if ! command -v ada_language_server >/dev/null 2>&1; then \
		echo "Warning: ALS not found, some tests will be skipped"; \
	fi
	$(PY) -m pytest -q -m integration

# Run all tests
.PHONY: test-all
test-all: install
	@echo "Running all tests..."
	@if [ ! -f "$(VENV)/bin/pytest" ]; then \
		$(PIP) install -e ".[test]"; \
	fi
	$(PY) -m pytest -q

# Run tests with verbose output
.PHONY: test-v
test-v: install
	@if [ ! -f "$(VENV)/bin/pytest" ]; then \
		$(PIP) install -e ".[test]"; \
	fi
	$(PY) -m pytest -vv

# Run only failing tests
.PHONY: test-failed
test-failed: install
	@if [ ! -f "$(VENV)/bin/pytest" ]; then \
		$(PIP) install -e ".[test]"; \
	fi
	$(PY) -m pytest --lf -vv

# Run tests with coverage
.PHONY: coverage
coverage: install
	@echo "Running tests with coverage..."
	@if [ ! -f "$(VENV)/bin/pytest" ]; then \
		$(PIP) install -e ".[dev]"; \
	fi
	$(PY) -m pytest --cov=adafmt --cov-report=term-missing --cov-report=html
	@echo "✓ Coverage report saved to htmlcov/index.html"

# Format code with black
.PHONY: format
format: venv
	@if [ -f "$(VENV)/bin/black" ]; then \
		echo "Formatting code with black..."; \
		$(VENV)/bin/black $(SRC_DIR) $(TEST_DIR) $(TOOLS_DIR); \
	else \
		echo "black not installed. Run 'make dev' first."; \
		exit 1; \
	fi

# Type checking
.PHONY: typecheck
typecheck: venv
	@if [ -f "$(VENV)/bin/mypy" ]; then \
		echo "Running type checks..."; \
		$(VENV)/bin/mypy $(SRC_DIR) --ignore-missing-imports; \
	else \
		echo "mypy not installed. Run 'make dev' first."; \
		exit 1; \
	fi

# Lint code
.PHONY: lint
lint: venv
	@if [ -f "$(VENV)/bin/ruff" ]; then \
		echo "Running ruff linter..."; \
		$(VENV)/bin/ruff check $(SRC_DIR) $(TEST_DIR); \
	else \
		echo "ruff not installed. Run 'make dev' first."; \
		exit 1; \
	fi

# === Ada Formatting Targets ===
# Note: These targets require a project.gpr file to be present
# adafmt now creates timestamped log files by default:
#   - ./adafmt_YYYYMMDD_HHMMSS_log.jsonl (main log)
#   - ./adafmt_YYYYMMDD_HHMMSS_stderr.log (stderr capture)

# Format Ada files (dry-run mode)
.PHONY: ada-format
ada-format: install
	@echo "Formatting Ada files (dry-run)..."
	$(ADAFMT) --project-path project.gpr \
		--include-path src \
		--include-path tests \
		--exclude-path tests/fixtures \
		--exclude-path tests/golden \
		--exclude-path tests/snapshots \
		--ui auto

# Format and write Ada files
.PHONY: ada-write
ada-write: install
	@echo "Formatting Ada files (write mode)..."
	$(ADAFMT) --project-path project.gpr \
		--include-path src \
		--include-path tests \
		--exclude-path tests/fixtures \
		--exclude-path tests/golden \
		--exclude-path tests/snapshots \
		--ui auto \
		--write

# Check if Ada files need formatting
.PHONY: ada-check
ada-check: install
	@echo "Checking if Ada files need formatting..."
	$(ADAFMT) --project-path project.gpr \
		--include-path src \
		--include-path tests \
		--exclude-path tests/fixtures \
		--exclude-path tests/golden \
		--exclude-path tests/snapshots \
		--ui plain \
		--check || \
	(echo ""; echo "Some Ada files need formatting. Run 'make ada-write' to fix."; exit 1)


# Build distribution packages
.PHONY: build
build: install
	@echo "Building distribution packages..."
	@if [ ! -f "$(VENV)/bin/pyproject-build" ]; then \
		echo "Installing build tool..."; \
		$(PIP) install build; \
	fi
	$(PY) -m build
	@echo ""
	@echo "✓ Packages built in dist/"

# Check that the built package is installable
.PHONY: check-build
check-build: build
	@echo "Checking build..."
	@rm -rf test_install_venv
	@$(PYTHON) -m venv test_install_venv
	@test_install_venv/bin/pip install dist/*.whl
	@test_install_venv/bin/adafmt --version
	@rm -rf test_install_venv
	@echo "✓ Build is installable"

# Test development tools
.PHONY: tools
tools: install
	@echo "Testing development tools..."
	@echo "Available tools:"
	@ls -1 $(TOOLS_DIR)/*.py
	@echo ""
	@echo "Run individual tools with:"
	@echo "  $(PY) $(TOOLS_DIR)/als_rpc_probe.py --help"
	@echo "  $(PY) $(TOOLS_DIR)/als_rpc_probe_stdio.py --help"
	@echo "  $(PY) $(TOOLS_DIR)/harness_mocked.py"

# Check documentation
.PHONY: docs
docs:
	@echo "Checking documentation files..."
	@for doc in README.md $(DOCS_DIR)/SRS.md $(DOCS_DIR)/SDD.md $(DOCS_DIR)/DEVELOPER_GUIDE.md; do \
		if [ -f "$$doc" ]; then \
			echo "✓ $$doc exists"; \
		else \
			echo "✗ $$doc missing"; \
		fi \
	done

# === Semantic Release Documentation Targets ===

## Compute the next version and update doc headers (writes in-place; makes backups per script).
.PHONY: docs-bump-headers
docs-bump-headers: dev
	@echo "Computing next version via python-semantic-release..."
	@nv="$( $(SEMREL) version --noop --print )"; \
	 if [ -z "$$nv" ]; then \
	   echo "ERROR: Could not compute next version (semantic-release)."; exit 2; \
	 fi; \
	 echo "Next version: $$nv"; \
	 SEMVER_NEXT="$$nv" $(PY) scripts/update_doc_headers.py --write

## Dry-run: show what would change without writing files.
.PHONY: docs-bump-headers-dry-run
docs-bump-headers-dry-run: dev
	@echo "Computing next version via python-semantic-release..."
	@nv="$( $(SEMREL) version --noop --print )"; \
	 if [ -z "$$nv" ]; then \
	   echo "ERROR: Could not compute next version (semantic-release)."; exit 2; \
	 fi; \
	 echo "Next version: $$nv"; \
	 SEMVER_NEXT="$$nv" $(PY) scripts/update_doc_headers.py

## Print the next version as detected by python-semantic-release.
.PHONY: print-next-version
print-next-version: dev
	@$(SEMREL) version --noop --print

# Clean build artifacts but keep venv
.PHONY: clean
clean:
	@echo "Cleaning build artifacts..."
	rm -rf dist/ build/ *.egg-info .pytest_cache htmlcov/ .coverage
	rm -rf dist-exe build-exe dist-zipapp build-zipapp
	rm -rf src/*.egg-info  # Clean egg-info from src directory
	rm -f *.log *.jsonl    # Clean log files from root
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "✓ Build artifacts removed"

# Clean everything including venv
.PHONY: distclean
distclean: clean
	@echo "Removing virtual environment..."
	rm -rf $(VENV)
	@echo "✓ Virtual environment removed"

# Quick sanity check
.PHONY: check
check: install
	@echo "Running sanity checks..."
	@echo -n "Python version: "
	@$(PY) --version
	@echo -n "adafmt version: "
	@$(PY) -c "import adafmt; print(adafmt.__version__)"
	@echo -n "Package location: "
	@$(PY) -c "import adafmt; print(adafmt.__file__)"
	@echo "✓ Basic checks passed"

# Development shortcuts
.PHONY: all
all: dev test

.PHONY: ci
ci: install test lint ada-check

# Ensure git is clean before release
.PHONY: check-git
check-git:
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: Git working directory is not clean"; \
		exit 1; \
	fi

# Kill all ALS processes and clean stale locks (aggressive mode)
.PHONY: kill-als
kill-als:
	@echo "Killing all ALS processes and cleaning stale locks..."
	@$(PY) $(SCRIPTS_DIR)/kill_als.py
	@echo "✓ ALS cleanup completed"

# === Distribution Targets ===

# Create standalone executable with PyInstaller
.PHONY: dist-exe
dist-exe: install
	@echo "Creating standalone executable with PyInstaller..."
	@if [ ! -f "$(VENV)/bin/pyinstaller" ]; then \
		echo "Installing PyInstaller..."; \
		$(PIP) install pyinstaller; \
	fi
	@echo "Building executable..."
	$(VENV)/bin/pyinstaller \
		--onefile \
		--name adafmt \
		--distpath dist-exe \
		--workpath build-exe \
		--clean \
		--noconfirm \
		--hidden-import adafmt \
		--hidden-import adafmt.cli \
		--hidden-import adafmt.als_client \
		--hidden-import adafmt.tui \
		--hidden-import adafmt.utils \
		--hidden-import adafmt.file_discovery \
		--hidden-import adafmt.logging_jsonl \
		--hidden-import adafmt.edits \
		src/adafmt/__main__.py
	@echo ""
	@echo "✓ Executable created: dist-exe/adafmt"
	@echo "✓ Test with: ./dist-exe/adafmt --help"

# Create Python zipapp (portable, requires Python on target)
.PHONY: dist-zipapp
dist-zipapp: install
	@echo "Creating Python zipapp..."
	@rm -rf build-zipapp dist-zipapp
	@mkdir -p build-zipapp dist-zipapp
	# Copy package to build directory
	@cp -r $(SRC_DIR) build-zipapp/
	# Create __main__.py for zipapp entry point
	@echo "from adafmt.cli import main" > build-zipapp/__main__.py
	@echo "if __name__ == '__main__': main()" >> build-zipapp/__main__.py
	# Create zipapp
	$(PY) -m zipapp build-zipapp \
		--output dist-zipapp/adafmt.pyz \
		--python "/usr/bin/env python3"
	@chmod +x dist-zipapp/adafmt.pyz
	@rm -rf build-zipapp
	@echo ""
	@echo "✓ Zipapp created: dist-zipapp/adafmt.pyz"
	@echo "✓ Run with: python3 dist-zipapp/adafmt.pyz --help"
	@echo "✓ Or directly: ./dist-zipapp/adafmt.pyz --help"


# Create all distribution formats
.PHONY: dist-all
dist-all: build dist-zipapp
	@echo ""
	@echo "✓ All distribution formats created:"
	@echo "  - PyPI packages in dist/"
	@echo "  - Zipapp in dist-zipapp/"
	@echo ""
	@echo "Note: Run 'make dist-exe' separately for standalone executable (large)"

# Clean distribution artifacts
.PHONY: dist-clean
dist-clean:
	@echo "Cleaning distribution artifacts..."
	rm -rf dist-exe build-exe dist-zipapp build-zipapp
	@echo "✓ Distribution artifacts removed"

# ---- Release-body bundle for Claude (adafmt specifics) ---------------------
# Usage:
#   make release-body            # prints bundle to stdout
#   make release-body-file       # writes bundle to ./.tmp/release_body_bundle.txt
#   make release-body | pbcopy   # macOS: copy to clipboard

.PHONY: release-body release-body-file _release-body-build

BUNDLE_DIR := .tmp
BUNDLE_FILE := $(BUNDLE_DIR)/release_body_bundle.txt

release-body: _release-body-build
	@cat $(BUNDLE_FILE)

release-body-file: _release-body-build
	@echo "Wrote $(BUNDLE_FILE)"

_release-body-build:
	@mkdir -p $(BUNDLE_DIR)
	@{ \
	  set -e; \
	  NOW="$$(date -u +"%Y-%m-%d %H:%M:%S UTC")"; \
	  LAST_TAG="$$(git describe --tags --abbrev=0 2>/dev/null || true)"; \
	  if [ -z "$$LAST_TAG" ]; then RANGE_DESC="(no previous tag; using full history)"; GIT_RANGE=""; else RANGE_DESC="(since $$LAST_TAG)"; GIT_RANGE="$$LAST_TAG..HEAD"; fi; \
	  echo "### Refresh Pack for Claude — adafmt" > $(BUNDLE_FILE); \
	  echo "_Generated: $$NOW_" >> $(BUNDLE_FILE); \
	  echo >> $(BUNDLE_FILE); \
	  echo "#### How to use" >> $(BUNDLE_FILE); \
	  echo "Paste into Claude. Return only the **commit body** (overview + bullets) and, if needed, a \`BREAKING CHANGE:\` footer. Do **not** include the subject line." >> $(BUNDLE_FILE); \
	  echo >> $(BUNDLE_FILE); \
	  echo "---" >> $(BUNDLE_FILE); \
	  echo "#### CLI help (adafmt --help)" >> $(BUNDLE_FILE); \
	  ( $(PY) -m adafmt --help 2>/dev/null || $(PY) -m adafmt.cli --help 2>/dev/null || $(ADAFMT) --help 2>/dev/null || echo "[WARN] Unable to capture CLI help." ) >> $(BUNDLE_FILE); \
	  echo >> $(BUNDLE_FILE); \
	  echo "#### CLI version (adafmt --version)" >> $(BUNDLE_FILE); \
	  ( $(PY) -m adafmt --version 2>/dev/null || $(PY) -m adafmt.cli --version 2>/dev/null || $(ADAFMT) --version 2>/dev/null || echo "[WARN] Unable to capture CLI version." ) >> $(BUNDLE_FILE); \
	  echo >> $(BUNDLE_FILE); \
	  echo "#### Recent commits $$RANGE_DESC" >> $(BUNDLE_FILE); \
	  if [ -z "$$GIT_RANGE" ]; then git log --pretty=format:"%h %ad %s" --date=short -n 200 >> $(BUNDLE_FILE) || true; \
	  else git log --pretty=format:"%h %ad %s" --date=short $$GIT_RANGE >> $(BUNDLE_FILE) || true; fi; \
	  echo >> $(BUNDLE_FILE); \
	  echo "#### Diff stat $$RANGE_DESC" >> $(BUNDLE_FILE); \
	  if [ -z "$$GIT_RANGE" ]; then git diff --stat HEAD~50..HEAD 2>/dev/null >> $(BUNDLE_FILE) || true; \
	  else git diff --stat $$GIT_RANGE 2>/dev/null >> $(BUNDLE_FILE) || true; fi; \
	  echo >> $(BUNDLE_FILE); \
	  echo "#### README & docs deltas $$RANGE_DESC" >> $(BUNDLE_FILE); \
	  if [ -z "$$GIT_RANGE" ]; then (git diff HEAD~50..HEAD -- README.md docs/ 2>/dev/null || true) >> $(BUNDLE_FILE); \
	  else (git diff $$GIT_RANGE -- README.md docs/ 2>/dev/null || true) >> $(BUNDLE_FILE); fi; \
	  echo >> $(BUNDLE_FILE); \
	  echo "#### Constraints / operational notes (adafmt specifics)" >> $(BUNDLE_FILE); \
	  echo "- Requirement: \`ada_language_server\` must be on PATH (not bundled). Override via \`ADAFMT_ALS_PATH\` or \`--als-path\`." >> $(BUNDLE_FILE); \
	  echo "- Apply changes with \`--write\`; default is dry-run. Use \`--diff\` to preview unified diffs." >> $(BUNDLE_FILE); \
	  echo "- **Check mode**: \`--check\` returns **0** (no diffs), **1** (diffs), non-zero on errors." >> $(BUNDLE_FILE); \
	  echo "- **Exit codes (general)**: 0=success; non-zero indicates failure (fatal exceptions exit 1)." >> $(BUNDLE_FILE); \
	  echo "- **Logging**: JSONL log at \`./adafmt_<timestamp>_log.jsonl\`; pattern log at \`./adafmt_<timestamp>_patterns.log\`." >> $(BUNDLE_FILE); \
	  echo "- **Stderr mirror**: default \`./adafmt_<timestamp>_stderr.log\`; override with \`--stderr-path\`." >> $(BUNDLE_FILE); \
	  echo "- **Log file override**: \`--log-path\` sets the JSONL log location." >> $(BUNDLE_FILE); \
	  echo >> $(BUNDLE_FILE); \
	  echo "#### TEMPLATE (Claude fills this; return only body + optional footer)" >> $(BUNDLE_FILE); \
	  echo "<overview, 2–3 sentences summarizing user-visible value>" >> $(BUNDLE_FILE); \
	  echo "" >> $(BUNDLE_FILE); \
	  echo "- <bullet 1: capability or improvement>" >> $(BUNDLE_FILE); \
	  echo "- <bullet 2: key flag/config with brief usage>" >> $(BUNDLE_FILE); \
	  echo "- <bullet 3: robustness/perf/accuracy note>" >> $(BUNDLE_FILE); \
	  echo "- <bullet 4: operational behavior (exit codes, --check semantics, etc.)>" >> $(BUNDLE_FILE); \
	  echo "- <bullet 5: integrations (Alire/GPR detection, path handling)>" >> $(BUNDLE_FILE); \
	  echo "- <bullet 6+: other top items, 1–2 lines each>" >> $(BUNDLE_FILE); \
	  echo "- **Requirement:** \`ada_language_server\` must be on PATH" >> $(BUNDLE_FILE); \
	  echo "" >> $(BUNDLE_FILE); \
	  echo "[optional tiny example(s)]" >> $(BUNDLE_FILE); \
	  echo "" >> $(BUNDLE_FILE); \
	  echo "[If needed, after one blank line:]" >> $(BUNDLE_FILE); \
	  echo "BREAKING CHANGE: <one short sentence of the breaking surface>" >> $(BUNDLE_FILE) \
	; }