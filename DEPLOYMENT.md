# 🚀 Deployment Guide

This guide covers various deployment options for Rora AI.

## Table of Contents

- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
  - [AWS](#aws-deployment)
  - [Google Cloud Platform](#gcp-deployment)
  - [Azure](#azure-deployment)
  - [Heroku](#heroku-deployment)
  - [Railway](#railway-deployment)
- [Production Considerations](#production-considerations)

## Local Development

### Prerequisites

- Python 3.11+
- Ollama installed and running
- Git

### Setup

```bash
# Clone repository
git clone https://github.com/markotuya0/rora-ai.git
cd rora-ai

# Run setup script
chmod +x setup.sh
./setup.sh

# Or manual setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python create_db.py

# Start services
python api.py                    # Terminal 1
streamlit run app_v2.py          # Terminal 2
```

## Docker Deployment

### Local Docker

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Docker

```bash
# Build production image
docker build -t rora-ai:latest .

# Run API only
docker run -d -p 8000:8000 \
  -e LLM_MODEL=llama3.1:8b \
  --name rora-api \
  rora-ai:latest

# Run with custom database
docker run -d -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e DB_PATH=/app/data/production.db \
  rora-ai:latest
```

## Cloud Deployment

### AWS Deployment

#### Option 1: ECS Fargate

```bash
# Install AWS CLI
pip install awscli

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -t rora-ai .
docker tag rora-ai:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/rora-ai:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/rora-ai:latest

# Create ECS task definition and service via AWS Console or CLI
```

#### Option 2: EC2

```bash
# SSH into EC2 instance
ssh -i key.pem ec2-user@<instance-ip>

# Install Docker
sudo yum update -y
sudo yum install docker -y
sudo service docker start

# Clone and run
git clone https://github.com/markotuya0/rora-ai.git
cd rora-ai
sudo docker-compose up -d
```

#### Environment Variables for AWS

```bash
export DB_PATH=/data/production.db
export LLM_MODEL=llama3.1:8b
export API_HOST=0.0.0.0
export API_PORT=8000
export ALLOWED_ORIGINS=https://yourdomain.com
```

### GCP Deployment

#### Cloud Run

```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud config set project <project-id>

# Build and deploy
gcloud builds submit --tag gcr.io/<project-id>/rora-ai
gcloud run deploy rora-ai \
  --image gcr.io/<project-id>/rora-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars LLM_MODEL=llama3.1:8b
```

#### GKE (Kubernetes)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rora-ai
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rora-ai
  template:
    metadata:
      labels:
        app: rora-ai
    spec:
      containers:
      - name: api
        image: gcr.io/<project-id>/rora-ai:latest
        ports:
        - containerPort: 8000
        env:
        - name: LLM_MODEL
          value: "llama3.1:8b"
        - name: API_HOST
          value: "0.0.0.0"
---
apiVersion: v1
kind: Service
metadata:
  name: rora-ai-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: rora-ai
```

```bash
kubectl apply -f deployment.yaml
```

### Azure Deployment

#### Container Instances

```bash
# Install Azure CLI
# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

# Login
az login

# Create resource group
az group create --name rora-ai-rg --location eastus

# Create container registry
az acr create --resource-group rora-ai-rg \
  --name roraairegistry --sku Basic

# Build and push
az acr build --registry roraairegistry \
  --image rora-ai:latest .

# Deploy container
az container create \
  --resource-group rora-ai-rg \
  --name rora-ai-container \
  --image roraairegistry.azurecr.io/rora-ai:latest \
  --dns-name-label rora-ai \
  --ports 8000 \
  --environment-variables \
    LLM_MODEL=llama3.1:8b \
    API_HOST=0.0.0.0
```

### Heroku Deployment

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Create app
heroku create rora-ai

# Set stack to container
heroku stack:set container

# Deploy
git push heroku main

# Set environment variables
heroku config:set LLM_MODEL=llama3.1:8b
heroku config:set API_HOST=0.0.0.0

# Open app
heroku open
```

Create `heroku.yml`:

```yaml
build:
  docker:
    web: Dockerfile
run:
  web: uvicorn api:app --host 0.0.0.0 --port $PORT
```

### Railway Deployment

1. Visit [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway auto-detects Dockerfile
5. Add environment variables:
   - `LLM_MODEL=llama3.1:8b`
   - `API_HOST=0.0.0.0`
6. Deploy!

Or use Railway CLI:

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize
railway init

# Deploy
railway up
```

## Production Considerations

### Environment Variables

Create a `.env` file (never commit this):

```bash
# Database
# DEMO_MODE=false uses your own database via DB_URI (see docs/DEMO_AND_REAL_DATA.md)
DEMO_MODE=true
DB_URI=
DB_PATH=production.db

# LLM
LLM_MODEL=llama3.1:8b
LLM_TEMPERATURE=0
OLLAMA_BASE_URL=http://localhost:11434

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# Security
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
MAX_QUERY_LENGTH=500

# Monitoring (optional)
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
```

### Database Migration

For production, consider PostgreSQL:

```python
# config.py
DB_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/rora_ai"
)
```

Update `requirements.txt`:
```
psycopg2-binary==2.9.9
```

### Security Checklist

- [ ] Set `ALLOWED_ORIGINS` to specific domains
- [ ] Use HTTPS in production
- [ ] Enable rate limiting
- [ ] Add authentication (JWT)
- [ ] Use environment variables for secrets
- [ ] Enable CORS properly
- [ ] Set up monitoring and logging
- [ ] Regular security updates
- [ ] Database backups
- [ ] Use secrets management (AWS Secrets Manager, etc.)

### Performance Optimization

```python
# Add Redis caching
from redis import Redis
from functools import lru_cache

redis_client = Redis(host='localhost', port=6379)

@lru_cache(maxsize=100)
def cached_query(question: str):
    # Cache query results
    pass
```

### Monitoring

Add health checks and monitoring:

```python
# Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

### Load Balancing

Use Nginx as reverse proxy:

```nginx
upstream rora_api {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://rora_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Scaling

Horizontal scaling with Docker Swarm:

```bash
docker swarm init
docker stack deploy -c docker-compose.yml rora-ai
docker service scale rora-ai_api=5
```

Or Kubernetes:

```bash
kubectl scale deployment rora-ai --replicas=5
```

### Backup Strategy

```bash
# Database backup
docker exec rora-ai-api sqlite3 /app/student_grades.db ".backup '/backup/db_$(date +%Y%m%d).db'"

# Automated backups
0 2 * * * /path/to/backup-script.sh
```

### SSL/TLS

Use Let's Encrypt with Certbot:

```bash
sudo certbot --nginx -d yourdomain.com
```

## Troubleshooting

### Common Issues

**Ollama not connecting:**
```bash
# Check Ollama is running
ollama list

# Pull model
ollama pull llama3.1:8b
```

**Port already in use:**
```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>
```

**Database locked:**
```bash
# Check connections
fuser student_grades.db

# Restart services
docker-compose restart
```

## Support

For deployment issues:
- Open an issue: [GitHub Issues](https://github.com/markotuya0/rora-ai/issues)
- Check documentation: [README.md](README.md)
- Review architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

---

Happy Deploying! 🚀
