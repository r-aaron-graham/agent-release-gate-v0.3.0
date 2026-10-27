.PHONY: install dev run seed test lint migrate upgrade docker docker-run

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt

run:
	uvicorn app.main:app --reload

seed:
	python -m app.seed

test:
	pytest -q --cov=app --cov-report=term-missing

lint:
	ruff check .

migrate:
	alembic revision --autogenerate -m "update schema"

upgrade:
	alembic upgrade head

docker:
	docker build -t agent-release-gate:local .

docker-run: docker
	docker run --rm -p 8000:8000 agent-release-gate:local
