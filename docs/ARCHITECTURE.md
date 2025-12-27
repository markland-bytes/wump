# Software Architecture Document
## wump: Who's Using My Package?
### Dependency Sponsorship Discovery API

**Version:** 1.0  
**Date:** December 20, 2025  
**Status:** Draft

---

## 1. Architecture Overview

### 1.1 System Context
The Dependency Sponsorship Discovery API is a multi-tier application that aggregates and exposes data about software dependency usage across organizations. The system periodically collects data from external sources, processes it, stores it in a relational database, and serves it through a RESTful API.

### 1.2 Architecture Style
- **Layered Architecture** for the API service
- **Event-driven Architecture** for background job processing
- **Microservices-ready** with clear service boundaries

### 1.3 Open Source Architecture

This project follows an **open-core model**:

**Open Source (Public Repository):**
- All application code (API, workers, providers)
- Database schemas and migrations  
- Infrastructure as Code (OpenTofu templates)
- Documentation and deployment guides
- Testing infrastructure

**Managed Service (Hosted):**
- Production infrastructure (AWS)
- Populated database (millions of records)
- Continuous data ingestion pipeline
- Support and SLAs

**Key Principles:**
1. **No vendor lock-in**: Anyone can self-host with same functionality
2. **Transparent**: All business logic is visible and auditable
3. **Extensible**: Community can add data providers, features
4. **Portable**: Works on any infrastructure (AWS, GCP, Azure, on-prem)

### 1.4 Solo Developer Architecture Path

**Don't build the full architecture described below on day 1!** Here's the evolution:

#### Stage 1: MVP (Weeks 1-4)
```
Docker Compose (Local Dev)
├── Fastify API (single container)
├── Postgres 18
└── Valkey

Deploy to: Railway/Render (push to git = deploy)
Users: You + 10 friends
Traffic: 10 req/day
Cost: $0-20/month
```

#### Stage 2: Public Beta (Weeks 5-8)
```
Railway:
├── API Service (auto-scaled 1-3 instances)
├── Worker Service (Celery workers for background jobs)
├── Managed Postgres 18
└── Managed Valkey 8.x

Users: 100-1000
Traffic: 1K-10K req/day
Cost: $50-100/month (Railway pro plan)
```

#### Stage 3: Growth (Month 3+)
```
AWS ECS (migrate when Railway > $100/month)
├── ECS Fargate (API, 2-5 tasks)
├── ECS Fargate (Worker, 1-2 tasks)
├── RDS Postgres 18
├── ElastiCache Valkey
└── CloudWatch + X-Ray

Users: 1K-10K
Traffic: 100K-1M req/day
Cost: $200-500/month
```

#### Stage 4: Scale (Month 6+)
*Use the full architecture documented below*

**Key Insight**: Railway is perfect for solo developers and small teams. Only migrate to AWS when you're paying $100+/month for Railway or need enterprise features (multi-region, VPCs, SLAs, compliance).

---

## 2. System Components

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     External Systems                         │
├─────────────────────────────────────────────────────────────┤
│  GitHub API  │  Libraries.io API  │  Other Data Providers   │
│              │                    │  (npm, PyPI, Maven, etc.)│
└──────┬───────────────┬──────────────────────┬────────────────┘
       │               │                      │
       │               │                      │
┌──────▼───────────────▼──────────────────────▼────────────────┐
│            Load Balancer / Cloudflare Edge                    │
└──────┬────────────────────────────────────────────────────────┘
       │
       │
┌──────▼────────────────────────────────────────────────────────┐
│                      API Service Layer                        │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Fastify   │  │     Auth     │  │   Rate Limiter   │   │
│  │   Router    │  │    Plugin    │  │      Plugin      │   │
│  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                │                    │              │
│  ┌──────▼────────────────▼────────────────────▼─────────┐   │
│  │         OpenTelemetry Instrumentation               │   │
│  └──────┬──────────────────────────────────────────────┘   │
│         │                                                     │
│  ┌──────▼────────────────────────────────────────────────┐   │
│  │              API Controllers/Handlers                 │   │
│  │  - PackageController                                  │   │
│  │  - OrganizationController                             │   │
│  │  - SearchController                                   │   │
│  │  - StatsController                                    │   │
│  └──────┬────────────────────────────────────────────────┘   │
│         │                                                     │
│  ┌──────▼────────────────────────────────────────────────┐   │
│  │              Business Logic Services                  │   │
│  │  - PackageService                                     │   │
│  │  - OrganizationService                                │   │
│  │  - DependencyService                                  │   │
│  │  - SearchService                                      │   │
│  └──────┬────────────────────────────────────────────────┘   │
│         │                                                     │
│  ┌──────▼────────────────────────────────────────────────┐   │
│  │              Data Access Layer (DAL)                  │   │
│  │  - Repository Pattern                                 │   │
│  │  - ORM (Prisma)                                       │   │
│  └──────┬────────────────────────────────────────────────┘   │
└─────────┼─────────────────────────────────────────────────────┘
          │
          │
┌─────────▼─────────────────────────────────────────────────────┐
│                      Data Layer                               │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐         ┌───────────────────┐         │
│  │   PostgreSQL 18  │         │      Valkey 8.x   │         │
│  │   Database       │         │   (Cache & Queue) │         │
│  │                  │         │                   │         │
│  │  - packages      │         │  - API Cache      │         │
│  │  - organizations │         │  - Job Queue      │         │
│  │  - repositories  │         │  - Rate Limits    │         │
│  │  - dependencies  │         │                   │         │
│  │  - api_keys      │         │                   │         │
│  │  - job_executions│         │                   │         │
│  └──────────────────┘         └───────────────────┘         │
└───────────────────────────────────────────────────────────────┘


┌───────────────────────────────────────────────────────────────┐
│                 Background Job Processor                      │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Job        │  │   Job        │  │   Job            │   │
│  │   Scheduler  │  │   Processor  │  │   Monitor        │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                 │                    │              │
│  ┌──────▼─────────────────▼────────────────────▼─────────┐   │
│  │                  Job Workers                          │   │
│  │  - GitHubScraperJob                                   │   │
│  │  - DependencyParserJob                                │   │
│  │  - OrganizationEnrichmentJob                          │   │
│  │  - DataCleanupJob                                     │   │
│  └──────┬────────────────────────────────────────────────┘   │
│         │                                                     │
│  ┌──────▼────────────────────────────────────────────────┐   │
│  │        Extensible Data Provider Services              │   │
│  │  - GitHubProvider                                     │   │
│  │  - LibrariesIoProvider                                │   │
│  │  - NpmRegistryProvider                                │   │
│  │  - PyPIProvider                                       │   │
│  │  - MavenProvider                                      │   │
│  │  - ProviderRegistry (factory pattern)                 │   │
│  └──────┬────────────────────────────────────────────────┘   │
└─────────┼─────────────────────────────────────────────────────┘
          │
          │ (Reads/Writes)
          ▼
    [Data Layer]

┌───────────────────────────────────────────────────────────────┐
│              Observability & Monitoring                       │
├───────────────────────────────────────────────────────────────┤
│  OpenTelemetry Collector → AWS X-Ray / CloudWatch            │
│  Pino Logs → CloudWatch Logs                                 │
│  Metrics → CloudWatch Metrics                                │
└───────────────────────────────────────────────────────────────┘
```

---

## 3. Component Details

### 3.1 API Service Layer

#### 3.1.1 Technology Stack
- **Runtime**: Python 3.14
- **Framework**: FastAPI 0.115+
- **Validation**: Pydantic v2 (built into FastAPI)
- **Documentation**: FastAPI's built-in OpenAPI (Swagger UI)
- **Testing**: pytest + httpx + pytest-asyncio

#### 3.1.2 Architecture Layers

**1. HTTP Layer (FastAPI)**
- Route definitions with automatic OpenAPI schema
- Request/response handling with Pydantic models
- Dependency injection system
- CORS middleware
- Security headers middleware

**2. Dependency/Middleware Layer (FastAPI)**
- Authentication dependency (API key validation)
- Rate limiting middleware (slowapi + Valkey)
- Request logging (structlog with context)
- Schema validation (Pydantic models - automatic)
- OpenTelemetry instrumentation
- Exception handlers

**3. Controller Layer**
- Request parameter extraction
- Response formatting
- HTTP status code management
- Delegation to service layer

**4. Service Layer**
- Business logic implementation
- Data transformation
- Service composition
- Transaction management

**5. Data Access Layer**
- Database queries
- ORM operations
- Query optimization
- Connection management

**6. Observability Layer**
- OpenTelemetry tracing (automatic + manual spans)
- structlog structured logging
- Metrics collection
- Performance monitoring

#### 3.1.3 Key Design Patterns
- **Repository Pattern**: Abstract database operations
- **Service Pattern**: Encapsulate business logic
- **Dependency Injection**: FastAPI's built-in DI system
- **Factory Pattern**: Create service instances
- **Context Manager**: Database sessions and connections
- **Async/Await**: Non-blocking I/O throughout

### 3.2 Database Layer

#### 3.2.1 PostgreSQL 18 Schema

**Tables:**

```sql
-- Packages table
CREATE TABLE packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    ecosystem VARCHAR(50) NOT NULL,
    description TEXT,
    repository_url VARCHAR(500),
    homepage_url VARCHAR(500),
    latest_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, ecosystem)
);

-- Organizations table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    github_url VARCHAR(500),
    website_url VARCHAR(500),
    description TEXT,
    sponsorship_url VARCHAR(500),
    total_repositories INTEGER DEFAULT 0,
    total_stars INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Repositories table
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    github_url VARCHAR(500) UNIQUE NOT NULL,
    stars INTEGER DEFAULT 0,
    last_commit_at TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE,
    primary_language VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dependencies table
CREATE TABLE dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    package_id UUID REFERENCES packages(id) ON DELETE CASCADE,
    version VARCHAR(50),
    dependency_type VARCHAR(20), -- direct, dev, peer
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repository_id, package_id)
);

-- API Keys table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    tier VARCHAR(20) NOT NULL, -- free, standard, premium
    rate_limit INTEGER NOT NULL,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP
);

-- Job Executions table
CREATE TABLE job_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL, -- pending, running, completed, failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_packages_name_ecosystem ON packages(name, ecosystem);
CREATE INDEX idx_organizations_name ON organizations(name);
CREATE INDEX idx_repositories_org_id ON repositories(organization_id);
CREATE INDEX idx_repositories_stars ON repositories(stars DESC);
CREATE INDEX idx_dependencies_repo_id ON dependencies(repository_id);
CREATE INDEX idx_dependencies_package_id ON dependencies(package_id);
CREATE INDEX idx_job_executions_status ON job_executions(status, created_at);
```

#### 3.2.2 Database Optimization Strategy
- B-tree indexes on foreign keys
- Composite indexes for common query patterns
- Partial indexes for filtered queries
- Regular VACUUM and ANALYZE operations
- Connection pooling (10-20 connections)
- Read replicas for query distribution (future)

### 3.3 Caching Layer (Valkey 8.x)

#### 3.3.1 Cache Strategy
**Valkey-Compatible Cache Keys:**
```python
# Cache key patterns
f"cache:package:{ecosystem}:{name}:{filters_hash}"
f"cache:org:{org_name}"
"cache:stats:global"
f"ratelimit:{api_key}:{window}"
```

**TTL Strategy:**
- Package dependents: 1 hour
- Organization data: 6 hours
- Global stats: 15 minutes
- Rate limit counters: 1 hour sliding window

#### 3.3.2 Cache Invalidation
- Time-based expiration (TTL)
- Manual invalidation after data updates
- Cache warming for popular queries

### 3.4 Background Job Processor

#### 3.4.1 Technology Stack
- **Job Queue**: Celery 5.4+ (Valkey-backed)
- **Scheduler**: Celery Beat for periodic tasks
- **Concurrency**: Worker pools with prefork or async (gevent/eventlet)

### 3.5 Extensible Data Provider Architecture

#### 3.5.1 Provider Interface Pattern

All data providers implement a common interface to enable extensibility:

```python
from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel

class DataProvider(ABC):
    name: str
    provider_type: str  # 'repository' | 'registry' | 'aggregator'
    
    @abstractmethod
    async def initialize(self, config: ProviderConfig) -> None:
        """Initialize provider with credentials/config"""
        pass
    
    @abstractmethod
    async def fetch_repositories(self, query: RepositoryQuery) -> List[Repository]:
        """Fetch repository information"""
        pass
    
    @abstractmethod
    async def fetch_packages(self, query: PackageQuery) -> List[Package]:
        """Fetch package/dependency information"""
        pass
    
    @abstractmethod
    async def fetch_organizations(self, query: OrgQuery) -> List[Organization]:
        """Fetch organization information"""
        pass
    
    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Health check"""
        pass
    
    @abstractmethod
    async def get_rate_limit_status(self) -> RateLimitStatus:
        """Rate limit status"""
        pass
```

#### 3.5.2 Provider Registry

```python
class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, DataProvider] = {}
    
    def register(self, provider: DataProvider) -> None:
        """Register a provider"""
        self._providers[provider.name] = provider
    
    def get_provider(self, name: str) -> DataProvider:
        """Get provider by name"""
        return self._providers[name]
    
    def get_all_providers(self) -> List[DataProvider]:
        """Get all providers"""
        return list(self._providers.values())
    
    def get_providers_by_type(self, provider_type: str) -> List[DataProvider]:
        """Get providers by type"""
        return [p for p in self._providers.values() if p.provider_type == provider_type]
```

#### 3.5.3 Supported Providers

**Tier 1 (Initial Implementation):**
- GitHubProvider
- LibrariesIoProvider

**Tier 2 (Extensible Framework):**
- NpmRegistryProvider
- PyPIProvider
- MavenCentralProvider
- CratesIoProvider
- GitLabProvider
- BitbucketProvider

**Tier 3 (Future):**
- DepsDevProvider (Google)
- SnykProvider
- SonatypeProvider

#### 3.5.4 Provider Strategy Pattern

Jobs can utilize multiple providers with fallback:

```python
class ProviderStrategy:
    async def fetch_with_fallback(
        self,
        primary_provider: str,
        fallback_providers: List[str],
        query: Query
    ) -> Result:
        """Try primary provider, fall back on failure"""
        # Try primary, fall back on failure
        pass
```

#### 3.4.2 Job Types

**1. GitHub Scraper Job**
- **Frequency**: Daily at 2 AM UTC
- **Purpose**: Discover repositories and organizations
- **Process**:
  1. Query GitHub API for popular repositories
  2. Extract organization information
  3. Upsert organizations and repositories to database
  4. Queue DependencyParserJob for new repositories

**2. Dependency Parser Job**
- **Frequency**: Triggered by scraper or on-demand
- **Purpose**: Extract dependencies from repository files
- **Process**:
  1. Fetch package manifest files (package.json, etc.)
  2. Parse dependency information
  3. Create/update package records
  4. Create dependency relationships

**3. Organization Enrichment Job**
- **Frequency**: Weekly
- **Purpose**: Update organization metadata
- **Process**:
  1. Fetch updated repository counts
  2. Calculate total stars
  3. Check for sponsorship URLs
  4. Update organization records

**4. Data Cleanup Job**
- **Frequency**: Monthly
- **Purpose**: Remove stale data
- **Process**:
  1. Identify archived repositories
  2. Remove dependencies for deleted repositories
  3. Archive old job execution records

#### 3.4.3 Job Management
- Job status tracking in `job_executions` table
- Retry logic (3 attempts with exponential backoff via Celery)
- Dead letter queue for failed jobs
- Job prioritization (high, normal, low queues)
- OpenTelemetry tracing for job execution
- Celery Flower for monitoring dashboard

---

## 4. Data Flow

### 4.1 API Request Flow

```
1. Client Request
   ↓
2. Load Balancer (future)
   ↓
3. Express Router
   ↓
4. Authentication Middleware
   ↓
5. Rate Limiting Middleware
   ↓
6. Validation Middleware
   ↓
7. Controller
   ↓
8. Service Layer
   ↓
9. Check Redis Cache
   ├─ Cache Hit → Return cached data
   └─ Cache Miss ↓
10. Data Access Layer (ORM)
    ↓
11. PostgreSQL Query
    ↓
12. Store in Redis Cache
    ↓
13. Transform & Return Response
```

### 4.2 Background Job Flow

```
1. Cron Trigger / Manual Trigger
   ↓
2. Job Scheduler
   ↓
3. Create Job in Bull Queue
   ↓
4. Job Worker Picks Up Job
   ↓
5. Update job_executions (status: running)
   ↓
6. Execute Job Logic
   ├─ Call External API (GitHub, Libraries.io)
   ├─ Parse/Transform Data
   └─ Write to Database
   ↓
7. Update job_executions (status: completed/failed)
   ↓
8. Invalidate Related Caches
   ↓
9. Send Alerts (if failed)
```

---

## 5. Security Architecture

### 5.1 API Security

**Authentication:**
- API Key in header: `X-API-Key: <key>`
- Key hashing: bcrypt with salt
- Key rotation support

**Authorization:**
- Tier-based rate limits
- Endpoint access control by tier

**Input Validation:**
- Schema validation with Zod
- SQL injection prevention via ORM
- XSS prevention (sanitize inputs)

**Transport Security:**
- HTTPS enforcement
- HSTS headers
- Secure cookie flags

### 5.2 Database Security
- Parameterized queries (ORM)
- Least privilege database user
- Encrypted connections (SSL/TLS)
- Regular security patches

### 5.3 Secrets Management
- Environment variables for secrets
- No secrets in code/git
- Rotation policy for API keys
- Future: HashiCorp Vault integration

---

## 6. Deployment Architecture

### 6.1 Open Source Deployment Options

#### 6.1.1 Self-Hosted Deployment Paths

**Option 1: Docker Compose (Development/Small Scale)**
```yaml
services:
  api:
    build: ./packages/api
    environment:
      DATABASE_URL: postgresql://postgres:5432/wump
      VALKEY_URL: valkey://valkey:6379
  worker:
    build: ./packages/worker
  postgres:
    image: postgres:18
  valkey:
    image: valkey/valkey:8
```
- Best for: Development, small teams, low traffic
- Pros: Simple setup, low cost
- Cons: Limited scalability, manual updates

**Option 2: AWS ECS (Recommended for Production)**
- Use provided OpenTofu templates
- Deploy to your own AWS account
- Full control over infrastructure
- Best for: Production use, moderate-high traffic

**Option 3: Kubernetes (Advanced)**
- Community-contributed Helm charts (future)
- Works on any K8s cluster (EKS, GKE, AKS, self-managed)
- Best for: Large organizations, multi-cloud

**Option 4: Managed Service**
- No infrastructure management
- Pre-populated data
- Support and SLAs
- Best for: Quick start, no DevOps resources

### 6.2 Infrastructure as Code (OpenTofu)

#### 6.2.1 Repository Structure
```
infrastructure/
├── modules/
│   ├── networking/
│   │   ├── vpc.tf
│   │   ├── subnets.tf
│   │   ├── security_groups.tf
│   │   ├── nat_gateway.tf
│   │   └── outputs.tf
│   ├── compute/
│   │   ├── ecs_cluster.tf
│   │   ├── ecs_service.tf
│   │   ├── alb.tf
│   │   ├── autoscaling.tf
│   │   └── outputs.tf
│   ├── database/
│   │   ├── rds.tf
│   │   ├── elasticache.tf
│   │   ├── parameter_groups.tf
│   │   └── outputs.tf
│   ├── storage/
│   │   ├── s3.tf
│   │   ├── lifecycle.tf
│   │   └── outputs.tf
│   ├── monitoring/
│   │   ├── cloudwatch.tf
│   │   ├── alarms.tf
│   │   ├── dashboards.tf
│   │   └── outputs.tf
│   ├── iam/
│   │   ├── roles.tf
│   │   ├── policies.tf
│   │   └── outputs.tf
│   └── dns/
│       ├── cloudflare.tf
│       ├── ssl.tf
│       └── outputs.tf
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   ├── staging/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   └── production/
│       ├── main.tf
│       ├── variables.tf
│       ├── terraform.tfvars
│       └── backend.tf
├── scripts/
│   ├── plan.sh
│   ├── apply.sh
│   └── destroy.sh
└── README.md
```

#### 6.2.2 AWS Resource Specifications

**VPC & Networking:**
```hcl
module "networking" {
  source = "./modules/networking"
  
  vpc_cidr = "10.0.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
  
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
  database_subnet_cidrs = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]
}
```

**ECS Fargate Configuration:**
```hcl
module "api_service" {
  source = "./modules/compute"
  
  cluster_name = "dependency-api-cluster"
  service_name = "api-service"
  
  task_cpu    = 512  # 0.5 vCPU
  task_memory = 1024 # 1 GB
  
  desired_count = 3
  min_capacity  = 2
  max_capacity  = 10
  
  autoscaling_target_cpu = 70
  autoscaling_target_memory = 80
}
```

**RDS PostgreSQL 18:**
```hcl
module "database" {
  source = "./modules/database"
  
  engine_version = "18.1"
  instance_class = "db.t4g.large"
  
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_type          = "gp3"
  iops                  = 3000
  
  multi_az               = true
  backup_retention_period = 7
  
  read_replica_count = 2
}
```

**ElastiCache for Valkey 8.x:**
```hcl
module "cache" {
  source = "./modules/database"
  
  engine = "valkey"
  engine_version = "8.0"
  node_type      = "cache.t4g.medium"
  
  num_cache_clusters = 3
  cluster_mode_enabled = true
  
  automatic_failover_enabled = true
}
```

**Application Load Balancer:**
```hcl
module "alb" {
  source = "./modules/compute"
  
  name = "dependency-api-alb"
  
  health_check_path = "/health"
  health_check_interval = 30
  
  ssl_certificate_arn = aws_acm_certificate.api.arn
  
  deregistration_delay = 30
}
```

#### 6.2.3 Cloudflare Configuration

```hcl
resource "cloudflare_zone" "main" {
  zone = var.domain_name
}

resource "cloudflare_record" "api" {
  zone_id = cloudflare_zone.main.id
  name    = "api"
  value   = module.alb.dns_name
  type    = "CNAME"
  proxied = true
}

resource "cloudflare_page_rule" "api_cache" {
  zone_id = cloudflare_zone.main.id
  target  = "api.${var.domain_name}/api/v1/stats*"
  
  actions {
    cache_level = "cache_everything"
    edge_cache_ttl = 900
  }
}

resource "cloudflare_firewall_rule" "rate_limit" {
  zone_id = cloudflare_zone.main.id
  description = "Rate limit API endpoints"
  
  filter_id = cloudflare_filter.api_rate_limit.id
  action = "challenge"
}
```

#### 6.2.4 Secrets Management

```hcl
resource "aws_secretsmanager_secret" "database" {
  name = "dependency-api/database-credentials"
  
  rotation_rules {
    automatically_after_days = 30
  }
}

resource "aws_secretsmanager_secret" "api_keys" {
  name = "dependency-api/external-api-keys"
  
  # GitHub, Libraries.io tokens
}
```

### 6.3 Development Environment (Open Source)
```
Docker Compose:
- API Service (Node.js container)
- PostgreSQL (postgres:15 container)
- Redis (redis:7 container)
- Job Worker (Node.js container)
```

### 6.2 Production Architecture (Future)
```
Cloud Provider (AWS/GCP/Azure):
- Load Balancer (ALB/Cloud Load Balancer)
- API Service (ECS/Kubernetes pods, auto-scaling)
- Job Workers (ECS/Kubernetes pods)
- RDS PostgreSQL (Multi-AZ, read replicas)
- ElastiCache Redis (cluster mode)
- S3/Cloud Storage (backups, logs)
- CloudWatch/Monitoring (metrics, logs)
```

### 6.3 CI/CD Pipeline
1. Code push to GitHub
2. GitHub Actions triggered
3. Run linter (ESLint)
4. Run unit tests (Jest)
5. Run integration tests
6. Build Docker images
7. Push to AWS ECR
8. Deploy to staging (ECS)
9. Run smoke tests
10. Manual approval gate
11. Deploy to production (ECS)
12. Run health checks

**GitHub Actions Workflow:**
```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          python-version: '3.14'
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run pytest
  
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
      - run: docker build -t api .
      - run: docker push $ECR_REGISTRY/api:${{ github.sha }}
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: aws-actions/amazon-ecs-deploy-task-definition@v1
```

---

## 7. Monitoring & Observability

### 7.1 OpenTelemetry Integration

#### 7.1.1 Tracing
**Instrumentation:**
- `opentelemetry-instrumentation-fastapi` - FastAPI instrumentation
- `opentelemetry-instrumentation-sqlalchemy` - SQLAlchemy instrumentation
- `opentelemetry-instrumentation-redis` - Valkey/Redis instrumentation
- `opentelemetry-instrumentation-httpx` - HTTP client instrumentation
- `opentelemetry-instrumentation-celery` - Celery task instrumentation

**Trace Spans:**
- HTTP request/response lifecycle (automatic via FastAPI instrumentation)
- Database queries with query text (automatic via SQLAlchemy instrumentation)
- Valkey operations (get, set, del)
- External API calls (GitHub, Libraries.io, etc.)
- Background job execution (Celery tasks)
- Business logic operations (manual spans)

**Exporters:**
- OTLP exporter to AWS X-Ray
- Console exporter for development
- Jaeger exporter for local debugging (optional)

#### 7.1.2 Metrics
**Default Metrics:**
- `http.server.request.duration` - Request duration histogram
- `http.server.active_requests` - Active requests gauge
- `db.client.connections.usage` - Database connection pool
- `cache.hits` - Cache hit counter
- `cache.misses` - Cache miss counter

**Custom Metrics:**
- `api.package_lookup.duration` - Package query performance
- `job.execution.duration` - Job processing time
- `provider.api.calls` - External API call counter
- `provider.rate_limit.remaining` - Provider rate limit gauge

**Exporters:**
- OTLP exporter to CloudWatch
- Prometheus exporter for scraping (optional)

#### 7.1.3 Context Propagation
- W3C Trace Context headers
- Baggage for cross-service correlation
- Trace ID in all log messages

### 7.2 Logging Strategy

**Logger:** structlog (structured logging for Python with JSON output)

**Configuration:**
```python
import structlog
from opentelemetry import trace

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Add trace context
        lambda _, __, event_dict: {
            **event_dict,
            "trace_id": format(trace.get_current_span().get_span_context().trace_id, "032x"),
            "span_id": format(trace.get_current_span().get_span_context().span_id, "016x"),
        },
        structlog.processors.JSONRenderer(),  # Output as JSON
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

**JSON Output Example:**
```json
{
  "event": "API request received",
  "level": "info",
  "timestamp": "2025-12-21T10:30:45.123Z",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "method": "GET",
  "path": "/api/v1/packages/express/dependents",
  "status_code": 200,
  "duration_ms": 245
}
```

**Log Levels:**
- `fatal` - Unrecoverable errors requiring immediate attention
- `error` - Error conditions that need investigation
- `warn` - Warning conditions (rate limits, retries)
- `info` - Informational messages (request logs, job starts/ends)
- `debug` - Detailed debugging information
- `trace` - Very detailed diagnostic information

**Key Logs:**
- API requests (method, path, status, duration)
- Authentication attempts
- Rate limit violations
- Job executions
- Database query performance
- External API calls
- OpenTelemetry trace IDs in all logs

### 7.3 Metrics Collection

**Collection Method:** OpenTelemetry Metrics API

**Key Metrics:**
- Request rate (requests/second by endpoint)
- Response time (p50, p95, p99 by endpoint)
- Error rate (4xx, 5xx by endpoint)
- Database query time (histogram)
- Database connection pool utilization
- Cache hit rate (by key pattern)
- Job execution time (by job type)
- Job queue depth (by queue)
- Provider API call rate (by provider)
- Provider rate limit remaining (by provider)

**Aggregation:**
- CloudWatch Metrics via OTLP
- Custom CloudWatch dashboards
- Metric alarms for SLOs

### 7.4 Health Checks
- `/health` - API service health
- `/health/db` - Database connectivity
- `/health/redis` - Redis connectivity
- `/health/jobs` - Job processor status

**Kubernetes Probes:**
- Liveness probe: `/health` (restart on failure)
- Readiness probe: `/health` (remove from load balancer on failure)
- Startup probe: `/health` (delay traffic until ready)

### 7.5 Alerting

**Alert Channels:**
- AWS SNS topics
- CloudWatch Alarms
- PagerDuty integration (production)
- Slack webhooks

**Alert Conditions:**
- API error rate > 5% (5-minute window)
- Response time p95 > 1 second (5-minute window)
- Database connection failures
- Redis connection failures
- Job failure rate > 10%
- Disk space > 80%
- Memory usage > 85%
- CPU usage > 80% (sustained 10 minutes)
- Provider rate limit < 10% remaining

**Alert Severity:**
- P1: Production down, immediate action
- P2: Degraded performance, action within 1 hour
- P3: Warning condition, action within 1 day
- P4: Informational, no immediate action

### 7.6 Distributed Tracing Examples

**Example Trace for Package Lookup:**
```
HTTP GET /api/v1/packages/express/dependents
  ├─ fastify.request (10ms)
  ├─ auth.validateApiKey (5ms)
  ├─ ratelimit.check (3ms)
  ├─ packageService.getDependents (450ms)
  │   ├─ redis.get cache:package:npm:express:* (2ms) [MISS]
  │   ├─ db.query SELECT * FROM dependencies... (380ms)
  │   ├─ db.query SELECT * FROM organizations... (60ms)
  │   └─ redis.setex cache:package:npm:express:* (5ms)
  └─ fastify.response (3ms)
Total: 471ms
```

**Example Trace for Background Job:**
```
Job: GitHubScraperJob
  ├─ job.start (1ms)
  ├─ github.fetchRepositories (2500ms)
  │   ├─ http.request GET api.github.com/search/repositories (2450ms)
  │   └─ ratelimit.check (50ms)
  ├─ db.transaction.begin (5ms)
  ├─ db.batchInsert organizations (350ms)
  ├─ db.batchInsert repositories (800ms)
  ├─ db.transaction.commit (45ms)
  ├─ cache.invalidate package:* (120ms)
  └─ job.complete (5ms)
Total: 3826ms
```

---

## 8. Scalability Considerations

### 8.1 Horizontal Scaling
- Stateless API servers
- Load balancer distribution
- Session management in Redis
- Database read replicas

### 8.2 Vertical Scaling
- Database connection pooling
- Redis memory optimization
- Database query optimization
- Index tuning

### 8.3 Data Growth Strategy
- Partition tables by date (future)
- Archive old job executions
- Implement data retention policies
- Database compression

---

## 9. Technology Decisions

### 9.1 Why Python?
- Rich ecosystem for data processing and APIs
- Excellent libraries for external API integrations
- Strong typing with Pydantic and type hints
- Async/await support (asyncio)
- Great for data-heavy workloads
- Popular in data/ML space (future features)

### 9.2 Why FastAPI?
- **Performance**: One of the fastest Python frameworks (comparable to Node.js)
- **Automatic validation**: Pydantic models for request/response
- **Automatic docs**: OpenAPI/Swagger UI built-in
- **Type safety**: Full type hints and editor support
- **Async native**: First-class async/await support
- **Dependency injection**: Clean, testable code
- **Modern**: Built on Starlette and Pydantic v2
- **Active development**: Large community, frequent updates

### 9.3 Why PostgreSQL 18?
- ACID compliance
- Rich query capabilities
- JSON support (JSONB with continued improvements)
- Excellent for relational data
- Enhanced indexing and performance in v18
- Logical replication improvements
- Built-in incremental backup support
- Better parallel query performance

### 9.4 Why SQLAlchemy 2.0?
- **Mature ORM**: Industry standard for Python
- **Async support**: Native async/await in 2.0
- **Type safety**: Works with mypy and Pydantic
- **Powerful**: Complex queries, relationships, migrations
- **Migration tool**: Alembic for schema changes
- **Performance**: Query optimization, lazy loading

### 9.5 Why Celery (vs other Python task queues)?
- **Python native**: Perfect for Python ecosystem
- **Battle-tested**: Used by Instagram, Reddit, others
- **Valkey/Redis backed**: Persistence and reliability
- **Flexible**: Multiple broker options
- **Retry logic**: Built-in exponential backoff
- **Monitoring**: Celery Flower dashboard
- **Scheduling**: Celery Beat for periodic tasks
- **Canvas**: Task chains, groups, chords for complex workflows

### 9.6 Why Valkey 8.x?
- **Open-source**: Linux Foundation project, truly open
- **Redis-compatible**: Drop-in replacement, same APIs (redis-py works)
- **High-performance**: Caching and job queue support (Celery)
- **No licensing concerns**: Avoids Redis licensing changes
- **Active development**: Community-driven innovation
- **AWS support**: ElastiCache for Valkey available
- **Modern features**: ACLs, Functions, Pub/Sub
- **Better memory efficiency**: Optimized for cloud workloads

### 9.7 Why OpenTelemetry?
- Vendor-neutral observability standard
- Single SDK for traces, metrics, and logs
- Wide ecosystem support
- AWS X-Ray integration
- Future-proof observability strategy
- Reduces vendor lock-in

### 9.8 Why OpenTofu (vs Terraform)?
- Open-source fork of Terraform
- Community-driven development
- No licensing concerns
- Terraform-compatible
- Active development
- HashiCorp MPL issues avoided

### 9.9 Why Open Source + Managed Service Model?
- **Trust & Transparency**: Users can audit code, understand how data is collected
- **Community Innovation**: Contributors can add new providers, features
- **Flexibility**: Self-host for compliance/privacy or use managed service
- **Sustainable**: Managed service revenue funds development
- **No Vendor Lock-in**: Always have option to self-host
- **Proven Model**: Successful pattern (Sentry, Plausible, PostHog, GitLab)

---

## 10. Future Architecture Enhancements

### 10.1 Phase 2
- GraphQL API alongside REST
- WebSocket server for real-time updates
- Separate read/write databases (CQRS)
- CDN for static content

### 10.2 Phase 3
- Microservices split:
  - Package Service
  - Organization Service
  - Job Service
- Event streaming (Kafka/RabbitMQ)
- Search engine (Elasticsearch)
- ML model deployment for recommendations

---

## 11. Architecture Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| GitHub API rate limits | High | Implement caching, use multiple tokens, backoff strategy |
| Database bottleneck | High | Connection pooling, read replicas, query optimization |
| Job processing delays | Medium | Worker scaling, job prioritization, parallel processing |
| Cache invalidation bugs | Medium | Conservative TTLs, manual invalidation on updates |
| Security breach | High | Regular security audits, dependency updates, monitoring |

---

## 12. Architecture Decision Records (ADRs)

### ADR-001: Use PostgreSQL over MongoDB
**Decision**: Use PostgreSQL 18 as primary database  
**Rationale**: Data is highly relational (packages → dependencies → repositories → organizations). PostgreSQL provides ACID guarantees, complex joins, and better consistency. Version 18 adds performance improvements, better parallel queries, and incremental backup support.

### ADR-002: Use Celery over other Python task queues
**Decision**: Use Celery with Valkey for job queue  
**Rationale**: Celery is the industry standard for Python background tasks, provides persistence, retry logic, job monitoring (Flower), scheduling (Beat), and is production-tested at scale. Better ecosystem than alternatives like Dramatiq or RQ.

### ADR-003: Use FastAPI over Flask/Django
**Decision**: Use FastAPI as web framework  
**Rationale**: Modern async framework with automatic validation (Pydantic), automatic API documentation (OpenAPI), excellent performance, type safety with Python type hints, and great developer experience. Better suited for APIs than Django, faster than Flask.

### ADR-004: Implement OpenTelemetry for observability
**Decision**: Use OpenTelemetry SDK for traces, metrics, and logs  
**Rationale**: Vendor-neutral standard, better AWS X-Ray integration, unified observability approach, future-proof strategy.

### ADR-005: Use extensible provider pattern
**Decision**: Abstract data providers behind common interface  
**Rationale**: Enables adding new data sources (npm, PyPI, GitLab) without core changes. Improves testability and maintainability.

### ADR-006: Use Valkey over Redis
**Decision**: Use Valkey 8.x instead of Redis  
**Rationale**: Open-source Linux Foundation project, avoids Redis licensing issues (SSPL), fully Redis-compatible, AWS ElastiCache support, community-driven development, no vendor lock-in concerns.

### ADR-007: Use OpenTofu for IaC
**Decision**: Use OpenTofu instead of Terraform  
**Rationale**: Open-source, no licensing concerns, community-driven, Terraform-compatible, avoids HashiCorp MPL issues.

### ADR-008: Monolithic API initially, microservices later
**Decision**: Start with monolithic API service  
**Rationale**: Simpler to develop, deploy, and debug initially. Clear service boundaries allow future microservices split.

### ADR-009: Open-source business logic, managed data service
**Decision**: Open source all application code while offering managed service  
**Rationale**: Builds trust and community, allows self-hosting for privacy/compliance needs, enables contributions for new data providers, creates sustainable business model (managed service revenue), follows successful patterns (Sentry, Plausible, PostHog).

### ADR-010: Cache-aside pattern for Valkey
**Decision**: Implement cache-aside (lazy loading) with Valkey  
**Rationale**: Simple to implement, works well with read-heavy workloads, automatic cache updates on misses, Valkey's Redis compatibility makes migration seamless.
