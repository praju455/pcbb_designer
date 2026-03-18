install:
	pip install -e .
	cd frontend && npm install

backend:
	uvicorn pcbai.api.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	uvicorn pcbai.api.main:app --reload --port 8000

test:
	python -m pytest -q
