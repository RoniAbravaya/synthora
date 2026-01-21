# Synthora - External Services Setup Guide

This guide walks you through setting up all the external services required for Synthora.

## Table of Contents

1. [Firebase Setup](#1-firebase-setup)
2. [Stripe Setup](#2-stripe-setup)
3. [Google Cloud Storage Setup](#3-google-cloud-storage-setup)
4. [Upstash Redis Setup](#4-upstash-redis-setup)
5. [Railway Deployment](#5-railway-deployment)
6. [Social Media OAuth Setup](#6-social-media-oauth-setup)

---

## 1. Firebase Setup

Firebase handles authentication (Google Sign-In).

### Step 1.1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **"Add project"**
3. Enter project name: `synthora` (or your preferred name)
4. Disable Google Analytics (optional for this project)
5. Click **"Create project"**

### Step 1.2: Enable Google Sign-In

1. In Firebase Console, go to **Authentication** → **Sign-in method**
2. Click **Google** provider
3. Toggle **Enable**
4. Set **Project support email** (your email)
5. Click **Save**

### Step 1.3: Get Web App Configuration

1. In Firebase Console, click the **gear icon** → **Project settings**
2. Scroll to **"Your apps"** section
3. Click **"Add app"** → **Web** (</> icon)
4. Register app name: `synthora-web`
5. Copy the configuration values:

```javascript
// You'll need these values:
apiKey: "AIza..."           → FIREBASE_WEB_API_KEY
authDomain: "xxx.firebaseapp.com" → FIREBASE_AUTH_DOMAIN
projectId: "synthora-xxx"   → FIREBASE_PROJECT_ID
```

### Step 1.4: Generate Service Account Key (Backend)

1. In Firebase Console, click **gear icon** → **Project settings**
2. Go to **Service accounts** tab
3. Click **"Generate new private key"**
4. Save the JSON file securely
5. For Railway: Copy the entire JSON content to `FIREBASE_SERVICE_ACCOUNT_JSON`

### Environment Variables to Set

```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_WEB_API_KEY=your-web-api-key
FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```

---

## 2. Stripe Setup

Stripe handles subscription billing.

### Step 2.1: Create Stripe Account

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Sign up or log in
3. Complete account verification (for production)

### Step 2.2: Get API Keys

1. In Stripe Dashboard, go to **Developers** → **API keys**
2. Copy:
   - **Publishable key** (pk_test_...) → `STRIPE_PUBLISHABLE_KEY`
   - **Secret key** (sk_test_...) → `STRIPE_SECRET_KEY`

> ⚠️ Use **test keys** for development. Switch to **live keys** for production.

### Step 2.3: Create Products and Prices

1. Go to **Products** → **Add product**

**Product 1: Synthora Premium Monthly**
- Name: `Synthora Premium Monthly`
- Description: `Full access to all Synthora features`
- Pricing: `$5.00 USD / month` (Recurring)
- Click **Save product**
- Copy the **Price ID** (price_...) → `STRIPE_PRICE_MONTHLY`

**Product 2: Synthora Premium Annual**
- Name: `Synthora Premium Annual`
- Description: `Full access to all Synthora features - Annual`
- Pricing: `$50.00 USD / year` (Recurring)
- Click **Save product**
- Copy the **Price ID** (price_...) → `STRIPE_PRICE_ANNUAL`

### Step 2.4: Set Up Webhook

1. Go to **Developers** → **Webhooks**
2. Click **"Add endpoint"**
3. Endpoint URL: `https://your-backend-url.railway.app/api/v1/subscriptions/webhook`
4. Select events to listen:
   - `checkout.session.completed`
   - `invoice.paid`
   - `invoice.payment_failed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Click **"Add endpoint"**
6. Copy **Signing secret** (whsec_...) → `STRIPE_WEBHOOK_SECRET`

### Environment Variables to Set

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_MONTHLY=price_...
STRIPE_PRICE_ANNUAL=price_...
```

---

## 3. Google Cloud Storage Setup

GCS stores generated videos and media files.

### Step 3.1: Create GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Note your **Project ID** → `GCS_PROJECT_ID`

### Step 3.2: Enable Cloud Storage API

1. Go to **APIs & Services** → **Enable APIs**
2. Search for "Cloud Storage"
3. Click **"Cloud Storage API"** → **Enable**

### Step 3.3: Create Storage Bucket

1. Go to **Cloud Storage** → **Buckets**
2. Click **"Create bucket"**
3. Configure:
   - Name: `synthora-videos` (must be globally unique) → `GCS_BUCKET_NAME`
   - Location: Choose region close to your users
   - Storage class: Standard
   - Access control: Fine-grained
4. Click **Create**

### Step 3.4: Configure CORS

1. Install Google Cloud CLI or use Cloud Shell
2. Create `cors.json` file:

```json
[
  {
    "origin": ["https://your-frontend-url.railway.app", "http://localhost:5173"],
    "method": ["GET", "PUT", "POST", "DELETE"],
    "responseHeader": ["Content-Type", "Authorization"],
    "maxAgeSeconds": 3600
  }
]
```

3. Apply CORS configuration:
```bash
gsutil cors set cors.json gs://synthora-videos
```

### Step 3.5: Create Service Account

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **"Create service account"**
3. Name: `synthora-storage`
4. Role: **Storage Admin**
5. Click **Done**
6. Click on the service account → **Keys** tab
7. Click **"Add key"** → **Create new key** → **JSON**
8. Save the JSON file securely
9. For Railway: Copy entire JSON to `GCS_SERVICE_ACCOUNT_JSON`

### Environment Variables to Set

```env
GCS_PROJECT_ID=your-gcp-project-id
GCS_BUCKET_NAME=synthora-videos
GCS_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```

---

## 4. Upstash Redis Setup

Upstash provides serverless Redis for the job queue.

### Step 4.1: Create Upstash Account

1. Go to [Upstash Console](https://console.upstash.com/)
2. Sign up or log in

### Step 4.2: Create Redis Database

1. Click **"Create Database"**
2. Configure:
   - Name: `synthora-redis`
   - Type: **Regional**
   - Region: Choose closest to your Railway region
   - Enable **TLS** (recommended)
3. Click **Create**

### Step 4.3: Get Connection URL

1. Click on your database
2. Find **REST API** section
3. Copy the **UPSTASH_REDIS_REST_URL** and **UPSTASH_REDIS_REST_TOKEN**
4. Or use the **Connection String** for standard Redis URL → `REDIS_URL`

### Environment Variables to Set

```env
REDIS_URL=redis://default:your-password@your-endpoint.upstash.io:6379
```

---

## 5. Railway Deployment

### Step 5.1: Create Railway Account

1. Go to [Railway](https://railway.app/)
2. Sign up with GitHub (recommended for auto-deploy)

### Step 5.2: Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Select your `videogenerator` repository
4. Railway will auto-detect the monorepo structure

### Step 5.3: Configure Services

You need to create 3 services from the same repo:

**Service 1: Backend API**
1. Click **"New Service"** → **GitHub Repo**
2. Settings:
   - Root Directory: `/backend`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add all backend environment variables

**Service 2: Frontend**
1. Click **"New Service"** → **GitHub Repo**
2. Settings:
   - Root Directory: `/frontend`
   - Build Command: `npm run build`
   - Start Command: `npm run preview -- --host --port $PORT`
3. Add frontend environment variables (VITE_*)

**Service 3: Worker**
1. Click **"New Service"** → **GitHub Repo**
2. Settings:
   - Root Directory: `/backend`
   - Start Command: `rq worker --url $REDIS_URL synthora`
3. Add same environment variables as backend

### Step 5.4: Add PostgreSQL

1. Click **"New Service"** → **Database** → **PostgreSQL**
2. Railway automatically provides `DATABASE_URL`

### Step 5.5: Configure Environment Variables

In Railway dashboard, add all variables from `.env.example` for each service.

**Important Railway-provided variables:**
- `PORT` - Automatically set
- `DATABASE_URL` - Automatically set by PostgreSQL plugin

**Update URLs after deployment:**
```env
BACKEND_URL=https://synthora-api-production.up.railway.app
FRONTEND_URL=https://synthora-web-production.up.railway.app
CORS_ORIGINS=https://synthora-web-production.up.railway.app
```

---

## 6. Social Media OAuth Setup

### 6.1 YouTube (Google OAuth)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **Credentials**
3. Click **"Create Credentials"** → **OAuth client ID**
4. Application type: **Web application**
5. Name: `Synthora YouTube`
6. Authorized redirect URIs:
   - `http://localhost:8000/api/v1/social-accounts/callback/youtube` (dev)
   - `https://your-backend.railway.app/api/v1/social-accounts/callback/youtube` (prod)
7. Copy **Client ID** and **Client Secret**

**Enable YouTube APIs:**
1. Go to **APIs & Services** → **Library**
2. Enable:
   - YouTube Data API v3
   - YouTube Analytics API

```env
YOUTUBE_CLIENT_ID=your-client-id
YOUTUBE_CLIENT_SECRET=your-client-secret
```

### 6.2 TikTok

1. Go to [TikTok Developer Portal](https://developers.tiktok.com/)
2. Create a new app
3. Add **Login Kit** and **Content Posting API** products
4. Configure redirect URI:
   - `https://your-backend.railway.app/api/v1/social-accounts/callback/tiktok`
5. Submit for review (required for production)

```env
TIKTOK_CLIENT_KEY=your-client-key
TIKTOK_CLIENT_SECRET=your-client-secret
```

### 6.3 Instagram & Facebook (Meta)

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app → **Business** type
3. Add products:
   - **Facebook Login**
   - **Instagram Basic Display** (or Instagram Graph API for business accounts)
4. Configure OAuth redirect URIs:
   - `https://your-backend.railway.app/api/v1/social-accounts/callback/instagram`
   - `https://your-backend.railway.app/api/v1/social-accounts/callback/facebook`
5. Get App ID and App Secret from **Settings** → **Basic**

```env
META_APP_ID=your-app-id
META_APP_SECRET=your-app-secret
```

---

## Quick Checklist

Before deploying, ensure you have:

- [ ] Firebase project with Google Sign-In enabled
- [ ] Firebase service account JSON
- [ ] Stripe account with products created
- [ ] Stripe webhook configured
- [ ] Google Cloud Storage bucket created
- [ ] GCS service account with Storage Admin role
- [ ] Upstash Redis database created
- [ ] Railway project connected to GitHub
- [ ] All environment variables configured in Railway

---

## Troubleshooting

### Firebase Auth Issues
- Ensure authorized domains include your Railway URLs
- Check that Google Sign-In is enabled

### Stripe Webhook Failures
- Verify webhook URL is correct
- Check webhook signing secret matches
- Ensure all required events are selected

### GCS Access Denied
- Verify service account has Storage Admin role
- Check bucket CORS configuration
- Ensure bucket name is correct

### Redis Connection Failed
- Verify TLS is enabled if using Upstash TLS endpoint
- Check connection string format

---

## Support

For additional help:
- [Firebase Documentation](https://firebase.google.com/docs)
- [Stripe Documentation](https://stripe.com/docs)
- [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [Upstash Documentation](https://docs.upstash.com/)
- [Railway Documentation](https://docs.railway.app/)

