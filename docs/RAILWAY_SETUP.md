# Railway Deployment - Step by Step Guide

This guide will walk you through deploying Synthora to Railway with **minimum configuration** to get it running first, then add features incrementally.

## Prerequisites

1. A [Railway account](https://railway.app/) (sign up with GitHub)
2. Your repository pushed to GitHub: `https://github.com/RoniAbravaya/synthora`

---

## Phase 1: Minimal Setup (Get It Running)

### Step 1: Create Railway Project

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Select `RoniAbravaya/synthora`
5. Railway will detect the monorepo structure

### Step 2: Add PostgreSQL Database

1. In your project, click **"+ New"** → **"Database"** → **"PostgreSQL"**
2. Railway automatically creates `DATABASE_URL` variable
3. Wait for the database to provision (green status)

### Step 3: Configure Backend Service

1. Click on the GitHub service that was created
2. Go to **Settings** tab
3. Set **Root Directory**: `backend`
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 4: Add Minimum Environment Variables

Go to **Variables** tab and add these (click "Raw Editor" for easier pasting):

```env
# Required - App Config
APP_NAME=Synthora
APP_ENV=production
DEBUG=false
SECRET_KEY=generate-a-random-32-char-string-here-abc123

# Required - CORS (will update after frontend deploys)
CORS_ORIGINS=*

# Required - Encryption (generate with Python)
ENCRYPTION_KEY=your-fernet-key-here

# Placeholder values (app will start but features won't work)
FIREBASE_PROJECT_ID=placeholder
FIREBASE_WEB_API_KEY=placeholder
REDIS_URL=redis://localhost:6379
GCS_BUCKET_NAME=placeholder
GCS_PROJECT_ID=placeholder
STRIPE_SECRET_KEY=sk_test_placeholder
STRIPE_WEBHOOK_SECRET=whsec_placeholder
STRIPE_PRICE_MONTHLY=price_placeholder
STRIPE_PRICE_ANNUAL=price_placeholder
```

### Step 5: Generate Encryption Key

Run this in your terminal to generate a Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output and paste it as `ENCRYPTION_KEY` value.

### Step 6: Deploy Backend

1. Click **"Deploy"** or push a commit to trigger deployment
2. Wait for build to complete (check logs for errors)
3. Once deployed, click the URL (e.g., `synthora-production.up.railway.app`)
4. Test: Visit `https://your-backend-url/docs` - you should see the API docs

### Step 7: Deploy Frontend

1. Click **"+ New"** → **"GitHub Repo"** → Select same repo
2. Go to **Settings** tab
3. Set **Root Directory**: `frontend`
4. Set **Build Command**: `npm ci && npm run build`
5. Set **Start Command**: `npx serve dist -s -l $PORT`

Add these **Variables**:

```env
VITE_API_URL=https://your-backend-url.up.railway.app
VITE_FIREBASE_API_KEY=placeholder
VITE_FIREBASE_AUTH_DOMAIN=placeholder.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=placeholder
```

### Step 8: Update CORS

Once frontend is deployed, go back to **Backend Variables** and update:

```env
CORS_ORIGINS=https://your-frontend-url.up.railway.app
```

---

## Phase 2: Add Real Services

Now that the app is running, add real services one by one.

### Add Firebase Authentication

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or use existing
3. Enable Authentication → Sign-in methods → Email/Password
4. Go to Project Settings → General → Your apps → Add web app
5. Copy the config values

Update **Backend Variables**:
```env
FIREBASE_PROJECT_ID=your-actual-project-id
FIREBASE_WEB_API_KEY=your-actual-api-key
```

For Firebase Admin SDK:
1. Go to Project Settings → Service Accounts
2. Click "Generate new private key"
3. Copy the entire JSON content
4. Add as variable: `FIREBASE_SERVICE_ACCOUNT_JSON` (paste the entire JSON)

Update **Frontend Variables**:
```env
VITE_FIREBASE_API_KEY=your-actual-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-actual-project-id
```

### Add Redis (Upstash)

1. Go to [Upstash Console](https://console.upstash.com/)
2. Create a new Redis database
3. Copy the Redis URL

Update **Backend Variables**:
```env
REDIS_URL=redis://default:password@endpoint.upstash.io:6379
```

### Add Worker Service (Optional - for background jobs)

1. Click **"+ New"** → **"GitHub Repo"** → Select same repo
2. Rename service to "worker"
3. Set **Root Directory**: `backend`
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `python -m rq.cli worker --url $REDIS_URL synthora-default`

Copy all backend variables to worker service.

### Add Stripe (Payments)

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Get API keys from Developers → API Keys
3. Create products and prices

Update **Backend Variables**:
```env
STRIPE_SECRET_KEY=sk_live_your-key
STRIPE_WEBHOOK_SECRET=whsec_your-secret
STRIPE_PRICE_MONTHLY=price_xxx
STRIPE_PRICE_ANNUAL=price_xxx
```

Set up webhook:
1. Go to Developers → Webhooks
2. Add endpoint: `https://your-backend-url/api/v1/subscriptions/webhook`
3. Select events: `checkout.session.completed`, `customer.subscription.*`, `invoice.*`

### Add Google Cloud Storage

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a bucket
3. Create a service account with Storage Admin role
4. Generate JSON key

Update **Backend Variables**:
```env
GCS_BUCKET_NAME=your-bucket-name
GCS_PROJECT_ID=your-project-id
GCS_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```

---

## Troubleshooting

### Build Fails

Check the build logs. Common issues:
- Missing environment variables
- Python version mismatch (ensure Python 3.11+)
- Node version mismatch (ensure Node 18+)

### App Crashes on Start

1. Check runtime logs
2. Verify all required environment variables are set
3. Check database connection

### Database Errors

1. Ensure PostgreSQL is provisioned
2. Check `DATABASE_URL` is automatically set
3. Run migrations manually if needed:
   ```bash
   railway run alembic upgrade head
   ```

### CORS Errors

1. Update `CORS_ORIGINS` with your frontend URL
2. Ensure no trailing slash
3. Redeploy backend after changing

---

## Environment Variables Reference

### Required for Backend to Start

| Variable | Example | Notes |
|----------|---------|-------|
| `DATABASE_URL` | (auto) | Provided by Railway PostgreSQL |
| `SECRET_KEY` | `abc123...` | Random 32+ character string |
| `APP_ENV` | `production` | Must be production/staging/development |
| `ENCRYPTION_KEY` | `abc...=` | Fernet key (generate with Python) |

### Required for Full Functionality

| Variable | Service | Notes |
|----------|---------|-------|
| `FIREBASE_*` | Firebase | Authentication |
| `REDIS_URL` | Upstash | Background jobs |
| `STRIPE_*` | Stripe | Payments |
| `GCS_*` | Google Cloud | Video storage |
| `YOUTUBE_*` | Google | YouTube posting |
| `TIKTOK_*` | TikTok | TikTok posting |
| `META_*` | Meta | Instagram/Facebook |

---

## Quick Commands

```bash
# View logs
railway logs

# Run command in service
railway run python -c "print('hello')"

# Connect to database
railway connect postgres

# Redeploy
railway up
```

---

## Support

If you encounter issues:
1. Check Railway logs for error messages
2. Verify all environment variables are set correctly
3. Test locally with the same environment variables
4. Check the [Railway Documentation](https://docs.railway.app/)
