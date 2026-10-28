.PHONY: help install test lint verify-eval run docker-up docker-down

help:
	@echo "SignalGuard Developer Commands:"
	@echo "  make install      - Install Python dependencies"
	@echo "  make test         - Run pytest suite with coverage"
	@echo "  make lint         - Run Ruff static analysis"
	@echo "  make verify-eval  - Run AI evaluation lab verifier"
	@echo "  make run          - Run FastAPI development server"
	@echo "  make docker-up    - Start Docker Compose services"
	@echo "  make docker-down  - Stop Docker Compose services"

install:
	pip install -r requirements.txt

test:
	pytest -v --cov=backend/app --cov-report=term-missing

lint:
	ruff check backend evaluation tests

verify-eval:
	python -m evaluation.cli verify-all

run:
	uvicorn backend.app.main:app --reload --port 8000

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
