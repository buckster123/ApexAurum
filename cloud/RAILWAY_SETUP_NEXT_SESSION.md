# Railway Setup - Next Session Guide

## Status: Ready for Fresh Deployment

The ApexAurum Cloud code is **complete and tested**. Just needs proper Railway setup.

## What We Learned (Railway Gotchas)

1. **MUST connect GitHub repo to each service** - Without this, Railway uses cached/wrong images
2. **MUST connect branch (master)** - Click "Connect Environment to Branch"
3. **Root Directory matters** - Backend: `cloud/backend`, Frontend: `cloud/frontend`
4. **Docker healthcheck killed our app** - We removed it, let Railway handle healthchecks
5. **Argon2 not bcrypt** - We switched password hashing to avoid 72-byte limit issues

## Fresh Setup Steps

### 1. Create New Project
```
Railway Dashboard → New Project → Empty Project
Name: ApexAurum-Cloud
```

### 2. Add PostgreSQL
```
+ New → Database → PostgreSQL
Wait for it to provision
```

### 3. Add Backend Service
```
+ New → GitHub Repo → Select ApexAurum repo
Settings:
  - Root Directory: cloud/backend
  - Branch: master (CLICK "Connect Environment to Branch"!)
  - Builder: Dockerfile (should auto-detect)

Variables to add:
  - DATABASE_URL: (Add Reference → PostgreSQL → DATABASE_URL)
  - ANTHROPIC_API_KEY: sk-ant-xxx (your key)
  - ALLOWED_ORIGINS: *
  - SECRET_KEY: (any random string, e.g., apexaurum-secret-2026)
  - DEBUG: false
```

### 4. Add Frontend Service
```
+ New → GitHub Repo → Select ApexAurum repo
Settings:
  - Root Directory: cloud/frontend
  - Branch: master (CLICK "Connect Environment to Branch"!)
  - Builder: Dockerfile (should auto-detect)

Variables to add:
  - VITE_API_URL: https://[backend-domain].up.railway.app
    (Get this from backend's public domain after it deploys)
```

### 5. Verify Deployment
```bash
# Test backend health
curl https://[backend-domain].up.railway.app/health

# Test registration
curl -X POST https://[backend-domain].up.railway.app/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"testpass123"}'
```

## Code Status (All Ready)

- ✅ Backend: FastAPI + SQLAlchemy + Argon2 auth
- ✅ Frontend: Vue 3 + Pinia + TailwindCSS
- ✅ All null handling fixes applied
- ✅ Login redirect with nextTick
- ✅ Docker healthcheck removed (was causing crash loop)
- ✅ Redis deps commented out (not needed yet)

## Key Files

- `cloud/backend/Dockerfile` - Backend container config
- `cloud/backend/railway.toml` - Railway build settings
- `cloud/backend/app/auth/password.py` - Argon2 password hashing
- `cloud/frontend/Dockerfile` - Frontend container config

## If Things Go Wrong

1. **502 errors**: Check Deploy Logs for Python traceback
2. **Container crash loop**: Usually healthcheck or missing env var
3. **Auth not working**: Make sure DATABASE_URL is set
4. **Frontend can't reach backend**: Check VITE_API_URL is correct

## Railway API Token (for automation)
```
90fb849e-af7b-4ea5-8474-d57d8802a368
```

---
Created: 2026-01-25
Ready for: Fresh Railway deployment
