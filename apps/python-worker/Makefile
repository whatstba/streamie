.PHONY: test test-integration test-unit test-coverage test-watch install clean

# Install dependencies
install:
	pip install -r requirements.txt

# Run all tests
test:
	pytest tests/ -v

# Run only integration tests
test-integration:
	pytest tests/integration/ -v -m integration

# Run only unit tests  
test-unit:
	pytest tests/ -v -m unit

# Run tests with coverage
test-coverage:
	pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

# Run tests in watch mode
test-watch:
	pytest-watch tests/ -- -v

# Run specific test file
test-file:
	@read -p "Enter test file path: " filepath; \
	pytest $$filepath -v

# Clean up cache and coverage files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -f .coverage

# Run linting
lint:
	flake8 . --exclude=venv,__pycache__
	black . --check --exclude=venv

# Format code
format:
	black . --exclude=venv

# Full CI pipeline
ci: clean lint test-coverage