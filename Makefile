.PHONY: install install-dev lint test test-unit test-integration clean

install:
pip install -e .

install-dev:
pip install -e ".[dev]"

lint:
ruff check src tests
ruff format --check src tests

format:
ruff format src tests
ruff check --fix src tests

test:
pytest tests/ -v

test-unit:
pytest tests/unit/ -v

test-integration:
pytest tests/integration/ -v

analyze:
python -m adapter_lab.main analyze $(URL)

discover:
python -m adapter_lab.main discover $(SOURCE)

fetch:
python -m adapter_lab.main fetch $(SOURCE)

clean:
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
