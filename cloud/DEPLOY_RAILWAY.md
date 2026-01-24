# Deploying ApexAurum Cloud to Railway

## Quick Start (10 minutes)

### Step 1: Push to GitHub

```bash
cd /home/hailo/claude-root/Projects/ApexAurum
git add cloud/
git commit -m "ApexAurum Cloud: Railway deployment ready"
git push origin master
```

### Step 2: Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub (recommended)
3. Verify your account

### Step 3: Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose `buckster123/ApexAurum`
4. Railway will detect the monorepo

### Step 4: Add PostgreSQL

1. In your project, click **"+ New"**
2. Select **"Database" → "PostgreSQL"**
3. Railway provisions it automatically
4. Copy the `DATABASE_URL` from the Variables tab

**Enable pgvector:**
```sql
-- Connect to Railway PostgreSQL and run:
CREATE EXTENSION IF NOT EXISTS vector;
```

### Step 5: Add Redis

1. Click **"+ New"**
2. Select **"Database" → "Redis"**
3. Copy the `REDIS_URL` from Variables

### Step 6: Deploy Backend

1. Click **"+ New" → "GitHub Repo"**
2. Select your repo
3. Set **Root Directory:** `cloud/backend`
4. Add environment variables:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=generate-a-random-32-char-string

# Optional
VOYAGE_API_KEY=
SUNO_API_KEY=

# App Config
DEBUG=false
ALLOWED_ORIGINS=https://your-frontend.railway.app
```

5. Click **Deploy**

### Step 7: Deploy Frontend

1. Click **"+ New" → "GitHub Repo"**
2. Select your repo
3. Set **Root Directory:** `cloud/frontend`
4. Add environment variables:

```env
VITE_API_URL=https://your-backend.railway.app
```

5. Click **Deploy**

### Step 8: Configure Domains

1. Go to Backend service → Settings → Domains
2. Generate a Railway domain or add custom domain
3. Do the same for Frontend
4. Update `ALLOWED_ORIGINS` in backend with frontend URL

---

## Architecture on Railway

```
┌─────────────────────────────────────────────────────┐
│                    Railway Project                   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Backend   │  │  Frontend   │  │  PostgreSQL │ │
│  │   FastAPI   │  │   Vue.js    │  │  + pgvector │ │
│  │   :8000     │  │   :3000     │  │   :5432     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │         │
│         └────────────────┼────────────────┘         │
│                          │                          │
│                   ┌──────┴──────┐                   │
│                   │    Redis    │                   │
│                   │    :6379    │                   │
│                   └─────────────┘                   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## Environment Variables Reference

### Backend (Required)

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | `sk-ant-...` |
| `DATABASE_URL` | PostgreSQL connection | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | Redis connection | `${{Redis.REDIS_URL}}` |
| `SECRET_KEY` | JWT signing key | Random 32+ chars |
| `ALLOWED_ORIGINS` | CORS origins | Frontend URL |

### Backend (Optional)

| Variable | Description |
|----------|-------------|
| `VOYAGE_API_KEY` | Better vector embeddings |
| `SUNO_API_KEY` | Music generation |
| `DEBUG` | Enable API docs (default: false) |

### Frontend

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `https://backend.railway.app` |

---

## Post-Deployment Checklist

- [ ] PostgreSQL provisioned
- [ ] pgvector extension enabled
- [ ] Redis provisioned
- [ ] Backend deployed and healthy (`/health` returns 200)
- [ ] Frontend deployed
- [ ] CORS configured (frontend can call backend)
- [ ] Custom domain configured (optional)
- [ ] SSL working (automatic with Railway)

---

## Useful Commands

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# View logs
railway logs

# Open shell
railway shell

# Run database migrations
railway run alembic upgrade head
```

---

## Troubleshooting

### "502 Bad Gateway"
- Check backend logs: `railway logs`
- Verify `PORT` is being used correctly
- Check health endpoint: `/health`

### "CORS Error"
- Update `ALLOWED_ORIGINS` with exact frontend URL
- Include protocol: `https://...`

### "Database connection failed"
- Verify `DATABASE_URL` is set
- Check PostgreSQL service is running
- Run migrations: `railway run alembic upgrade head`

### "pgvector not found"
- Connect to PostgreSQL and run: `CREATE EXTENSION vector;`

---

## Estimated Costs

| Service | Usage | Cost |
|---------|-------|------|
| Backend | 2 vCPU, 2GB RAM | ~$10/mo |
| Frontend | Static hosting | ~$0-5/mo |
| PostgreSQL | 1GB | ~$7/mo |
| Redis | 256MB | ~$5/mo |
| **Total** | | **~$22-27/mo** |

Railway offers $5 free credit monthly and usage-based billing.

---

## Next Steps After Deploy

1. **Create first user** - Register at your frontend URL
2. **Test chat** - Send a message to Claude
3. **Add custom domain** - Point your domain to Railway
4. **Monitor usage** - Check Railway dashboard for metrics

---

*The furnace burns eternal. Now it burns in the cloud.* 🔥
