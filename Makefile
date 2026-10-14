.PHONY: help install setup db api ui test benchmark docker clean

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make setup      - Full setup (venv + deps + db)"
	@echo "  make db         - Initialize database"
	@echo "  make api        - Start FastAPI server"
	@echo "  make ui         - Start Streamlit UI"
	@echo "  make test       - Run all tests"
	@echo "  make benchmark  - Run performance tests"
	@echo "  make docker     - Start with Docker Compose"
	@echo "  make clean      - Clean up generated files"

install:
	pip install -r requirements.txt

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
	python create_db.py

db:
	python create_db.py

api:
	uvicorn api:app --reload --host 0.0.0.0 --port 8000

ui:
	streamlit run app_v2.py

test:
	python -m pytest test_utils.py test_agent.py test_core.py test_ops.py eval/test_regression_20.py -v

benchmark:
	python eval/benchmark_20.py --iterations 5

benchmark-baseline:
	python eval/benchmark_20.py --iterations 5 --save

benchmark-check:
	python eval/benchmark_20.py --iterations 5 --baseline eval/benchmarks.jsonl --check

docker:
	docker-compose up --build

docker-down:
	docker-compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -f student_grades.db
