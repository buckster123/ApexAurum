#!/bin/bash
# ApexAurum Cloud - Railway Deploy Script
# Usage: RAILWAY_TOKEN=your-token ./deploy.sh

set -e

PROJECT_ID="d0c16492-9f3b-44b1-9d04-209b99c6a683"
API_URL="https://backboard.railway.app/graphql/v2"

if [ -z "$RAILWAY_TOKEN" ]; then
    echo "Error: RAILWAY_TOKEN environment variable not set"
    echo "Get your token from: https://railway.app/account/tokens"
    exit 1
fi

echo "🚂 Deploying ApexAurum Cloud to Railway..."
echo "Project ID: $PROJECT_ID"

# Create backend service from GitHub
echo "Creating backend service..."
curl -s -X POST "$API_URL" \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { serviceCreate(input: { projectId: \"'$PROJECT_ID'\", name: \"backend\", source: { repo: \"buckster123/ApexAurum\" } }) { id name } }"
  }' | jq .

echo ""
echo "🔥 Service created! Configure in Railway dashboard:"
echo "   https://railway.app/project/$PROJECT_ID"
echo ""
echo "Set these variables in the backend service:"
echo "   Root Directory: cloud/backend"
echo "   ANTHROPIC_API_KEY=your-key"
echo "   DATABASE_URL=\${{Postgres.DATABASE_URL}}"
echo "   REDIS_URL=\${{Redis.REDIS_URL}}"
echo "   SECRET_KEY=apexaurum-railway-2026"
echo "   DEBUG=true"
echo "   ALLOWED_ORIGINS=*"
