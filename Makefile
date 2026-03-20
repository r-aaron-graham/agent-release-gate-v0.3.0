install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload

seed:
	python -m app.seed

test:
	pytest -q

migrate:
	alembic revision --autogenerate -m "update schema"

upgrade:
	alembic upgrade head
