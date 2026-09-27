.PHONY: lint format check test clean install sync all

install sync:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

check:
	uv run mypy .

test:
	uv run pytest tests/

clean:
	@echo "Cleaning up..."
	rm -rf .venv
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete."

all: format lint check test
