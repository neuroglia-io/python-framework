# Makefile for Neuroglia Python Framework
#
# This Makefile provides convenient commands for building, testing, and managing
# the Neuroglia Python framework and its sample applications.

.PHONY: help install dev-install build test test-coverage lint format clean docs docs-serve docs-build publish sample-mario sample-openbank sample-gateway mario-start mario-stop mario-restart mario-status mario-logs mario-clean mario-reset mario-open mario-test-data mario-clean-orders mario-create-menu mario-remove-validation

# Default target
help: ## Show this help message
	@echo "🐍 Neuroglia Python Framework - Build System"
	@echo ""
	@echo "Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# Python and Poetry commands
PYTHON := python3
POETRY := poetry
PIP := pip

# Project directories
SRC_DIR := src
DOCS_DIR := docs
SAMPLES_DIR := samples
TESTS_DIR := tests
SCRIPTS_DIR := scripts

# Sample applications
MARIO_PIZZERIA := $(SAMPLES_DIR)/mario-pizzeria
OPENBANK := $(SAMPLES_DIR)/openbank
API_GATEWAY := $(SAMPLES_DIR)/api-gateway
DESKTOP_CONTROLLER := $(SAMPLES_DIR)/desktop-controller
LAB_RESOURCE_MANAGER := $(SAMPLES_DIR)/lab_resource_manager

##@ Installation & Setup

install: ## Install production dependencies and pre-commit hooks
	@echo "📦 Installing production dependencies..."
	$(POETRY) install --only=main
	@echo "🪝 Installing pre-commit hooks..."
	$(POETRY) run pre-commit install

dev-install: ## Install development dependencies
	@echo "🔧 Installing development dependencies..."
	$(POETRY) install
	@echo "✅ Development environment ready!"

setup-path: ## Add pyneuroctl to system PATH
	@echo "🔧 Setting up pyneuroctl in PATH..."
	@chmod +x $(SCRIPTS_DIR)/setup/add_to_path.sh
	@$(SCRIPTS_DIR)/setup/add_to_path.sh

##@ Building & Packaging

build: ## Build the package
	@echo "🏗️  Building package..."
	$(POETRY) build
	@echo "✅ Package built successfully!"

clean: ## Clean build artifacts and cache files
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf dist/
	@rm -rf build/
	@rm -rf *.egg-info/
	@find . -type d -name __pycache__ -delete
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type d -name ".pytest_cache" -delete
	@find . -type d -name ".coverage" -delete
	@rm -rf site/
	@echo "✅ Cleanup completed!"

##@ Testing

test: ## Run all tests
	@echo "🧪 Running all tests..."
	$(POETRY) run pytest $(TESTS_DIR)/ -v --tb=short

test-coverage: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	$(POETRY) run pytest $(TESTS_DIR)/ --cov=$(SRC_DIR)/neuroglia --cov-report=html --cov-report=term --cov-report=xml
	@echo "📊 Coverage report generated in htmlcov/"

test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests..."
	$(POETRY) run pytest $(TESTS_DIR)/unit/ -v

test-integration: ## Run integration tests only
	@echo "🧪 Running integration tests..."
	$(POETRY) run pytest $(TESTS_DIR)/integration/ -v

test-mario: ## Test Mario's Pizzeria sample
	@echo "🍕 Testing Mario's Pizzeria..."
	$(POETRY) run pytest $(TESTS_DIR)/ -k mario_pizzeria -v

test-samples: ## Test all sample applications
	@echo "🧪 Testing all samples..."
	$(POETRY) run pytest $(TESTS_DIR)/ -k "mario_pizzeria or openbank or api_gateway or desktop_controller" -v

##@ Code Quality

lint: ## Run linting (flake8, pylint)
	@echo "🔍 Running linting..."
	$(POETRY) run flake8 $(SRC_DIR)/ $(SAMPLES_DIR)/ $(TESTS_DIR)/
	$(POETRY) run pylint $(SRC_DIR)/neuroglia/

format: ## Format code with black and isort
	@echo "🎨 Formatting code..."
	$(POETRY) run black $(SRC_DIR)/ $(SAMPLES_DIR)/ $(TESTS_DIR)/
	$(POETRY) run isort $(SRC_DIR)/ $(SAMPLES_DIR)/ $(TESTS_DIR)/
	@echo "✅ Code formatting completed!"

format-check: ## Check code formatting without making changes
	@echo "🔍 Checking code formatting..."
	$(POETRY) run black --check $(SRC_DIR)/ $(SAMPLES_DIR)/ $(TESTS_DIR)/
	$(POETRY) run isort --check-only $(SRC_DIR)/ $(SAMPLES_DIR)/ $(TESTS_DIR)/

##@ Documentation

docs: ## Build documentation
	@echo "📚 Building documentation..."
	$(POETRY) run mkdocs build
	@echo "✅ Documentation built in site/"

docs-serve: ## Serve documentation locally (development server)
	@echo "📚 Starting documentation server..."
	$(eval DEV_PORT := $(shell grep '^DOCS_DEV_PORT=' .env 2>/dev/null | cut -d'=' -f2 | tr -d ' ' || echo '8000'))
	@echo "Checking for existing servers on port $(DEV_PORT)..."
	@lsof -ti:$(DEV_PORT) | xargs -r kill -9 2>/dev/null || true
	@echo "✅ Open http://127.0.0.1:$(DEV_PORT) in your browser"
	poetry run mkdocs serve --dev-addr=127.0.0.1:$(DEV_PORT)

docs-deploy: ## Deploy documentation to GitHub Pages
	@echo "🚀 Deploying documentation..."
	$(POETRY) run mkdocs gh-deploy

docs-validate: ## Validate Mermaid diagrams in documentation
	@echo "📊 Validating Mermaid diagrams..."
	$(PYTHON) validate_mermaid.py

##@ Publishing

publish-test: ## Publish to TestPyPI
	@echo "🚀 Publishing to TestPyPI..."
	$(POETRY) config repositories.testpypi https://test.pypi.org/legacy/
	$(POETRY) publish -r testpypi

publish: build ## Publish to PyPI
	@echo "🚀 Publishing to PyPI..."
	$(POETRY) publish

##@ Sample Applications

sample-openbank: ## Run OpenBank sample
	@echo "🏦 Starting OpenBank..."
	cd $(OPENBANK) && $(POETRY) run $(PYTHON) main.py

sample-gateway: ## Run API Gateway sample
	@echo "🌐 Starting API Gateway..."
	cd $(API_GATEWAY) && $(POETRY) run $(PYTHON) main.py

sample-desktop: ## Run Desktop Controller sample
	@echo "🖥️  Starting Desktop Controller..."
	cd $(DESKTOP_CONTROLLER) && $(POETRY) run $(PYTHON) main.py

sample-lab: ## Run Lab Resource Manager sample
	@echo "🧪 Starting Lab Resource Manager..."
	cd $(LAB_RESOURCE_MANAGER) && $(POETRY) run $(PYTHON) main.py

sample-simple-ui: ## Run Simple UI sample (standalone, no Docker)
	@echo "📱 Starting Simple UI..."
	cd $(SAMPLES_DIR)/simple-ui && $(POETRY) run $(PYTHON) main.py

##@ Sample Management (using pyneuroctl)

samples-list: ## List all available samples
	@echo "📋 Available sample applications:"
	@$(PYTHON) $(SRC_DIR)/cli/pyneuroctl.py list

samples-status: ## Show status of all samples
	@echo "📊 Sample application status:"
	@$(PYTHON) $(SRC_DIR)/cli/pyneuroctl.py status

samples-stop: ## Stop all running samples
	@echo "⏹️  Stopping all sample applications..."
	@$(PYTHON) $(SRC_DIR)/cli/pyneuroctl.py stop --all

##@ Shared Infrastructure

infra-start: ## Start shared infrastructure services (MongoDB, Keycloak, Observability)
	@./infra start

infra-stop: ## Stop shared infrastructure services
	@./infra stop

infra-restart: ## Restart shared infrastructure services
	@./infra restart

infra-recreate: ## Recreate infrastructure services (use SERVICE=name for specific service)
	@./infra recreate $(if $(SERVICE),$(SERVICE),)

infra-recreate-clean: ## Recreate infrastructure with fresh volumes (deletes all data!)
	@./infra recreate --delete-volumes $(if $(SERVICE),$(SERVICE),)

infra-status: ## Check status of shared infrastructure
	@./infra status

infra-logs: ## View logs for shared infrastructure
	@./infra logs

infra-clean: ## Stop and clean shared infrastructure (removes volumes)
	@./infra clean

infra-build: ## Rebuild infrastructure Docker images
	@./infra build

infra-reset: ## Complete reset of infrastructure (clean + start)
	@./infra reset

infra-ps: ## List infrastructure containers
	@./infra ps

infra-health: ## Health check for infrastructure services
	@./infra health

##@ Keycloak Management

keycloak-reset: ## Reset Keycloak (delete volume and restart with fresh realm import)
	@echo "🔐 Resetting Keycloak..."
	@echo "⚠️  This will delete all Keycloak data and reimport the realm from file"
	@echo "⏹️  Stopping Keycloak..."
	@docker compose -f deployment/docker-compose/docker-compose.shared.yml stop keycloak
	@echo "🗑️  Deleting Keycloak data volume..."
	@docker volume rm pyneuro_keycloak_data 2>/dev/null || echo "Volume doesn't exist or already deleted"
	@echo "🚀 Starting Keycloak with fresh import..."
	@docker compose -f deployment/docker-compose/docker-compose.shared.yml up -d keycloak
	@echo "⏳ Waiting for Keycloak to be ready..."
	@sleep 15
	@echo "🔧 Configuring realms..."
	@./deployment/keycloak/configure-master-realm.sh
	@echo "✅ Keycloak reset complete!"

keycloak-configure: ## Configure Keycloak realms (disable SSL, import pyneuro realm if needed)
	@echo "🔧 Configuring Keycloak..."
	@./deployment/keycloak/configure-master-realm.sh

keycloak-logs: ## View Keycloak logs
	@docker compose -f deployment/docker-compose/docker-compose.shared.yml logs -f keycloak

keycloak-restart: ## Restart Keycloak (preserves data)
	@echo "🔄 Restarting Keycloak..."
	@docker compose -f deployment/docker-compose/docker-compose.shared.yml restart keycloak
	@echo "⏳ Waiting for Keycloak to be ready..."
	@sleep 10
	@echo "✅ Keycloak restarted!"

keycloak-export: ## Export current Keycloak realm configuration
	@echo "📤 Exporting pyneuro realm..."
	@docker exec pyneuro-keycloak-1 /opt/keycloak/bin/kc.sh export \
		--dir /opt/keycloak/data/import \
		--realm pyneuro \
		--users realm_file
	@echo "✅ Realm exported to container:/opt/keycloak/data/import/pyneuro-realm.json"
	@echo "💡 Copy it out with: docker cp pyneuro-keycloak-1:/opt/keycloak/data/import/pyneuro-realm.json deployment/keycloak/"

keycloak-create-users: ## Create/update test users with passwords
	@echo "👥 Creating test users in Keycloak..."
	@./deployment/keycloak/create-test-users.sh

##@ Mario's Pizzeria

mario-start: ## Start Mario's Pizzeria with shared infrastructure
	@./mario-pizzeria start

mario-stop: ## Stop Mario's Pizzeria and all services
	@./mario-pizzeria stop

mario-restart: ## Restart Mario's Pizzeria
	@./mario-pizzeria restart

mario-status: ## Check Mario's Pizzeria status
	@./mario-pizzeria status

mario-logs: ## View logs for Mario's Pizzeria
	@./mario-pizzeria logs

mario-clean: ## Stop Mario's Pizzeria and clean volumes
	@./mario-pizzeria clean

mario-build: ## Rebuild Mario's Pizzeria Docker image
	@./mario-pizzeria build

##@ Simple UI Sample

simple-ui-start: ## Start Simple UI with shared infrastructure
	@./simple-ui start

simple-ui-stop: ## Stop Simple UI and all services
	@./simple-ui stop

simple-ui-restart: ## Restart Simple UI
	@./simple-ui restart

simple-ui-status: ## Check Simple UI status
	@./simple-ui status

simple-ui-logs: ## View logs for Simple UI
	@./simple-ui logs

simple-ui-clean: ## Stop Simple UI and clean volumes
	@./simple-ui clean

simple-ui-build: ## Rebuild Simple UI Docker image
	@./simple-ui build

##@ Multi-Sample Commands

all-samples-start: ## Start all samples with shared infrastructure
	@echo "🚀 Starting all samples..."
	@$(MAKE) infra-start
	@$(MAKE) mario-start
	@$(MAKE) simple-ui-start
	@echo "✅ All samples started!"

all-samples-stop: ## Stop all samples and services
	@echo "⏹️  Stopping all samples..."
	@$(MAKE) mario-stop
	@$(MAKE) simple-ui-stop

all-samples-clean: ## Stop all samples and clean everything
	@echo "🧹 Cleaning all samples and infrastructure..."
	@$(MAKE) mario-clean
	@$(MAKE) simple-ui-clean
	@$(MAKE) infra-clean
	@echo "✅ All samples and infrastructure cleaned!"

##@ Legacy Commands (mario-docker.sh compatibility)

mario-reset: ## Complete reset of Mario's Pizzeria environment (destructive)
	@./mario-pizzeria reset

mario-open: ## Open key Mario's Pizzeria services in browser
	@echo "🌐 Opening Mario's Pizzeria services in browser..."
	@open http://localhost:8080 &
	@open http://localhost:3001 &
	@sleep 1
	@echo "✅ Opened Mario's Pizzeria UI and Grafana dashboards"

mario-test-data: ## Generate test data for Mario's Pizzeria observability dashboards
	@echo "🍕 Generating test data for Mario's Pizzeria..."
	@$(POETRY) run python samples/mario-pizzeria/scripts/generate_test_data.py --count 10

mario-clean-orders: ## Remove all order data from Mario's Pizzeria MongoDB
	@echo "🧹 Cleaning orders from MongoDB..."
	@docker exec -it $$(docker ps -qf "name=mongodb") mongosh --eval "use mario_pizzeria; db.orders.deleteMany({});" -u root -p neuroglia123 --authenticationDatabase admin

mario-create-menu: ## Create default pizza menu in Mario's Pizzeria
	@echo "🍕 Creating default menu..."
	@$(POETRY) run python samples/mario-pizzeria/scripts/create_menu.py

mario-remove-validation: ## Remove MongoDB validation schemas (use app validation only)
	@echo "🔧 Removing MongoDB validation..."
	@docker exec -it $$(docker ps -qf "name=mongodb") mongosh --eval "use mario_pizzeria; db.runCommand({collMod: 'orders', validator: {}, validationLevel: 'off'});" -u root -p neuroglia123 --authenticationDatabase admin

openbank-start: ## Start OpenBank using CLI
	@$(PYTHON) $(SRC_DIR)/cli/pyneuroctl.py start openbank

openbank-stop: ## Stop OpenBank using CLI
	@$(PYTHON) $(SRC_DIR)/cli/pyneuroctl.py stop openbank

##@ Development Workflows

dev-setup: dev-install setup-path ## Complete development setup
	@echo "🎉 Development environment fully configured!"

dev-test: format lint test-coverage ## Full development testing cycle
	@echo "✅ All development checks passed!"

pre-commit: format-check lint test ## Pre-commit checks
	@echo "✅ Pre-commit checks completed!"

release-prep: clean build test-coverage docs lint ## Prepare for release
	@echo "🚀 Release preparation completed!"

##@ Docker Support

docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t neuroglia-python .

docker-run: ## Run application in Docker
	@echo "🐳 Running in Docker..."
	docker-compose -f docker-compose.dev.yml up

docker-dev: ## Start development environment with Docker
	@echo "🐳 Starting development environment..."
	docker-compose -f docker-compose.dev.yml up -d

docker-logs: ## Show Docker container logs
	@echo "📝 Docker container logs:"
	docker-compose -f docker-compose.dev.yml logs -f

docker-stop: ## Stop Docker containers
	@echo "⏹️  Stopping Docker containers..."
	docker-compose -f docker-compose.dev.yml down

##@ Utilities

version: ## Show current version
	@echo "📦 Neuroglia Python Framework"
	@$(POETRY) version

deps-check: ## Check for outdated dependencies
	@echo "🔍 Checking for outdated dependencies..."
	$(POETRY) show --outdated

deps-update: ## Update all dependencies
	@echo "⬆️  Updating dependencies..."
	$(POETRY) update

security-check: ## Run security checks
	@echo "🔒 Running security checks..."
	$(POETRY) run safety check

install-hooks: ## Install pre-commit hooks
	@echo "🪝 Installing pre-commit hooks..."
	$(POETRY) run pre-commit install

##@ Quick Commands

all: dev-install pre-commit docs build ## Install, test, document, and build everything
	@echo "🎉 Complete build cycle finished!"

demo: sample-mario-bg ## Start Mario's Pizzeria demo in background
	@echo "🍕 Demo started! Visit http://localhost:8000"
	@echo "📖 API docs at http://localhost:8000/docs"

stop-demo: ## Stop demo application
	@if [ -f $(MARIO_PIZZERIA)/pizza.pid ]; then \
		kill $$(cat $(MARIO_PIZZERIA)/pizza.pid) && rm $(MARIO_PIZZERIA)/pizza.pid; \
		echo "🍕 Demo stopped!"; \
	else \
		echo "❌ No demo running"; \
	fi
