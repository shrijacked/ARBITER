.PHONY: check

check:
	uv run ruff check src tests
	uv run mypy
	uv run pytest
