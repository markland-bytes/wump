# wump: Who's Using My Package?

**Dependency sponsorship discovery API that helps open-source maintainers find organizations using their packages for potential sponsorship opportunities.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🎯 What is wump?

**The Problem:** Open-source maintainers don't know which organizations use their packages—making it impossible to pursue sponsorship opportunities.

**The Solution:** wump aggregates dependency data from GitHub and provides a searchable API to answer: "Who's using my package?" 

Example query:
```bash
GET /api/v1/packages/fastapi/users
# Returns: [{org: "Netflix", repos: 12}, {org: "Uber", repos: 8}, ...]
```

---

## 🚀 Getting Started

### With Docker Compose (Recommended)

```bash
git clone https://github.com/markland-bytes/wump.git
cd wump

# Copy environment template for the API service
cp api/.env.example api/.env

# Start all services
docker compose up -d
```

Access the API at:
- **API**: http://localhost:8000
- **Interactive docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health
- **Jaeger UI** (tracing): http://localhost:16686

For detailed setup instructions, see [QUICKSTART.md](docs/QUICKSTART.md)

### Seed Database

To populate the database with sample data for development:

```bash
# Using Docker
docker compose exec api uv run python seed.py

# Local development
cd api && uv run python seed.py
```

The seed script is idempotent and creates realistic sample data including organizations (Netflix, Shopify, etc.), popular packages (React, FastAPI, etc.), and their relationships.

### Local Development

For running commands directly on your machine (e.g., `uv run pytest`, `uv run mypy`), see [api/README.md](api/README.md)

### Prerequisites

- **Docker** & **Docker Compose** - All services run in containers

---

## 📁 Repository Structure

```
wump/                    # Repository root & orchestration
├── api/                 # REST API service (FastAPI)
├── docs/                # Documentation
├── docker-compose.yml   # Service orchestration
├── CLAUDE.md            # AI assistant guide
└── README.md            # This file
```

## 🗄️ Database Schema

The system uses PostgreSQL 18 with the following core tables:

```
┌─────────────────────────┐
│     organizations       │
│─────────────────────────│
│ id (UUID, PK)           │
│ name (unique)           │◄───┐
│ github_url              │    │
│ website_url             │    │
│ sponsorship_url         │    │
│ total_repositories      │    │
│ total_stars             │    │
│ created_at, updated_at  │    │
│ deleted_at              │    │
└─────────────────────────┘    │
                               │
                               │ 1:N
                               │
┌─────────────────────────┐    │
│      repositories       │    │
│─────────────────────────│    │
│ id (UUID, PK)           │    │
│ organization_id (FK)    │────┘
│ name                    │
│ github_url (unique)     │
│ stars                   │◄───┐
│ last_commit_at          │    │
│ is_archived             │    │
│ primary_language        │    │ 1:N
│ created_at, updated_at  │    │
└─────────────────────────┘    │
                               │
                               │
┌─────────────────────────┐    │
│      dependencies       │    │
│─────────────────────────│    │
│ id (UUID, PK)           │    │
│ repository_id (FK)      │────┘
│ package_id (FK)         │────┐
│ version                 │    │
│ dependency_type         │    │
│ detected_at             │    │
│ created_at, updated_at  │    │
└─────────────────────────┘    │
                               │ N:1
                               │
┌─────────────────────────┐    │
│        packages         │    │
│─────────────────────────│    │
│ id (UUID, PK)           │◄───┘
│ name                    │
│ ecosystem (npm/pypi/..) │
│ description             │
│ repository_url          │
│ homepage_url            │
│ latest_version          │
│ created_at, updated_at  │
└─────────────────────────┘
```

**Key Relationships:**
- Organizations have many Repositories (1:N)
- Repositories have many Dependencies (1:N)
- Packages are linked to Repositories through Dependencies (M:N)
- Organizations table includes soft delete support (`deleted_at`)

For full schema details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 📚 Documentation & Contributing

**Getting Started:**
- **[QUICKSTART.md](docs/QUICKSTART.md)** - 5-minute setup guide with Docker

**Contributing & Development:**
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Git workflow, commit conventions, PR process

**Technical Details:**
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and database schema
- **[api/README.md](api/README.md)** - API service development setup and commands
- **[API_EXAMPLES.md](docs/API_EXAMPLES.md)** - API usage examples and curl commands
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions

## 📝 License

MIT

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
