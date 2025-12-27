# Troubleshooting Guide

Common issues and solutions for developing with wump.

## Table of Contents

- [Docker Issues](#docker-issues)
- [Database Issues](#database-issues)
- [Cache Issues](#cache-issues)
- [Development Issues](#development-issues)
- [Testing Issues](#testing-issues)
- [Migration Issues](#migration-issues)
- [Performance Issues](#performance-issues)

---

## Docker Issues

### Port Already in Use

**Problem:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:8000: bind: address already in use
```

**Solution:**
```bash
# Find process using the port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or use a different port
docker compose down
docker compose up -d

# Or modify docker-compose.yml to use different port:
# ports:
#   - "8001:8000"
```

### Container Won't Start

**Problem:**
Container immediately exits with error.

**Solution:**
```bash
# Check container logs
docker compose logs api

# Check for syntax errors in docker-compose.yml
docker compose config

# Rebuild containers from scratch
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Volume Permission Issues

**Problem:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Fix volume ownership (Linux)
sudo chown -R $USER:$USER ./api

# Or run containers as current user (add to docker-compose.yml):
# user: "${UID}:${GID}"

# Reset volumes completely
docker compose down -v
docker compose up -d
```

### Out of Disk Space

**Problem:**
```
no space left on device
```

**Solution:**
```bash
# Clean up Docker resources
docker system prune -a --volumes

# Check disk usage
docker system df

# Remove specific volumes
docker volume ls
docker volume rm wump_postgres_data
```

---

## Database Issues

### Connection Refused

**Problem:**
```
ConnectionRefusedError: [Errno 111] Connection refused
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution:**
```bash
# Verify database container is running
docker compose ps

# Check database logs
docker compose logs db

# Restart database
docker compose restart db

# Wait for database to be ready
docker compose up -d db
sleep 5  # Give it time to start

# Test connection manually
docker compose exec db psql -U postgres -d wump -c "SELECT 1;"
```

### Database Connection Pool Exhausted

**Problem:**
```
TimeoutError: QueuePool limit of size 20 overflow 10 reached
```

**Solution:**
```bash
# Increase pool size in api/.env
DATABASE_POOL_SIZE=30
DATABASE_MAX_OVERFLOW=20

# Restart API
docker compose restart api

# Or reduce concurrent connections in your code
# Check for connection leaks (unclosed sessions)
```

### Migration Errors

**Problem:**
```
alembic.util.exc.CommandError: Target database is not up to date
```

**Solution:**
```bash
# Check current migration version
docker compose exec api uv run alembic current

# View migration history
docker compose exec api uv run alembic history

# Apply pending migrations
docker compose exec api uv run alembic upgrade head

# If migrations are stuck, downgrade and reapply
docker compose exec api uv run alembic downgrade -1
docker compose exec api uv run alembic upgrade head
```

### Database Locked (SQLite Testing)

**Problem:**
```
sqlite3.OperationalError: database is locked
```

**Solution:**
```bash
# This happens when tests run in parallel with SQLite
# Disable parallel execution in pytest.ini or:
uv run pytest -n 0  # Disable parallelism

# Or use PostgreSQL for testing:
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/wump_test pytest
```

### Data Inconsistency

**Problem:**
Unexpected data or missing relationships.

**Solution:**
```bash
# Reset database completely
docker compose down -v
docker compose up -d

# Wait for migrations
docker compose logs -f api

# Reseed database
docker compose exec api uv run python seed.py

# Verify data
docker compose exec db psql -U postgres -d wump -c "SELECT COUNT(*) FROM organizations;"
```

---

## Cache Issues

### Valkey Connection Timeout

**Problem:**
```
redis.exceptions.ConnectionError: Error connecting to Valkey
redis.exceptions.TimeoutError: Timeout reading from socket
```

**Solution:**
```bash
# Check if Valkey is running
docker compose ps valkey

# Check Valkey logs
docker compose logs valkey

# Restart Valkey
docker compose restart valkey

# Test connection manually
docker compose exec valkey valkey-cli ping
# Expected: PONG

# Flush cache if needed
docker compose exec valkey valkey-cli FLUSHALL
```

### Cache Data Not Updating

**Problem:**
Data changes aren't reflected in API responses.

**Solution:**
```bash
# Clear cache
docker compose exec valkey valkey-cli FLUSHALL

# Or clear specific keys
docker compose exec valkey valkey-cli DEL "cache:*"

# Check TTL settings in code
# Verify cache invalidation logic
```

### FakeRedis Issues (Testing)

**Problem:**
```
ImportError: cannot import name 'FakeAsyncRedis' from 'fakeredis'
```

**Solution:**
```bash
# Ensure fakeredis is installed
cd api
uv sync --all-extras

# Or install manually
uv add --dev fakeredis

# Check if VALKEY_URL is unset for tests
# Tests should use FakeRedis when VALKEY_URL is empty
```

---

## Development Issues

### Import Errors

**Problem:**
```
ModuleNotFoundError: No module named 'app'
ImportError: attempted relative import with no known parent package
```

**Solution:**
```bash
# Ensure you're in the api/ directory
cd api

# Reinstall dependencies
uv sync

# Check PYTHONPATH (should include src/)
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run with proper module path
uv run python -m pytest  # Not just 'pytest'
uv run uvicorn src.app.main:app  # Not 'app.main:app'
```

### Type Checking Failures

**Problem:**
```
error: Incompatible types in assignment
error: Argument 1 has incompatible type
```

**Solution:**
```bash
# Run mypy with verbose output
cd api
uv run mypy src/app/ --show-error-codes

# Check specific file
uv run mypy src/app/models/organization.py

# Ignore specific errors (use sparingly)
# Add to pyproject.toml:
# [[tool.mypy.overrides]]
# module = "problematic_module.*"
# ignore_errors = true

# Update type stubs
uv sync
```

### Linting Errors

**Problem:**
```
ruff: F401 [*] `Organization` imported but unused
ruff: E501 Line too long (120 > 100)
```

**Solution:**
```bash
# Auto-fix linting issues
cd api
uv run ruff check --fix src/app/

# Format code
uv run ruff format src/app/

# Check specific file
uv run ruff check src/app/models/organization.py

# Ignore specific rules (add to pyproject.toml)
# [tool.ruff]
# ignore = ["E501"]  # Ignore line length
```

### Environment Variables Not Loading

**Problem:**
Configuration values are default/None when they should be set.

**Solution:**
```bash
# Verify .env file exists
ls -la api/.env

# Check file contents
cat api/.env

# Ensure no quotes around values (unless needed)
# Correct:   DATABASE_URL=postgresql://...
# Incorrect: DATABASE_URL="postgresql://..."

# Restart containers to pick up changes
docker compose restart api

# Debug: Print settings
docker compose exec api uv run python -c "from src.app.core.config import settings; print(settings.database_url)"
```

---

## Testing Issues

### Tests Failing Locally but Passing in CI

**Problem:**
Tests pass in GitHub Actions but fail on your machine.

**Solution:**
```bash
# Use Docker test service (mirrors CI environment)
docker compose run --rm test

# Or manually replicate CI environment
cd api
export ENVIRONMENT=testing
export LOG_LEVEL=WARNING
export OTEL_ENABLED=false
unset DATABASE_URL  # Use SQLite in-memory
unset VALKEY_URL    # Use FakeRedis
uv run pytest
```

### Coverage Below Threshold

**Problem:**
```
FAIL Required test coverage of 80% not reached. Total coverage: 75.32%
```

**Solution:**
```bash
# View coverage report
cd api
uv run pytest --cov=src/app --cov-report=html
open htmlcov/index.html

# Find uncovered lines
uv run pytest --cov=src/app --cov-report=term-missing

# Add tests for uncovered code
# Focus on business logic, not trivial getters/setters
```

### Async Test Errors

**Problem:**
```
RuntimeError: Task attached to a different loop
pytest.PytestUnraisableExceptionWarning: Exception ignored in: <coroutine object ...>
```

**Solution:**
```bash
# Ensure pytest-asyncio is installed
cd api
uv sync

# Use @pytest.mark.asyncio decorator
# In test file:
# @pytest.mark.asyncio
# async def test_something():
#     ...

# Check for unclosed async resources
# Always use 'async with' for sessions:
# async with get_db() as session:
#     ...
```

### Fixtures Not Working

**Problem:**
```
fixture 'db_session' not found
```

**Solution:**
```bash
# Ensure conftest.py is in test directory
ls -la api/src/tests/conftest.py

# Check fixture scope
# @pytest.fixture  # function scope (default)
# @pytest.fixture(scope="session")  # session scope

# Verify fixture is imported
# Fixtures in conftest.py are auto-discovered

# Run tests with verbose output
uv run pytest -v src/tests/test_main.py
```

---

## Migration Issues

### Cannot Create Migration

**Problem:**
```
ERROR [alembic.env] Can't locate revision identified by '...'
```

**Solution:**
```bash
# Check migration history
cd api
uv run alembic history

# Ensure database is at latest version
uv run alembic current
uv run alembic upgrade head

# Create new migration
uv run alembic revision -m "describe changes"

# Edit migration file in alembic/versions/
# Test migration
uv run alembic upgrade head
uv run alembic downgrade -1
```

### Migration Order Issues

**Problem:**
```
alembic.util.exc.CommandError: Can't locate revision XXX
```

**Solution:**
```bash
# Migrations must form a chain
# Check migration files for 'down_revision' values

# Fix: Edit migration file to point to correct parent
# down_revision = 'previous_revision_id'

# Rebuild migration chain
uv run alembic history --verbose

# Nuclear option: Reset migrations (development only!)
docker compose down -v
rm -rf api/alembic/versions/*.py  # DANGER!
# Recreate initial migration
```

### Cannot Downgrade Migration

**Problem:**
```
NotImplementedError: downgrade() not implemented
```

**Solution:**
```bash
# All migrations should have downgrade() implemented
# Edit migration file and add downgrade logic

# For CREATE TABLE:
# def upgrade():
#     op.create_table('users', ...)
# def downgrade():
#     op.drop_table('users')

# For ALTER TABLE:
# def upgrade():
#     op.add_column('users', ...)
# def downgrade():
#     op.drop_column('users', 'column_name')
```

---

## Performance Issues

### Slow API Responses

**Problem:**
Endpoints taking > 1 second to respond.

**Solution:**
```bash
# Check Jaeger traces
# Visit: http://localhost:16686
# Find slow operations

# Enable SQL query logging
# In api/.env:
# Add to database.py: echo=True in create_async_engine()

# Add database indexes
# Check EXPLAIN ANALYZE for slow queries

# Increase connection pool
# DATABASE_POOL_SIZE=30
# DATABASE_MAX_OVERFLOW=20

# Add caching for expensive queries
```

### Memory Usage Growing

**Problem:**
API container memory usage continuously increases.

**Solution:**
```bash
# Check for connection leaks
# Ensure all async sessions are closed:
# async with get_db() as session:
#     ...

# Check for cache growth
docker compose exec valkey valkey-cli INFO memory
docker compose exec valkey valkey-cli FLUSHALL

# Restart API periodically (workaround)
docker compose restart api

# Monitor with docker stats
docker stats wump-api-1
```

### Database Query Performance

**Problem:**
Queries taking > 100ms.

**Solution:**
```bash
# Check slow query log
docker compose logs db | grep "duration:"

# Analyze specific query
docker compose exec db psql -U postgres -d wump
# \timing on
# EXPLAIN ANALYZE SELECT ...;

# Add indexes (in migration)
# CREATE INDEX idx_name ON table(column);

# Use eager loading for relationships
# query.options(joinedload(Organization.repositories))

# Add pagination
# .limit(50).offset(0)
```

---

## Common Error Messages

### "RuntimeError: Event loop is closed"

**Cause:** Async resources not properly cleaned up.

**Fix:**
```python
# Use async context managers
async with async_session_maker() as session:
    # Your code here
    pass

# Don't forget to await close()
await engine.dispose()
```

### "AssertionError: Task was destroyed but it is pending!"

**Cause:** Coroutine not awaited.

**Fix:**
```python
# BAD
result = some_async_function()  # Returns coroutine

# GOOD
result = await some_async_function()
```

### "sqlalchemy.exc.IntegrityError: duplicate key value"

**Cause:** Unique constraint violation.

**Fix:**
```python
# Check if record exists before creating
existing = await session.execute(
    select(Organization).where(Organization.name == name)
)
if existing.scalar_one_or_none():
    # Update instead of create
    pass
else:
    # Create new record
    pass
```

### "OSError: [Errno 24] Too many open files"

**Cause:** File descriptor limit reached.

**Fix:**
```bash
# Increase file descriptor limit
ulimit -n 4096

# Check current limit
ulimit -n

# Or add to ~/.bashrc:
# ulimit -n 4096

# Restart Docker
```

---

## Getting Help

If you're still stuck after trying these solutions:

1. **Check Logs:**
   ```bash
   docker compose logs --tail=100 api
   docker compose logs --tail=100 db
   docker compose logs --tail=100 valkey
   ```

2. **Search Issues:**
   - GitHub: https://github.com/markland-bytes/wump/issues
   - Stack Overflow: Tag `wump` or `fastapi`

3. **Ask for Help:**
   - Create a new issue with:
     - Steps to reproduce
     - Error message
     - Logs
     - Environment (OS, Docker version)

4. **Documentation:**
   - [ARCHITECTURE.md](ARCHITECTURE.md)
   - [DEVELOPMENT.md](DEVELOPMENT.md)
   - [api/README.md](../api/README.md)

---

## Debug Mode

Enable verbose logging for troubleshooting:

```bash
# In api/.env
LOG_LEVEL=DEBUG
OTEL_ENABLED=true

# Restart API
docker compose restart api

# View detailed logs
docker compose logs -f api

# Check Jaeger for traces
# http://localhost:16686
```

---

**Last Updated:** 2025-12-26
