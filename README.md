# wump: Who's Using My Package?

**Dependency sponsorship discovery API that helps open-source maintainers find organizations using their packages for potential sponsorship opportunities.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)

---

## 🎯 What is wump?

Open-source maintainers struggle to identify which organizations use their packages in production. **wump** solves this by:

1. **Aggregating dependency data** from GitHub repositories across organizations
2. **Mapping packages to organizations** that use them in production
3. **Providing a searchable API** to answer: "Who's using my package?"
4. **Enabling targeted outreach** for sponsorship opportunities

### The Problem

- Maintainers don't know which companies depend on their work
- Organizations benefit from open-source but lack easy ways to support it
- Sponsorship outreach is inefficient and often misses key opportunities

### The Solution

A simple REST API where you can query:
```bash
GET /api/v1/packages/fastapi/users
# Returns: [{org: "Netflix", repos: 12}, {org: "Uber", repos: 8}, ...]
```

---

## 🌟 Key Features

- **📦 Package Discovery**: Search by package name, ecosystem (npm, PyPI, etc.)
- **🏢 Organization Insights**: See which orgs use your packages, with repository counts
- **🔍 Flexible Queries**: Filter by stars, language, last updated
- **⚡ Fast API**: Sub-500ms response times with caching
- **🔐 API Authentication**: Rate-limited access with API keys
- **📊 Background Jobs**: Automated data collection and updates

---

## 🚀 Quick Start

### Prerequisites
- Python 3.14+
- Docker & Docker Compose
- uv (Python package manager)

### Local Development Setup

1. **Clone and setup environment:**
```bash
git clone https://github.com/yourusername/wump.git
cd wump

# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
```

2. **Start services with Docker Compose:**
```bash
docker-compose up -d
```

This starts:
- FastAPI application (http://localhost:8000)
- PostgreSQL 18 database
- Valkey 8.x (Redis-compatible cache)

3. **Access the API:**
- **API**: http://localhost:8000
- **Interactive docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

### Development without Docker

```bash
# Install uv if not already installed
pip install uv

# Install dependencies
uv sync

# Run database migrations (when implemented)
# alembic upgrade head

# Start the development server
uv run uvicorn app.main:app --reload
```

## 📁 Project Structure

```
wump/
├── app/
│   ├── api/              # API routes and endpoints
│   ├── core/             # Core config, logging, etc.
│   ├── models/           # SQLAlchemy database models
│   ├── schemas/          # Pydantic request/response schemas
│   ├── services/         # Business logic
│   ├── providers/        # External data providers (GitHub, etc.)
│   └── main.py           # FastAPI application entry point
├── tests/                # Test suite
├── ARCHITECTURE.md       # System architecture and database schema
├── docker-compose.yml    # Local development services
├── Dockerfile            # Container image
├── pyproject.toml        # Python dependencies (uv)
└── .env.example          # Environment variables template
```

## 🛠️ Tech Stack

- **Runtime**: Python 3.14
- **Framework**: FastAPI 0.115+
- **Database**: PostgreSQL 18
- **Cache**: Valkey 8.x (Redis-compatible)
- **ORM**: SQLAlchemy 2.0+ (async)
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Testing**: pytest + httpx
- **Logging**: structlog (JSON)
- **Package Manager**: uv

## 📚 Documentation

- [**QUICKSTART.md**](QUICKSTART.md) - 5-minute setup guide
- [**DEVELOPMENT.md**](DEVELOPMENT.md) - Git workflow, commit conventions, contributing
- [**ARCHITECTURE.md**](ARCHITECTURE.md) - Technical design, database schema, API specs

## 🧪 Testing

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Run linting
uv run ruff check .

# Run type checking
uv run mypy app/
```

## � Project Management

We use **GitHub Issues + Projects** for task management:
- 📊 [Project Board](https://github.com/markland-bytes/wump/projects) - Current sprint and backlog
- 🐛 [Issues](https://github.com/markland-bytes/wump/issues) - Bugs, features, and tasks

## �📝 License

MIT

## 🤝 Contributing

We welcome contributions! Please see [DEVELOPMENT.md](DEVELOPMENT.md) for:
- Git workflow and branch naming conventions
- Commit message format
- Pull request process
- Code standards and testing requirements

## 🗺️ Roadmap

- **Phase 1 (Current)**: Foundation - Database models, migrations, basic API
- **Phase 2**: Core API - CRUD endpoints, search, pagination
- **Phase 3**: Background Jobs - Data ingestion from GitHub/Libraries.io
- **Phase 4**: Infrastructure - OpenTofu, Railway/AWS deployment
- **Phase 5**: Open Source Launch - Documentation, public release

## 💡 Business Model

**Open Core**: The code is fully open source (MIT), but we'll offer a hosted service with:
- Pre-populated database of millions of packages/organizations
- Continuous data updates
- High availability and support
- API keys and rate limiting

Self-hosting is free and encouraged for private deployments!

---

**Status**: 🚧 In Development - Phase 1 (Foundation)  
**License**: MIT  
**Maintainer**: [@markland-bytes](https://github.com/markland-bytes)
