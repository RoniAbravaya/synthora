#!/bin/bash
# Synthora Backend Deployment Script
# ===================================
# This script runs during deployment to set up the database.

set -e

echo "🚀 Starting Synthora deployment..."

# Run database migrations
echo "📦 Running database migrations..."
python -m alembic upgrade head

echo "✅ Deployment complete!"
