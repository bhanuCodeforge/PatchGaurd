# PatchGuard Monorepo Makefile

.PHONY: up down down-v restart logs logs-f shell shell-db shell-redis migrate makemigrations test test-verbose seed help setup clean rebuild

# Colors
GREEN=\033[0;32m
YELLOW=\033[0;33m
NC=\033[0m # No Color

## @@@ DOCKER COMPOSE COMMANDS @@@

up: ## Start all services in the background
	@echo "$(GREEN)Starting PatchGuard services...$(NC)"
	docker compose up -d

down: ## Stop all running services
	@echo "$(YELLOW)Stopping PatchGuard services...$(NC)"
	docker compose down

down-v: ## Stop all services AND remove volumes (Destroys Database!)
	@echo "$(YELLOW)Stopping services and removing volumes...$(NC)"
	docker compose down -v

rebuild: ## Force rebuild and restart all services
	@echo "$(GREEN)Rebuilding containers...$(NC)"
	docker compose up -d --build

restart: ## Restart all services
	@echo "$(GREEN)Restarting PatchGuard...$(NC)"
	docker compose restart

logs: ## View logs from all services
	docker compose logs

logs-f: ## Follow logs from all services
	docker compose logs -f

logs-django: ## Follow Django backend logs
	docker compose logs -f django

logs-fastapi: ## Follow FastAPI realtime logs
	docker compose logs -f fastapi

logs-frontend: ## Follow Angular frontend logs
	docker compose logs -f frontend

logs-celery: ## Follow Celery worker logs
	docker compose logs -f celery-worker

## @@@ SHELL ACCESS @@@

shell: ## Open bash shell in the Django container
	docker compose exec django bash

shell-db: ## Open PostgreSQL CLI
	docker compose exec postgres psql -U patchmgr -d patchmgr

shell-redis: ## Open Redis CLI
	docker compose exec redis redis-cli

shell-frontend: ## Open sh shell in the Angular container
	docker compose exec frontend sh

## @@@ DJANGO COMMANDS @@@

migrate: ## Run Django database migrations
	@echo "$(GREEN)Applying migrations...$(NC)"
	docker compose exec django python manage.py migrate

makemigrations: ## Generate new Django migrations
	@echo "$(GREEN)Generating migrations...$(NC)"
	docker compose exec django python manage.py makemigrations

superuser: ## Create a new Django superuser
	docker compose exec django python manage.py createsuperuser

seed: ## Seed the database with sample data
	@echo "$(GREEN)Seeding database...$(NC)"
	docker compose exec django python /app/../scripts/seed-data.py

## @@@ TESTING COMMANDS @@@

test: ## Run Django test suite
	@echo "$(GREEN)Running Python tests...$(NC)"
	docker compose exec django pytest -v --tb=short

test-verbose: ## Run Django tests with full traceback
	@echo "$(GREEN)Running tests in verbose mode...$(NC)"
	docker compose exec django pytest -v --tb=long

test-frontend: ## Run Angular tests
	@echo "$(GREEN)Running Angular tests...$(NC)"
	docker compose exec frontend npm run test -- --watch=false

test-all: test test-frontend ## Run backend and frontend tests

## @@@ UTILITIES @@@

setup: ## Initial setup (create env, build, migrate, seed)
	@echo "$(GREEN)Running full setup...$(NC)"
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file"; fi
	docker compose build
	docker compose up -d
	@echo "Waiting for database..."
	sleep 10
	docker compose exec django python manage.py migrate

clean: down-v ## Remove all generated files, containers, and data volumes
	@echo "$(YELLOW)Cleaning codebase...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

help: ## Show this help menu
	@echo "PatchGuard Makefile Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
