PYTHON := .venv/bin/python
PYTEST := .venv/bin/pytest

.PHONY: dev test lint ingest eval eval-install

dev:
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTEST) -q

lint:
	.venv/bin/ruff check .
	.venv/bin/black --check .

ingest:
	$(PYTHON) -m app.ingestion.ingest

eval:
	$(PYTHON) -m eval.run_ragas

eval-install:
	.venv/bin/pip install -r requirements-eval.txt
