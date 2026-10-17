.PHONY: up down init-db etl run-dashboard test clean

up:
	docker compose up -d

down:
	docker compose down

init-db:
	python scripts/setup_db.py

etl:
	python etl/run_etl.py

run-dashboard:
	streamlit run dashboard/app.py

test:
	pytest tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
