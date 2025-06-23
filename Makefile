# Makefile for Danish Audio Downloader

.PHONY: help test test-gui test-smoke install-deps clean lint coverage

# Default target
help:
	@echo "Available targets:"
	@echo "  test          - Run all tests"
	@echo "  test-gui      - Run GUI tests only"
	@echo "  test-smoke    - Run smoke tests only"
	@echo "  install-deps  - Install test dependencies"
	@echo "  lint          - Run code linting"
	@echo "  coverage      - Run tests with coverage report"
	@echo "  clean         - Clean temporary files"

# Run all tests
test:
	@echo "Running all tests..."
	@. .venv/bin/activate && python run_tests.py

# Run GUI tests only
test-gui:
	@echo "Running GUI tests..."
	@. .venv/bin/activate && python -m unittest test_gui_components -v

# Run smoke tests only
test-smoke:
	@echo "Running smoke tests..."
	@. .venv/bin/activate && python smoke_test.py

# Install test dependencies
install-deps:
	@echo "Installing test dependencies..."
	@. .venv/bin/activate && pip install -r requirements-test.txt

# Run linting
lint:
	@echo "Running linting..."
	@. .venv/bin/activate && flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Run tests with coverage
coverage:
	@echo "Running tests with coverage..."
	@. .venv/bin/activate && python -m pytest --cov=. --cov-report=html --cov-report=term

# Clean temporary files
clean:
	@echo "Cleaning temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache htmlcov .coverage 2>/dev/null || true
	@echo "Clean complete."
