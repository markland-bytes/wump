# Development Guide

This guide covers the development workflow, conventions, and best practices for wump.

## Table of Contents

- [Quick Start](#quick-start)
- [Git Workflow](#git-workflow)
- [Branch Naming](#branch-naming)
- [Commit Messages](#commit-messages)
- [Pull Requests](#pull-requests)
- [GitHub Issue Linking](#github-issue-linking)
- [Testing](#testing)
- [Code Style](#code-style)
- [Database Migrations](#database-migrations)

---

## Quick Start

For first-time setup, see [QUICKSTART.md](QUICKSTART.md).

**Daily development:**
```bash
# Start services
docker compose up

# Run tests
uv run pytest

# Type checking
uv run mypy app/

# Linting
uv run ruff check app/
```

---

## Git Workflow

We use a **feature branch workflow** with `main` as the primary branch.

### Branch Strategy

```
main (protected, always deployable)
  ├── feature/1-database-models
  ├── feature/2-alembic-setup
  ├── feature/3-db-pool
  └── hotfix/fix-health-check
```

**Branch types:**
- `feature/*` - New features and enhancements (most common)
- `fix/*` - Bug fixes
- `hotfix/*` - Urgent production fixes
- `docs/*` - Documentation only changes
- `refactor/*` - Code refactoring without feature changes

---

## Branch Naming

**Format:** `<type>/<issue-number>-<short-description>`

**Examples:**
```bash
feature/1-database-models
feature/2-alembic-setup
fix/15-valkey-connection-timeout
docs/20-api-examples
refactor/8-repository-pattern
```

**Why this format?**
- ✅ GitHub auto-links branches to issues (e.g., `1-database-models` → Issue #1)
- ✅ Clear context at a glance
- ✅ Easy to find in `git branch` list
- ✅ Groups related work by type

**Creating a branch:**
```bash
# Always branch from latest main
git checkout main
git pull origin main
git checkout -b feature/1-database-models
```

---

## Commit Messages

### Format

```
<type>: <subject>

[optional body]

[optional footer]
```

### Types

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks (deps, config)
- `perf:` - Performance improvements

### Examples

**Simple:**
```bash
git commit -m "feat: add Package model with UUID primary key"
git commit -m "fix: handle null valkey connection gracefully"
git commit -m "docs: update database schema in README"
```

**With body:**
```bash
git commit -m "feat: add database connection pool

- Configure async SQLAlchemy engine
- Add connection pooling with size limits
- Implement get_db() dependency for FastAPI
- Add database health check

Closes #3"
```

**With issue reference:**
```bash
git commit -m "feat: add Organization model (#1)"
git commit -m "fix: valkey connection timeout

Fixes #15"
```

---

## Pull Requests

### Creating a PR

**After finishing feature work:**
```bash
# Push your branch
git push origin feature/1-database-models

# Create PR via CLI
gh pr create \
  --title "[Phase 1] Implement SQLAlchemy database models" \
  --body "Closes #1

## Summary
Implements all core database models with SQLAlchemy 2.0.

## Changes
- ✅ Package, Organization, Repository models
- ✅ Dependency junction table
- ✅ APIKey model for authentication
- ✅ Proper relationships and indexes
- ✅ Passes mypy type checking

## Testing
- [ ] All models tested
- [ ] Migrations run successfully
- [ ] Type checking passes"

# Or create via web UI
# gh pr create --web
```

### PR Template

Title format: `[Phase X] Brief description`

Use the closing keywords in PR description:
- `Closes #1` - Links and closes issue when PR merges
- `Fixes #15` - Same as Closes
- `Resolves #20` - Same as Closes
- `Relates to #5` - Links without closing

### Review Process

Even as a solo developer, use PRs for self-review:

1. **Create PR** - Push branch and open PR
2. **Self-review** - Read the diff in GitHub's web UI
3. **Check CI** - Wait for tests to pass (once CI is set up)
4. **Merge** - Use squash or merge strategy

**Merge strategies:**
```bash
# Squash (clean history, recommended for small features)
gh pr merge --squash

# Merge (preserve all commits, good for larger features)
gh pr merge --merge

# Rebase (linear history, advanced)
gh pr merge --rebase
```

**After merge:**
```bash
# Clean up local branch
git checkout main
git pull origin main
git branch -d feature/1-database-models
```

---

## GitHub Issue Linking

GitHub automatically links branches, commits, and PRs to issues.

### Branch Names → Issues

These branch names auto-link to Issue #1:
- ✅ `feature/1-database-models`
- ✅ `1-database-models`
- ✅ `feature/#1-models`

GitHub shows linked branches in the issue sidebar.

### Commit Messages → Issues

Reference issues in commit messages:

**Simple mention (creates link):**
```bash
git commit -m "feat: add Package model (#1)"
```

**Closing keywords (closes issue when merged to main):**
```bash
git commit -m "feat: complete database models

Closes #1"

# Also works:
# Fixes #1
# Resolves #1
# Closes: #1
```

**Multiple issues:**
```bash
git commit -m "feat: add health checks

Closes #3
Closes #4"
```

### PR Descriptions → Issues

**Recommended format:**
```markdown
Closes #1

## Summary
Brief description of changes

## Changes
- Change 1
- Change 2

## Testing
- [x] Tests pass
- [x] Manual testing complete
```

**Multiple issues in one PR:**
```markdown
This PR implements the database foundation.

Closes #1
Closes #2
Relates to #3 (partial implementation)
```

### Reference Patterns

All these patterns work in commits, PRs, and issue comments:

| Pattern | Effect |
|---------|--------|
| `#1` | Link to Issue #1 |
| `closes #1` | Link + auto-close when merged |
| `fixes #1` | Link + auto-close when merged |
| `resolves #1` | Link + auto-close when merged |
| `GH-1` | Link to Issue #1 (alternative) |
| `markland-bytes/wump#1` | Link to issue in specific repo |

**Case insensitive:** `Closes #1`, `closes #1`, `CLOSES #1` all work.

---

## Testing

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=app --cov-report=term-missing

# Specific test file
uv run pytest tests/test_models.py

# Specific test function
uv run pytest tests/test_models.py::test_package_model

# Watch mode (requires pytest-watch)
uv run ptw
```

### Test Requirements

**Before merging a PR:**
- ✅ All tests pass
- ✅ Coverage > 80% for new code
- ✅ Type checking passes (`mypy app/`)
- ✅ Linting passes (`ruff check app/`)

**Test structure:**
```python
# tests/test_models.py
import pytest
from app.models.package import Package

@pytest.mark.asyncio
async def test_package_creation(db_session):
    """Test creating a package model."""
    package = Package(
        name="fastapi",
        ecosystem="pypi",
        latest_version="0.115.0"
    )
    db_session.add(package)
    await db_session.commit()
    
    assert package.id is not None
    assert package.created_at is not None
```

---

## Code Style

### Python Style

We use **Ruff** for linting and formatting.

**Configuration:** See `pyproject.toml` → `[tool.ruff]`

**Key conventions:**
- Line length: 100 characters
- Strings: Double quotes preferred
- Imports: Sorted with isort
- Type hints: Required for all functions
- Docstrings: Google style

**Running formatters:**
```bash
# Check for issues
uv run ruff check app/

# Auto-fix issues
uv run ruff check --fix app/

# Format code
uv run ruff format app/
```

### Type Checking

We use **mypy** for static type checking.

**Configuration:** See `pyproject.toml` → `[tool.mypy]`

**Running mypy:**
```bash
# Check all code
uv run mypy app/

# Check specific file
uv run mypy app/models/package.py
```

**Type hint examples:**
```python
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

async def get_package(
    db: AsyncSession,
    package_id: str
) -> Optional[Package]:
    """Get a package by ID."""
    result = await db.execute(
        select(Package).where(Package.id == package_id)
    )
    return result.scalar_one_or_none()
```

---

## Database Migrations

### Creating Migrations

```bash
# Auto-generate migration from model changes
uv run alembic revision --autogenerate -m "add package model"

# Create empty migration (manual)
uv run alembic revision -m "add custom index"
```

### Running Migrations

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Show current version
uv run alembic current

# Show migration history
uv run alembic history
```

### Migration Best Practices

1. **Review auto-generated migrations** - Alembic sometimes misses things
2. **Test up and down** - Always test both directions
3. **Keep migrations small** - One logical change per migration
4. **Name descriptively** - `add_package_name_index` not `migration_1`
5. **Never edit merged migrations** - Create a new migration instead

**Example migration:**
```python
"""add package name index

Revision ID: abc123
Created: 2025-12-22 10:30:00
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.create_index(
        'ix_packages_name',
        'packages',
        ['name'],
        unique=False
    )

def downgrade() -> None:
    op.drop_index('ix_packages_name', table_name='packages')
```

---

## Common Workflows

### Starting a New Issue

```bash
# 1. Sync with main
git checkout main
git pull origin main

# 2. Create feature branch
git checkout -b feature/5-enhanced-health-check

# 3. Make changes, commit often
git add app/api/health.py
git commit -m "feat: add database health check (#5)"

git add app/api/health.py
git commit -m "feat: add valkey health check (#5)"

# 4. Push and create PR
git push origin feature/5-enhanced-health-check
gh pr create --title "[Phase 1] Enhanced health check" --body "Closes #5"

# 5. Merge PR (after review)
gh pr merge --squash

# 6. Clean up
git checkout main
git pull origin main
git branch -d feature/5-enhanced-health-check
```

### Updating from Main

If `main` has new commits while you're working:

```bash
# Option 1: Rebase (cleaner history)
git checkout feature/1-database-models
git fetch origin
git rebase origin/main

# Option 2: Merge (safer if you've pushed)
git checkout feature/1-database-models
git pull origin main
```

### Fixing Merge Conflicts

```bash
# After merge/rebase conflict
git status  # See conflicted files

# Edit conflicted files, look for:
# <<<<<<< HEAD
# your changes
# =======
# main's changes
# >>>>>>> main

# After resolving
git add <resolved-files>
git rebase --continue  # if rebasing
# or
git commit  # if merging
```

---

## Environment Variables

See `.env.example` for all available variables.

**Development defaults:**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://wump:wump@db:5432/wump

# Cache
VALKEY_URL=redis://valkey:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# External APIs (get your own keys)
LIBRARIES_IO_API_KEY=your_key_here
GITHUB_TOKEN=your_token_here
```

**Never commit secrets!** Use `.env` (gitignored) for local development.

---

## Getting Help

- **Documentation:** See `/md_docs/` for architecture and planning
- **Issues:** Check existing issues for similar problems
- **GitHub Discussions:** For questions and ideas (when enabled)
- **Project Board:** See https://github.com/markland-bytes/wump/projects

---

## Quick Reference

**Branch:**
```bash
git checkout -b feature/<issue>-<name>
```

**Commit:**
```bash
git commit -m "feat: description (#issue)"
```

**PR:**
```bash
gh pr create --title "[Phase X] Title" --body "Closes #issue"
```

**Merge:**
```bash
gh pr merge --squash
```

**Clean up:**
```bash
git checkout main && git pull && git branch -d feature/<branch>
```

---

## Phase-Specific Guidelines

### Phase 1: Foundation (Current)

**Focus:** Core infrastructure, no external APIs yet
**Testing:** Unit tests for models and repositories
**PRs:** Can be small (1-2 files per PR is fine)

### Phase 2+: Features

**Focus:** API endpoints, provider integrations
**Testing:** Integration tests, API endpoint tests
**PRs:** Should include tests and documentation

---

*Happy coding! 🚀*

For setup instructions, see [QUICKSTART.md](QUICKSTART.md).  
For daily workflow, see [GITHUB_WORKFLOW.md](GITHUB_WORKFLOW.md).  
For project planning, see [SPRINT.md](SPRINT.md) and [md_docs/](md_docs/).
