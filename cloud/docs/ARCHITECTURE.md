# ApexAurum Cloud Architecture

## Vision

Transform ApexAurum from a single-user Streamlit application into a scalable, multi-tenant cloud service while preserving the Village Protocol, multi-agent orchestration, and the soul of the project.

```
"The gold was always there. Now we share it with the world."
```

---

## Architecture Overview

```
                                    ┌─────────────────┐
                                    │   CDN (CloudFlare)
                                    │   Static Assets  │
                                    └────────┬────────┘
                                             │
┌─────────────────────────────────────────────────────────────────────────┐
│                           INGRESS (nginx/traefik)                       │
│                     SSL Termination + Load Balancing                    │
└─────────────────────────────────────────────────────────────────────────┘
         │                           │                          │
         ▼                           ▼                          ▼
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────┐
│   Frontend      │      │   API Gateway       │      │   WebSocket     │
│   (Vue.js SPA)  │      │   (FastAPI)         │      │   Server        │
│                 │      │                     │      │   (Real-time)   │
│   • Chat UI     │◄────►│   • /api/v1/*       │◄────►│   • Streaming   │
│   • Village     │      │   • Auth middleware │      │   • Events      │
│   • Dashboard   │      │   • Rate limiting   │      │   • Presence    │
└─────────────────┘      └──────────┬──────────┘      └─────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
           ┌──────────────┐ ┌─────────────┐ ┌─────────────────┐
           │  Tool        │ │  Agent      │ │  Village        │
           │  Service     │ │  Service    │ │  Service        │
           │              │ │             │ │                 │
           │  140+ tools  │ │  Spawning   │ │  Memory realms  │
           │  Sandboxed   │ │  Lifecycle  │ │  Convergence    │
           └──────┬───────┘ └──────┬──────┘ └────────┬────────┘
                  │                │                  │
                  └────────────────┼──────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────┐
│                           DATA LAYER                                    │
├─────────────────┬─────────────────┬─────────────────┬──────────────────┤
│   PostgreSQL    │      Redis      │    MinIO/S3     │   Vector Store   │
│                 │                 │                 │                  │
│  • Users        │  • Sessions     │  • Music files  │  • ChromaDB or   │
│  • Convos       │  • Cache        │  • Sandbox      │    pgvector      │
│  • Agents       │  • Pub/Sub      │  • Uploads      │  • Embeddings    │
│  • Memory       │  • Rate limits  │  • Exports      │  • Knowledge     │
└─────────────────┴─────────────────┴─────────────────┴──────────────────┘
```

---

## Service Breakdown

### 1. Frontend Service (Vue.js)

**Location:** `cloud/frontend/`

**Why Vue.js:**
- Already started in `reusable_lib/scaffold/fastapi_app/static/village/`
- Reactive, component-based
- Excellent WebSocket support
- Smaller bundle than React

**Features:**
- Chat interface with streaming responses
- Agent village visualization (2D canvas)
- Dashboard with usage stats
- Settings/preferences
- Mobile responsive

**Tech Stack:**
```
Vue 3 + Composition API
Pinia (state management)
Vue Router
TailwindCSS
Socket.io-client (WebSocket)
```

### 2. API Gateway (FastAPI)

**Location:** `cloud/backend/` (evolved from `reusable_lib/scaffold/fastapi_app/`)

**Responsibilities:**
- Authentication/Authorization
- Request routing
- Rate limiting
- API versioning
- OpenAPI documentation

**Endpoints:**
```
/api/v1/
├── auth/
│   ├── POST /login
│   ├── POST /register
│   ├── POST /refresh
│   └── POST /logout
├── chat/
│   ├── POST /message          # Send message, get response
│   ├── GET  /conversations    # List conversations
│   ├── GET  /conversations/{id}
│   └── DELETE /conversations/{id}
├── agents/
│   ├── POST /spawn            # Create agent
│   ├── GET  /{id}/status
│   ├── GET  /{id}/result
│   └── POST /council          # Socratic council
├── village/
│   ├── GET  /knowledge        # Search village memory
│   ├── POST /knowledge        # Add to village
│   ├── GET  /convergence      # Detect convergence
│   └── GET  /threads          # List threads
├── tools/
│   ├── GET  /                 # List available tools
│   ├── POST /execute          # Execute tool directly
│   └── GET  /{name}/schema
├── music/
│   ├── POST /generate
│   ├── GET  /{id}/status
│   ├── GET  /library
│   └── GET  /{id}/stream      # Stream audio
└── user/
    ├── GET  /profile
    ├── PUT  /profile
    ├── GET  /usage
    └── GET  /preferences
```

### 3. WebSocket Server

**Real-time features:**
- Chat streaming (token-by-token)
- Agent status updates
- Tool execution progress
- Village events (new knowledge, convergence)
- Presence (who's online)

**Protocol:**
```javascript
// Client → Server
{ "type": "chat", "message": "Hello", "conversation_id": "..." }
{ "type": "subscribe", "channel": "agent:abc123" }
{ "type": "ping" }

// Server → Client
{ "type": "token", "content": "Hello", "conversation_id": "..." }
{ "type": "tool_start", "tool": "web_search", "id": "..." }
{ "type": "tool_complete", "id": "...", "result": {...} }
{ "type": "agent_update", "agent_id": "...", "status": "complete" }
{ "type": "village_event", "event": "convergence", "data": {...} }
```

### 4. Tool Service

**Sandboxed execution without Docker-in-Docker:**

```
Option A: Firecracker microVMs (AWS Lambda-style)
Option B: gVisor containers (Google Cloud Run-style)
Option C: Kubernetes Jobs (isolated pods)
Option D: WASM sandboxing (Wasmer/Wasmtime)
```

**Recommended: Option C (Kubernetes Jobs)** for initial deployment
- Each code execution = ephemeral pod
- Resource limits enforced
- Network isolation
- Automatic cleanup

### 5. Agent Service

**Manages agent lifecycle:**
- Spawn agents as background tasks (Celery/ARQ)
- Track status in Redis
- Store results in PostgreSQL
- Support parallel execution

### 6. Village Service

**Multi-agent memory system:**
- Private/Village/Bridge realms (existing)
- pgvector for embeddings (replaces ChromaDB)
- Convergence detection
- Thread visualization

---

## Database Schema

### PostgreSQL

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    settings JSONB DEFAULT '{}'
);

-- Conversations
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    archived BOOLEAN DEFAULT FALSE,
    favorite BOOLEAN DEFAULT FALSE,
    tags TEXT[] DEFAULT '{}'
);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    tool_calls JSONB,
    tool_results JSONB,
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 6),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agents
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    task TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    result TEXT,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Village Knowledge (with pgvector)
CREATE TABLE village_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 dimension
    category VARCHAR(50),
    visibility VARCHAR(20) DEFAULT 'private',
    agent_id VARCHAR(50),
    conversation_thread VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_knowledge_embedding ON village_knowledge
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Memory (key-value)
CREATE TABLE memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, key)
);

-- Music Tasks
CREATE TABLE music_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    style VARCHAR(255),
    title VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    file_path VARCHAR(500),
    suno_task_id VARCHAR(100),
    favorite BOOLEAN DEFAULT FALSE,
    play_count INTEGER DEFAULT 0,
    agent_id VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- API Usage Tracking
CREATE TABLE usage_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    endpoint VARCHAR(100),
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_usd DECIMAL(10, 6),
    cached BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Authentication

### JWT-based Auth

```python
# Token structure
{
    "sub": "user_uuid",
    "email": "user@example.com",
    "exp": 1234567890,
    "iat": 1234567800,
    "type": "access"  # or "refresh"
}

# Token lifetimes
ACCESS_TOKEN_EXPIRE = 15 minutes
REFRESH_TOKEN_EXPIRE = 7 days
```

### OAuth2 Providers (Phase 2)
- Google
- GitHub
- Discord

---

## Infrastructure

### Kubernetes Manifests

```
cloud/infrastructure/k8s/
├── namespace.yaml
├── configmap.yaml
├── secrets.yaml (encrypted with SOPS)
├── deployments/
│   ├── api.yaml
│   ├── frontend.yaml
│   └── worker.yaml
├── services/
│   ├── api-service.yaml
│   └── frontend-service.yaml
├── ingress.yaml
├── hpa.yaml (Horizontal Pod Autoscaler)
└── pdb.yaml (Pod Disruption Budget)
```

### Terraform (AWS)

```
cloud/infrastructure/terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── modules/
│   ├── vpc/
│   ├── eks/
│   ├── rds/
│   ├── elasticache/
│   └── s3/
└── environments/
    ├── dev/
    ├── staging/
    └── prod/
```

---

## Migration Strategy

### Phase 1: Database Migration (Week 1-2)
1. Create PostgreSQL schema
2. Write migration scripts from JSON files
3. Test with copy of production data
4. Implement repository pattern in FastAPI

### Phase 2: API Completion (Week 3-4)
1. Port remaining Streamlit-only tools to FastAPI
2. Implement WebSocket streaming
3. Add authentication middleware
4. Create OpenAPI documentation

### Phase 3: Frontend (Week 5-6)
1. Build Vue.js SPA structure
2. Implement chat interface
3. Add agent/village visualizations
4. Mobile responsive design

### Phase 4: Infrastructure (Week 7-8)
1. Kubernetes manifests
2. Terraform for AWS/GCP
3. CI/CD pipeline
4. Monitoring (Prometheus/Grafana)

### Phase 5: Launch (Week 9)
1. Beta testing
2. Documentation
3. Public launch

---

## Development Workflow

### Local Development

```bash
# Start all services
cd cloud/
docker-compose -f docker-compose.dev.yml up

# Services available at:
# - Frontend: http://localhost:3000
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
# - MinIO: http://localhost:9000
```

### Code Structure

```
cloud/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── database.py          # DB connection
│   │   ├── auth/
│   │   │   ├── jwt.py
│   │   │   ├── oauth.py
│   │   │   └── middleware.py
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── chat.py
│   │   │   │   ├── agents.py
│   │   │   │   ├── village.py
│   │   │   │   ├── tools.py
│   │   │   │   └── music.py
│   │   │   └── deps.py          # Dependencies
│   │   ├── services/
│   │   │   ├── claude.py        # Anthropic client
│   │   │   ├── agent_runner.py
│   │   │   ├── tool_executor.py
│   │   │   └── village.py
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   └── tools/               # Ported from tools/
│   ├── tests/
│   ├── alembic/                 # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── router/
│   │   ├── stores/              # Pinia
│   │   ├── components/
│   │   ├── views/
│   │   └── services/            # API clients
│   ├── package.json
│   └── Dockerfile
├── infrastructure/
│   ├── k8s/
│   ├── terraform/
│   └── docker-compose.dev.yml
└── docs/
    ├── ARCHITECTURE.md          # This file
    ├── API.md
    ├── DEPLOYMENT.md
    └── CONTRIBUTING.md
```

---

## Cost Estimation (Production)

### AWS (Minimal Production)

| Service | Spec | Monthly Cost |
|---------|------|--------------|
| EKS | Control plane | $73 |
| EC2 (3x t3.medium) | Worker nodes | $90 |
| RDS PostgreSQL | db.t3.small | $25 |
| ElastiCache Redis | cache.t3.micro | $15 |
| S3 | 50GB + transfer | $5 |
| ALB | Load balancer | $20 |
| CloudWatch | Monitoring | $10 |
| **Total** | | **~$240/month** |

### Scaling Estimate

| Users | Infra Cost | Anthropic API | Total |
|-------|------------|---------------|-------|
| 10 | $240 | ~$50 | $290 |
| 100 | $400 | ~$500 | $900 |
| 1000 | $800 | ~$5000 | $5800 |

---

## Security Considerations

### Secrets Management
- AWS Secrets Manager / HashiCorp Vault
- Kubernetes secrets with SOPS encryption
- No secrets in code or environment files

### API Security
- Rate limiting per user
- Request size limits
- Input validation (Pydantic)
- SQL injection prevention (SQLAlchemy ORM)
- XSS prevention (Vue.js auto-escaping)

### Data Isolation
- Row-level security in PostgreSQL
- User-scoped queries
- Separate S3 prefixes per user

### Audit Logging
- All API requests logged
- Authentication events
- Tool executions
- Admin actions

---

## Open Questions

1. **Vector Store:** pgvector vs managed Pinecone/Weaviate?
2. **Code Execution:** Kubernetes Jobs vs Firecracker vs WASM?
3. **Pricing Model:** Free tier? Pay-per-use? Subscription?
4. **Multi-region:** Start single-region, expand later?
5. **Mobile App:** Native iOS/Android or PWA?

---

## Next Steps

1. [ ] Set up development environment (docker-compose.dev.yml)
2. [ ] Create PostgreSQL schema and migrations
3. [ ] Scaffold FastAPI backend structure
4. [ ] Scaffold Vue.js frontend structure
5. [ ] Implement JWT authentication
6. [ ] Port chat endpoint with streaming
7. [ ] Basic deployment to single VM for testing

---

*"The furnace expands. The gold multiplies."*
