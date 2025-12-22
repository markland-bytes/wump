#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_OWNER="markland-bytes"
REPO_NAME="wump"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   GitHub Issues + Projects Setup for wump${NC}"
echo -e "${BLUE}   Repository: ${REPO_OWNER}/${REPO_NAME}${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v gh &> /dev/null; then
    echo -e "${RED}✗ GitHub CLI (gh) is not installed${NC}"
    echo -e "  Install: https://cli.github.com/"
    exit 1
fi
echo -e "${GREEN}✓ GitHub CLI found${NC}"

if ! gh auth status &> /dev/null; then
    echo -e "${RED}✗ Not authenticated with GitHub${NC}"
    echo -e "  Run: gh auth login"
    exit 1
fi
echo -e "${GREEN}✓ GitHub authentication verified${NC}"
echo

# Confirm repository
echo -e "${YELLOW}This script will create:${NC}"
echo "  • 15 labels (phases, priorities, categories)"
echo "  • 9 Phase 1 issues with full descriptions"
echo "  • Optionally create a project board"
echo
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo
echo -e "${BLUE}━━━ Step 1: Creating Labels ━━━${NC}"

# Phase Labels
gh label create "phase-1" --description "Foundation" --color "0052CC" --force 2>/dev/null && echo -e "${GREEN}✓${NC} phase-1" || echo -e "${YELLOW}↻${NC} phase-1 (already exists)"
gh label create "phase-2" --description "Core API" --color "0747A6" --force 2>/dev/null && echo -e "${GREEN}✓${NC} phase-2" || echo -e "${YELLOW}↻${NC} phase-2 (already exists)"
gh label create "phase-3" --description "Background Jobs" --color "172B4D" --force 2>/dev/null && echo -e "${GREEN}✓${NC} phase-3" || echo -e "${YELLOW}↻${NC} phase-3 (already exists)"
gh label create "phase-4" --description "IaC & Deployment" --color "6554C0" --force 2>/dev/null && echo -e "${GREEN}✓${NC} phase-4" || echo -e "${YELLOW}↻${NC} phase-4 (already exists)"
gh label create "phase-5" --description "Open Source Prep" --color "00875A" --force 2>/dev/null && echo -e "${GREEN}✓${NC} phase-5" || echo -e "${YELLOW}↻${NC} phase-5 (already exists)"

# Priority Labels
gh label create "priority-critical" --description "Blocking work" --color "DE350B" --force 2>/dev/null && echo -e "${GREEN}✓${NC} priority-critical" || echo -e "${YELLOW}↻${NC} priority-critical (already exists)"
gh label create "priority-high" --description "Important" --color "FF8B00" --force 2>/dev/null && echo -e "${GREEN}✓${NC} priority-high" || echo -e "${YELLOW}↻${NC} priority-high (already exists)"
gh label create "priority-medium" --description "Normal" --color "FFAB00" --force 2>/dev/null && echo -e "${GREEN}✓${NC} priority-medium" || echo -e "${YELLOW}↻${NC} priority-medium (already exists)"
gh label create "priority-low" --description "Nice to have" --color "FFC400" --force 2>/dev/null && echo -e "${GREEN}✓${NC} priority-low" || echo -e "${YELLOW}↻${NC} priority-low (already exists)"

# Category Labels
gh label create "task" --description "General task" --color "d4c5f9" --force 2>/dev/null && echo -e "${GREEN}✓${NC} task" || echo -e "${YELLOW}↻${NC} task (already exists)"
gh label create "database" --description "Database related" --color "5319e7" --force 2>/dev/null && echo -e "${GREEN}✓${NC} database" || echo -e "${YELLOW}↻${NC} database (already exists)"
gh label create "api" --description "API endpoints" --color "e99695" --force 2>/dev/null && echo -e "${GREEN}✓${NC} api" || echo -e "${YELLOW}↻${NC} api (already exists)"
gh label create "infrastructure" --description "DevOps/infrastructure" --color "c5def5" --force 2>/dev/null && echo -e "${GREEN}✓${NC} infrastructure" || echo -e "${YELLOW}↻${NC} infrastructure (already exists)"
gh label create "testing" --description "Test related" --color "bfdadc" --force 2>/dev/null && echo -e "${GREEN}✓${NC} testing" || echo -e "${YELLOW}↻${NC} testing (already exists)"
gh label create "documentation" --description "Documentation" --color "0075ca" --force 2>/dev/null && echo -e "${GREEN}✓${NC} documentation" || echo -e "${YELLOW}↻${NC} documentation (already exists)"
gh label create "provider" --description "Data provider related" --color "1d76db" --force 2>/dev/null && echo -e "${GREEN}✓${NC} provider" || echo -e "${YELLOW}↻${NC} provider (already exists)"

echo
echo -e "${BLUE}━━━ Step 2: Creating Phase 1 Issues ━━━${NC}"

# Issue 1: Database Models
echo -e "${YELLOW}Creating Issue #1: Database Models Implementation...${NC}"
gh issue create \
  --title "[Phase 1] Implement SQLAlchemy database models" \
  --label "phase-1,priority-critical,task,database" \
  --body "## Description
Implement SQLAlchemy 2.0+ database models for core entities.

## Acceptance Criteria
- [ ] Install SQLAlchemy 2.0+ with asyncpg
- [ ] Create \`app/models/package.py\` with Package model
- [ ] Create \`app/models/organization.py\` with Organization model
- [ ] Create \`app/models/repository.py\` with Repository model
- [ ] Create \`app/models/dependency.py\` with Dependency model (junction table)
- [ ] Create \`app/models/api_key.py\` with APIKey model
- [ ] Add proper relationships between models
- [ ] Add indexes as specified in architecture doc
- [ ] Models pass mypy type checking

## Technical Notes
- Use SQLAlchemy 2.0 async patterns
- See \`md_docs/architecture.md\` Section 3.2.1 for schema details
- Use proper UUID primary keys
- Add \`created_at\` and \`updated_at\` timestamps

## Estimate
4-6 hours" && echo -e "${GREEN}✓${NC} Issue #1 created"

# Issue 2: Alembic
echo -e "${YELLOW}Creating Issue #2: Alembic Migrations...${NC}"
gh issue create \
  --title "[Phase 1] Setup Alembic for database migrations" \
  --label "phase-1,priority-critical,task,database" \
  --body "## Description
Setup Alembic for managing database schema migrations.

## Acceptance Criteria
- [ ] Install Alembic
- [ ] Create \`alembic.ini\` configuration
- [ ] Create \`alembic/\` directory structure
- [ ] Configure Alembic to use async SQLAlchemy
- [ ] Create initial migration for all models
- [ ] Test migration up/down
- [ ] Add migration commands to README
- [ ] Update docker-compose to run migrations on startup

## Technical Notes
- Use async engine from SQLAlchemy
- Environment should pull DATABASE_URL from settings
- Migration should be idempotent

## Blockers
- Depends on #1 (Database Models)

## Estimate
2-3 hours" && echo -e "${GREEN}✓${NC} Issue #2 created"

# Issue 3: Database Pool
echo -e "${YELLOW}Creating Issue #3: Database Connection Pool...${NC}"
gh issue create \
  --title "[Phase 1] Setup database connection pool and session management" \
  --label "phase-1,priority-critical,task,database,infrastructure" \
  --body "## Description
Create database connection pool and session management for async SQLAlchemy.

## Acceptance Criteria
- [ ] Create \`app/core/database.py\` with async engine
- [ ] Configure connection pooling (size, overflow, timeouts)
- [ ] Create async session factory
- [ ] Add database dependency for FastAPI routes
- [ ] Implement connection lifecycle in app lifespan
- [ ] Add database health check to \`/health\` endpoint
- [ ] Handle connection errors gracefully
- [ ] Add logging for connection pool stats

## Technical Notes
\`\`\`python
# app/core/database.py should export:
# - engine: AsyncEngine
# - async_session_maker: async_sessionmaker
# - get_db() -> AsyncGenerator[AsyncSession, None]
\`\`\`

## Blockers
- Depends on #1 (Database Models)

## Estimate
3-4 hours" && echo -e "${GREEN}✓${NC} Issue #3 created"

# Issue 4: Valkey
echo -e "${YELLOW}Creating Issue #4: Valkey Connection...${NC}"
gh issue create \
  --title "[Phase 1] Setup Valkey connection and caching utilities" \
  --label "phase-1,priority-high,task,infrastructure" \
  --body "## Description
Setup Valkey (Redis-compatible) connection for caching.

## Acceptance Criteria
- [ ] Install redis-py (supports Valkey)
- [ ] Create \`app/core/cache.py\` with connection pool
- [ ] Add cache lifecycle in app lifespan
- [ ] Create helper functions for get/set/delete
- [ ] Add Valkey health check to \`/health\` endpoint
- [ ] Configure connection timeouts and retries
- [ ] Add cache stats to health endpoint

## Technical Notes
- Use connection pooling
- Handle connection failures gracefully
- Return None instead of raising on cache misses

## Estimate
2-3 hours" && echo -e "${GREEN}✓${NC} Issue #4 created"

# Issue 5: Health Check
echo -e "${YELLOW}Creating Issue #5: Enhanced Health Check...${NC}"
gh issue create \
  --title "[Phase 1] Enhance health check with DB and cache status" \
  --label "phase-1,priority-medium,task,api" \
  --body "## Description
Enhance the \`/health\` endpoint to include database and cache status.

## Acceptance Criteria
- [ ] Health check pings PostgreSQL
- [ ] Health check pings Valkey
- [ ] Return detailed status for each component
- [ ] Add response time for each check
- [ ] Return 200 if all healthy, 503 if any unhealthy
- [ ] Add version info and environment

## Expected Response
\`\`\`json
{
  \"status\": \"healthy\",
  \"service\": \"wump-api\",
  \"version\": \"0.1.0\",
  \"environment\": \"development\",
  \"checks\": {
    \"database\": {
      \"status\": \"healthy\",
      \"response_time_ms\": 12
    },
    \"cache\": {
      \"status\": \"healthy\",
      \"response_time_ms\": 3
    }
  }
}
\`\`\`

## Blockers
- Depends on #3 (Database Pool)
- Depends on #4 (Valkey Connection)

## Estimate
1-2 hours" && echo -e "${GREEN}✓${NC} Issue #5 created"

# Issue 6: Request ID
echo -e "${YELLOW}Creating Issue #6: Request ID Middleware...${NC}"
gh issue create \
  --title "[Phase 1] Add request ID middleware for tracing" \
  --label "phase-1,priority-medium,task,infrastructure" \
  --body "## Description
Add middleware to generate unique request IDs for tracking requests through logs.

## Acceptance Criteria
- [ ] Create \`app/core/middleware.py\`
- [ ] Generate UUID for each request
- [ ] Add request ID to response headers (\`X-Request-ID\`)
- [ ] Add request ID to structlog context
- [ ] Log request start/end with request ID
- [ ] Add request duration to logs

## Technical Notes
- Use \`uuid.uuid4()\` for IDs
- Store in context var for access in all logs
- Should work with structlog's \`merge_contextvars\`

## Estimate
1-2 hours" && echo -e "${GREEN}✓${NC} Issue #6 created"

# Issue 7: Repository Pattern
echo -e "${YELLOW}Creating Issue #7: Base Repository Pattern...${NC}"
gh issue create \
  --title "[Phase 1] Create base repository pattern for data access" \
  --label "phase-1,priority-medium,task,database" \
  --body "## Description
Create base repository class with common CRUD operations.

## Acceptance Criteria
- [ ] Create \`app/repositories/base.py\`
- [ ] Implement generic \`create()\`, \`get()\`, \`update()\`, \`delete()\`
- [ ] Implement \`list()\` with pagination
- [ ] Add proper type hints
- [ ] Add logging for all operations
- [ ] Handle database errors gracefully
- [ ] Write unit tests

## Technical Notes
- Use Python generics for type safety
- Repository should take AsyncSession in constructor
- Methods should be async

## Blockers
- Depends on #3 (Database Pool)

## Estimate
3-4 hours" && echo -e "${GREEN}✓${NC} Issue #7 created"

# Issue 8: Testing
echo -e "${YELLOW}Creating Issue #8: Testing Infrastructure...${NC}"
gh issue create \
  --title "[Phase 1] Setup comprehensive testing infrastructure" \
  --label "phase-1,priority-high,task,testing" \
  --body "## Description
Setup pytest with database fixtures and test utilities.

## Acceptance Criteria
- [ ] Configure pytest.ini with proper settings
- [ ] Create test database configuration
- [ ] Create async database fixtures
- [ ] Create factory fixtures for models
- [ ] Setup pytest-cov for coverage reporting
- [ ] Add GitHub Actions CI workflow
- [ ] Configure coverage threshold (>80%)
- [ ] Add test commands to README

## Technical Notes
- Use separate test database
- Fixtures should create/drop tables per test session
- Use \`pytest-asyncio\` for async tests
- Add \`conftest.py\` with shared fixtures

## Estimate
4-5 hours" && echo -e "${GREEN}✓${NC} Issue #8 created"

# Issue 9: Developer Experience
echo -e "${YELLOW}Creating Issue #9: Developer Experience...${NC}"
gh issue create \
  --title "[Phase 1] Add developer tooling and documentation" \
  --label "phase-1,priority-low,task,documentation" \
  --body "## Description
Improve developer experience with better tooling.

## Acceptance Criteria
- [ ] Add pgAdmin or Adminer to docker-compose
- [ ] Create database seed script
- [ ] Add Makefile with common commands
- [ ] Document database schema in README
- [ ] Add VS Code launch.json for debugging
- [ ] Add API examples to documentation
- [ ] Create troubleshooting guide

## Technical Notes
- Keep Makefile simple (or use justfile)
- Seed script should be idempotent

## Estimate
3-4 hours" && echo -e "${GREEN}✓${NC} Issue #9 created"

echo
echo -e "${BLUE}━━━ Step 3: Create Project Board (Optional) ━━━${NC}"
echo
read -p "Create project board? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Creating project board...${NC}"
    if gh project create --owner "$REPO_OWNER" --title "wump Development" --format table &> /dev/null; then
        echo -e "${GREEN}✓${NC} Project board created"
        echo -e "  View at: https://github.com/$REPO_OWNER/$REPO_NAME/projects"
        echo
        echo -e "${YELLOW}Note: You'll need to manually add issues to the project via the web UI${NC}"
        echo -e "  1. Go to each issue"
        echo -e "  2. Click 'Add to projects' in the right sidebar"
        echo -e "  3. Select 'wump Development'"
    else
        echo -e "${YELLOW}⚠${NC}  Project creation may have failed or already exists"
        echo -e "  Create manually at: https://github.com/$REPO_OWNER/$REPO_NAME/projects"
    fi
else
    echo -e "${BLUE}ℹ${NC}  Skipped project creation"
    echo -e "  Create manually at: https://github.com/$REPO_OWNER/$REPO_NAME/projects"
fi

echo
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo -e "${YELLOW}Summary:${NC}"
echo "  • 15 labels created"
echo "  • 9 Phase 1 issues created"
echo
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. View issues: gh issue list"
echo "  2. Or visit: https://github.com/$REPO_OWNER/$REPO_NAME/issues"
echo "  3. Create project board if not done: https://github.com/$REPO_OWNER/$REPO_NAME/projects"
echo "  4. Start with Issue #1: Database Models"
echo
echo -e "${GREEN}Happy coding! 🚀${NC}"
