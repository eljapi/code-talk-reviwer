.PHONY: help install install-dev test test-cov lint format type-check clean setup-dev

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

install-dev:  ## Install development dependencies
	pip install -r requirements-dev.txt
	pre-commit install

test:  ## Run tests
	pytest

test-cov:  ## Run tests with coverage
	pytest --cov=src --cov-report=html --cov-report=term-missing

lint:  ## Run linting
	flake8 src tests
	black --check src tests
	isort --check-only src tests

format:  ## Format code
	black src tests
	isort src tests

type-check:  ## Run type checking
	mypy src

clean:  ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

setup-dev:  ## Set up development environment
	python -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source venv/bin/activate  # On Linux/Mac"
	@echo "  venv\\Scripts\\activate     # On Windows"
	@echo "Then run: make install-dev"

check-deps:  ## Check if required dependencies are available
	@echo "Checking Python version..."
	@python --version | grep -E "Python 3\.(10|11|12)" || (echo "Python 3.10+ required" && exit 1)
	@echo "Python version OK"
	@echo "Checking pip..."
	@pip --version || (echo "pip not found" && exit 1)
	@echo "pip OK"