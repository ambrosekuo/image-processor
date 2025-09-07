PY=python3

.PHONY: setup dev install run api test fmt lint precommit docker

setup:
	$(PY) -m venv .venv
	. .venv/bin/activate; pip install -U pip
	. .venv/bin/activate; pip install -e ".[dev]"
	pre-commit install

install:
	. .venv/bin/activate; pip install -e .

dev:
	. .venv/bin/activate; pip install -e ".[dev]"

run:
	. .venv/bin/activate; sprite-processor --help

api:
	. .venv/bin/activate; sprite-processor-api --host 0.0.0.0 --port 8000

fmt:
	. .venv/bin/activate; black src tests
	. .venv/bin/activate; isort src tests

lint:
	. .venv/bin/activate; ruff check src tests

test:
	. .venv/bin/activate; pytest -q

precommit:
	pre-commit run --all-files

docker:
	docker build -t sprite-processor:local .
