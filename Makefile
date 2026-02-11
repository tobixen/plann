# plann Makefile

.PHONY: help install dev test lint clean install-completion install-completion-user install-completion-system uninstall

PYTHON ?= python3
VENV = venv
COMPLETION_DIR_USER = $(HOME)/.local/share/bash-completion/completions
COMPLETION_DIR_SYSTEM = /usr/share/bash-completion/completions

help:
	@echo "plann - Command-line interface to calendars"
	@echo ""
	@echo "Installation:"
	@echo "  sudo make install                  Install system-wide"
	@echo "  make install                       Install for current user"
	@echo "  make uninstall                     Uninstall plann"
	@echo ""
	@echo "Development:"
	@echo "  make dev                           Install in development mode (Poetry)"
	@echo "  make test                          Run tests"
	@echo "  make lint                          Run linter"
	@echo "  make clean                         Clean build artifacts"
	@echo ""
	@echo "Shell Completion:"
	@echo "  make install-completion            Enable tab completion (user-local)"
	@echo "  sudo make install-completion-system  Enable tab completion (system-wide)"

# Create virtual environment
venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
		$(VENV)/bin/pip install --upgrade pip; \
	fi

# Install package via pip
# When run as root (sudo make install), installs system-wide with --break-system-packages.
# When run as a normal user, installs to the user's home directory with --user.
install:
	@if [ "$$(id -u)" = "0" ]; then \
		echo "Installing plann system-wide..."; \
		pip install --break-system-packages .; \
	else \
		echo "Installing plann for current user..."; \
		pip install --user .; \
	fi

# Uninstall plann
uninstall:
	@if [ "$$(id -u)" = "0" ]; then \
		pip uninstall --break-system-packages -y plann; \
	else \
		pip uninstall -y plann; \
	fi

# Install in development mode
dev:
	@echo "Installing in development mode..."
	@poetry install
	@echo ""
	@echo "Installed! Run: poetry run plann --help"

# Run tests
test:
	@poetry run pytest tests/ -v

# Run linter
lint:
	@poetry run ruff check .

# Clean build artifacts
clean:
	@rm -rf $(VENV) build dist *.egg-info .pytest_cache .ruff_cache
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true

# =============================================================================
# Shell Tab Completion (click-based)
# =============================================================================

install-completion: install-completion-user

install-completion-user:
	@echo "Installing shell completion for current user..."
	@mkdir -p "$(COMPLETION_DIR_USER)"
	@_PLANN_COMPLETE=bash_source plann > "$(COMPLETION_DIR_USER)/plann" 2>/dev/null || \
		poetry run python -c "import click; from plann.cli import cli; print(click.shell_completion.get_completion_class('bash')(cli, {}, 'plann', '_PLANN_COMPLETE').source())" > "$(COMPLETION_DIR_USER)/plann"
	@echo "Completion script installed to $(COMPLETION_DIR_USER)/plann"
	@echo "Restart your shell or run: source $(COMPLETION_DIR_USER)/plann"

install-completion-system:
	@echo "Installing shell completion system-wide..."
	@_PLANN_COMPLETE=bash_source plann > "$(COMPLETION_DIR_SYSTEM)/plann"
	@echo "Completion script installed to $(COMPLETION_DIR_SYSTEM)/plann"
