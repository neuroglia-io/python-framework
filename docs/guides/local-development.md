# 🛠️ Local Development Environment Setup

Set up a complete local development environment for productive Neuroglia development. This guide covers tooling, IDE setup, debugging, and best practices for building maintainable applications.

!!! info "🎯 What You'll Set Up"
A professional development environment with debugging, testing, linting, and database integration.

## 📋 Prerequisites

### System Requirements

- **Python 3.8+** with pip
- **Git** for version control
- **Docker & Docker Compose** for services (MongoDB, Redis, etc.)
- **VS Code** or **PyCharm** (recommended IDEs)

### Verify Installation

```bash
python --version  # Should be 3.8+
pip --version
git --version
docker --version
docker-compose --version
```

## 🚀 Project Setup

### 1. Create Project Structure

```bash
# Create project directory
mkdir my-neuroglia-app && cd my-neuroglia-app

# Initialize git repository
git init

# Create standard project structure
mkdir -p src/{api,application,domain,integration}
mkdir -p src/api/{controllers,dtos}
mkdir -p src/application/{commands,queries,handlers}
mkdir -p src/domain/{entities,events,repositories}
mkdir -p src/integration/{repositories,services}
mkdir -p tests/{unit,integration,fixtures}
mkdir -p docs
touch README.md
```

### 2. Python Environment Setup

**Option A: Using Poetry (Recommended)**

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Initialize Poetry project
poetry init

# Add Neuroglia and development dependencies
poetry add neuroglia-python[web]
poetry add --group dev pytest pytest-asyncio pytest-cov black flake8 mypy

# Create virtual environment and activate
poetry install
poetry shell
```

**Option B: Using venv**

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install neuroglia-python[web]
pip install pytest pytest-asyncio pytest-cov black flake8 mypy
```

### 3. Development Configuration Files

**pyproject.toml** (Poetry users):

```toml
[tool.poetry]
name = "my-neuroglia-app"
version = "0.1.0"
description = "My Neuroglia Application"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.8"
neuroglia-python = {extras = ["web"], version = "^1.0.0"}

[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
pytest-asyncio = "^0.20.0"
pytest-cov = "^4.0.0"
black = "^22.0.0"
flake8 = "^5.0.0"
mypy = "^1.0.0"

[tool.black]
line-length = 88
target-version = ['py38']

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**requirements.txt** (venv users):

```txt
neuroglia-python[web]>=1.0.0
pytest>=7.0.0
pytest-asyncio>=0.20.0
pytest-cov>=4.0.0
black>=22.0.0
flake8>=5.0.0
mypy>=1.0.0
```

**pytest.ini**:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = --cov=src --cov-report=html --cov-report=term
```

## 🔧 IDE Configuration

### VS Code Setup

**Install Extensions**:

```bash
# Install VS Code extensions
code --install-extension ms-python.python
code --install-extension ms-python.black-formatter
code --install-extension ms-python.flake8
code --install-extension ms-python.mypy-type-checker
code --install-extension bradlc.vscode-tailwindcss
code --install-extension ms-vscode.vscode-json
```

**.vscode/settings.json**:

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

**.vscode/launch.json** (for debugging):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/src/main.py",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    },
    {
      "name": "Python: Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["tests", "-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

## 🐳 Docker Development Services

**docker-compose.dev.yml**:

```yaml
version: "3.8"

services:
  mongodb:
    image: mongo:5.0
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password
    volumes:
      - mongodb_data:/data/db
    networks:
      - neuroglia-dev

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - neuroglia-dev

  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025" # SMTP
      - "8025:8025" # Web UI
    networks:
      - neuroglia-dev

volumes:
  mongodb_data:

networks:
  neuroglia-dev:
    driver: bridge
```

**Start development services**:

```bash
docker-compose -f docker-compose.dev.yml up -d
```

## 🧪 Testing Setup

**tests/conftest.py**:

```python
import pytest
from neuroglia.dependency_injection import ServiceCollection
from neuroglia.mediation import Mediator

@pytest.fixture
def service_collection():
    """Create a fresh service collection for testing"""
    return ServiceCollection()

@pytest.fixture
def service_provider(service_collection):
    """Create a service provider for testing"""
    service_collection.add_mediator()
    return service_collection.build_provider()

@pytest.fixture
def mediator(service_provider):
    """Get mediator instance for testing"""
    return service_provider.get_service(Mediator)
```

**tests/unit/test_example.py**:

```python
import pytest
from src.domain.entities.example import ExampleEntity

class TestExampleEntity:
    def test_entity_creation(self):
        """Test entity can be created successfully"""
        entity = ExampleEntity(name="Test")
        assert entity.name == "Test"
        assert entity.id is not None

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async operations work correctly"""
        # Add async test logic here
        pass
```

## 🏃‍♂️ Development Workflow

### Daily Development Commands

```bash
# Start development services
docker-compose -f docker-compose.dev.yml up -d

# Activate virtual environment (if using venv)
source venv/bin/activate  # or `poetry shell`

# Run your application
python src/main.py

# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Format code
black src tests

# Lint code
flake8 src tests

# Type checking
mypy src
```

### Git Hooks Setup

**.pre-commit-config.yaml**:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3.8

  - repo: https://github.com/pycqa/flake8
    rev: 5.0.4
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
```

Install pre-commit:

```bash
pip install pre-commit
pre-commit install
```

## 🔍 Debugging and Monitoring

### Application Logging

**src/config/logging.py**:

```python
import logging
import sys
from pathlib import Path

def setup_logging(log_level: str = "INFO"):
    """Configure application logging"""

    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Configure third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
```

### Environment Configuration

**.env.development**:

```bash
# Application
APP_NAME=My Neuroglia App
APP_VERSION=0.1.0
DEBUG=true
LOG_LEVEL=DEBUG

# Database
MONGODB_URL=mongodb://admin:password@localhost:27017
REDIS_URL=redis://localhost:6379

# External Services
SMTP_HOST=localhost
SMTP_PORT=1025
```

## ✅ Environment Validation

Create a validation script to ensure everything is set up correctly:

**scripts/validate-env.py**:

```python
#!/usr/bin/env python3
"""Validate development environment setup"""

import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import neuroglia
        print("✅ Neuroglia installed")
        return True
    except ImportError:
        print("❌ Neuroglia not installed")
        return False

def check_docker():
    """Check if Docker services are running"""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            check=True
        )
        if "mongo" in result.stdout and "redis" in result.stdout:
            print("✅ Docker services running")
            return True
        else:
            print("⚠️  Docker services not all running")
            return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker not available")
        return False

if __name__ == "__main__":
    checks = [
        check_python_version(),
        check_dependencies(),
        check_docker()
    ]

    if all(checks):
        print("\n🎉 Development environment is ready!")
    else:
        print("\n❌ Some issues need to be resolved")
        sys.exit(1)
```

Run validation:

```bash
python scripts/validate-env.py
```

## 🔄 Next Steps

Your development environment is now ready! Continue with:

1. **[⚡ 3-Minute Bootstrap](3-min-bootstrap.md)** - Quick hello world setup
2. **[🍕 Mario's Pizzeria Tutorial](mario-pizzeria-tutorial.md)** - Build a complete application
3. **[🎯 Architecture Patterns](../patterns/index.md)** - Learn design principles
4. **[🚀 Framework Features](../features/index.md)** - Explore advanced capabilities

## 🔗 Related Documentation

- **[Dependency Injection Setup](../patterns/dependency-injection.md)** - Advanced DI configuration
- **[Testing Strategies](testing-setup.md)** - Comprehensive testing approaches
- **[Project Structure](project-setup.md)** - Detailed project organization

---

!!! tip "🎯 Pro Tip"
Bookmark this page! You'll refer back to these commands and configurations throughout your development journey.
