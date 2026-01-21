# Synthora Deployment Guide

This guide explains how to deploy Synthora to Railway.

## Prerequisites

Before deploying, you need:

1. **GitHub Repository** - Your code pushed to GitHub
2. **Railway Account** - Sign up at [railway.app](https://railway.app)
3. **External Services** (set up before deploying):
   - Firebase project (Authentication)
   - Stripe account (Payments)
   - Upstash Redis (Queue)
   - Google Cloud Storage bucket (Video storage)

## Architecture Overview

Synthora consists of 4 services on Railway:

```
┌─────────────────────────────────────────────────────────────┐
│                        Railway Project                       │
├─────────────────┬─────────────────┬─────────────────────────┤
│    Frontend     │     Backend     │    Worker    │ Postgres │
│   (React SPA)   │   (FastAPI)     │  (RQ Worker) │   (DB)   │
│   Port: 443     │   Port: 8000    │   No Port    │  5432    │
└─────────────────┴─────────────────┴─────────────────────────┘
                           │
                           ▼
                    Upstash Redis
                    (External)
```

## Step-by-Step Deployment

### 1. Create Railway Project

1. Go to [railway.app](https://railway.app) and sign in
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Connect your GitHub account and select the `synthora` repository

### 2. Add PostgreSQL Database

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway will automatically provide `DATABASE_URL`

### 3. Create Backend Service

1. Click **"+ New"** → **"GitHub Repo"**
2. Select your repo
3. Set **Root Directory**: `backend`
4. Railway will auto-detect Python

**Environment Variables for Backend:**

```env
# App
APP_ENV=production
DEBUG=false
SECRET_KEY=<generate-a-strong-32-char-key>
BACKEND_URL=https://your-backend.up.railway.app
FRONTEND_URL=https://your-frontend.up.railway.app

# Database (auto-provided by Railway)
# DATABASE_URL=postgresql://...

# Redis (from Upstash)
REDIS_URL=redis://default:xxx@xxx.upstash.io:6379

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_WEB_API_KEY=your-api-key
FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}

# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_MONTHLY_PRICE_ID=price_xxx
STRIPE_ANNUAL_PRICE_ID=price_xxx

# Google Cloud Storage
GCS_BUCKET_NAME=synthora-videos
GCS_PROJECT_ID=your-gcp-project
GCS_CREDENTIALS_JSON={"type":"service_account",...}

# Encryption
ENCRYPTION_KEY=<generate-fernet-key>

# Social OAuth (optional, for posting)
YOUTUBE_CLIENT_ID=xxx
YOUTUBE_CLIENT_SECRET=xxx
TIKTOK_CLIENT_KEY=xxx
TIKTOK_CLIENT_SECRET=xxx
META_APP_ID=xxx
META_APP_SECRET=xxx
```

### 4. Create Worker Service

1. Click **"+ New"** → **"GitHub Repo"**
2. Select your repo (same as backend)
3. Set **Root Directory**: `backend`
4. **Override Start Command**: 
   ```
   python -m rq.cli worker --url $REDIS_URL synthora-default synthora-video
   ```
5. Copy all environment variables from Backend service

### 5. Create Frontend Service

1. Click **"+ New"** → **"GitHub Repo"**
2. Select your repo
3. Set **Root Directory**: `frontend`
4. Railway will auto-detect Node.js

**Environment Variables for Frontend:**

```env
VITE_API_URL=https://your-backend.up.railway.app
VITE_FIREBASE_API_KEY=your-firebase-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
```

### 6. Configure Domains

1. Go to each service's **Settings** → **Networking**
2. Click **"Generate Domain"** for each service
3. Note down the URLs:
   - Backend: `https://synthora-api.up.railway.app`
   - Frontend: `https://synthora-web.up.railway.app`

### 7. Update CORS Settings

Update the backend's `FRONTEND_URL` environment variable with the actual frontend URL.

### 8. Configure Stripe Webhook

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-backend.up.railway.app/api/v1/subscriptions/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the webhook secret to `STRIPE_WEBHOOK_SECRET`

## Generating Secrets

### SECRET_KEY (32+ characters)
```python
import secrets
print(secrets.token_urlsafe(32))
```

### ENCRYPTION_KEY (Fernet key)
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

## Monitoring & Logs

- View logs: Railway Dashboard → Service → Logs
- View metrics: Railway Dashboard → Service → Metrics
- Set up alerts: Railway Dashboard → Project Settings → Alerts

## Troubleshooting

### Database Connection Issues
- Ensure `DATABASE_URL` is correctly set
- Check if PostgreSQL service is running

### Worker Not Processing Jobs
- Verify `REDIS_URL` is correct
- Check worker logs for errors
- Ensure queues match between backend and worker

### Frontend Can't Reach Backend
- Verify `VITE_API_URL` points to backend URL
- Check CORS settings in backend
- Ensure backend is running and healthy

### Stripe Webhooks Failing
- Verify webhook secret is correct
- Check webhook endpoint URL
- View failed webhook attempts in Stripe Dashboard

## Scaling

To scale services:

1. Go to service **Settings** → **Scaling**
2. Increase **Replicas** (horizontal scaling)
3. Increase **Memory/CPU** (vertical scaling)

## Custom Domain

1. Go to service **Settings** → **Networking**
2. Click **"+ Custom Domain"**
3. Add your domain (e.g., `api.synthora.app`)
4. Configure DNS records as shown
5. Wait for SSL certificate provisioning

## Rollback

To rollback a deployment:

1. Go to service **Deployments**
2. Find the previous working deployment
3. Click **"Redeploy"**
