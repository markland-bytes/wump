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

For detailed setup instructions, see [QUICKSTART.md](QUICKSTART.md)

### Local Development

For running commands directly on your machine (e.g., `uv run pytest`, `uv run mypy`), see [api/README.md](api/README.md)

### Prerequisites

- **Docker** & **Docker Compose** - All services run in containers

---

## 📁 Repository Structure

```
wump/                    # Repository root & orchestration
├── api/                 # REST API service (FastAPI)
├── docker-compose.yml   # Service orchestration
├── ARCHITECTURE.md      # Technical design & database schema
├── DEVELOPMENT.md       # Contributing guidelines
├── QUICKSTART.md        # 5-minute setup guide
└── README.md            # This file
```

## 📚 Documentation & Contributing

**Getting Started:**
- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide with Docker

**Contributing & Development:**
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Git workflow, commit conventions, PR process

**Technical Details:**
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and database schema
- **[api/README.md](api/README.md)** - API service development setup and commands

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
