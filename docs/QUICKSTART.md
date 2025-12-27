# Quick Start Guide
## Get wump running in 5 minutes

### Prerequisites Check
```bash
# Check Python version (need 3.14+)
python --version

# Check Docker
docker --version
docker compose version

# Install uv (Python package manager)
pip install uv
```

### Step 1: Clone and Setup
```bash
cd wump

# Copy environment file
cp .env.example .env

# Optional: Edit .env to add API keys
# nano .env
```

### Step 2: Start with Docker (Easiest)
```bash
# Build and start all services
docker compose up --build

# In another terminal, test it:
curl http://localhost:8000/health

# View logs
docker compose logs -f api

# Stop services
docker compose down
```

### Step 3: Start without Docker (Local Development)
```bash
# Install dependencies
uv sync

# Start PostgreSQL and Valkey separately (via Docker)
docker compose up db valkey -d

# Run the API locally
uv run uvicorn app.main:app --reload

# Test it
curl http://localhost:8000/health
```

### Step 4: View API Docs
Open in browser:
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Common Commands
```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app

# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run mypy app/

# Database migrations (when implemented)
uv run alembic upgrade head

# See all containers
docker compose ps

# View logs for specific service
docker compose logs -f db
docker compose logs -f valkey
docker compose logs -f api

# Restart just the API (after code changes)
docker compose restart api

# Clean everything
docker compose down -v  # Removes volumes too!
```

### Troubleshooting

**Port already in use:**
```bash
# Check what's using port 8000
lsof -i :8000

# Change the port in docker-compose.yml or .env
```

**Database connection fails:**
```bash
# Make sure PostgreSQL is running
docker compose ps db

# Check logs
docker compose logs db

# Manually connect to test
docker compose exec db psql -U postgres -d wump
```

**Dependencies not installing:**
```bash
# Update uv
pip install --upgrade uv

# Clear cache and reinstall
rm -rf .venv
uv sync
```

**Can't access API:**
```bash
# Check if container is running
docker compose ps

# Check API logs for errors
docker compose logs api

# Try rebuilding
docker compose down
docker compose up --build
```

### Next Steps

Once the basic setup works:

1. **Database Schema**: Implement models in `app/models/`
2. **Migrations**: Setup Alembic and create initial migration
3. **First Endpoint**: Add a package lookup endpoint
4. **Tests**: Write integration tests
5. **GitHub Provider**: Implement GitHub data fetching

See [SPRINT.md](SPRINT.md) for prioritized tasks!
