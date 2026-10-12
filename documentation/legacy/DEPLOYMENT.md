# Deployment Guide

This guide covers deployment of Vision Assistant for production environments.

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Deployment](#cloud-deployment)
4. [Performance Optimization](#performance-optimization)
5. [Security Hardening](#security-hardening)
6. [Monitoring & Logging](#monitoring--logging)
7. [Backup & Recovery](#backup--recovery)
8. [Scaling](#scaling)

---

## Deployment Options

### Development

**Environment**: Local machine with venv

**Use Case**: Testing, development, daily use

**Setup**:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

---

### Docker Container

**Environment**: Linux container (self-contained)

**Use Case**: Consistent deployment across machines, cloud platforms

**Benefits**:

- Reproducible environment
- Easy to scale horizontally
- Simplified dependency management

---

### Cloud Platform

**Environment**: AWS, Google Cloud, Azure, DigitalOcean

**Use Case**: Always-on service, multi-user access, enterprise deployment

**Benefits**:

- High availability
- Automatic scaling
- Managed services
- Global distribution

---

### Edge/On-Device

**Environment**: User's local devices (mobile, laptop)

**Use Case**: Privacy-first, offline-capable operation

**Benefits**:

- No cloud dependency
- Data stays local
- Works offline
- Lower latency

---

## Docker Deployment

### Dockerfile

Create `Dockerfile` in project root:

```dockerfile
# Use Python image with system libraries
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    libsndfile1 \
    libgomp1 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 visionai
RUN chown -R visionai:visionai /app
USER visionai

# Set environment
ENV PYTHONUNBUFFERED=1
ENV DEVICE=cpu

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import app; print('healthy')" || exit 1

# Run application
CMD ["python", "app.py"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  vision-assistant:
    build: .
    container_name: vision-assistant

    # Volume mounts
    volumes:
      - ./config.yaml:/app/config.yaml
      - ./database:/app/database
      - ./logs:/app/logs
      - /dev/snd:/dev/snd # Audio device
      - /dev/video0:/dev/video0 # Camera device (Linux)

    # Environment variables
    environment:
      - PYTHONUNBUFFERED=1
      - DEVICE=cpu
      - TZ=UTC

    # Port mapping (if using API)
    ports:
      - "8000:8000"

    # Resource limits
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
        reservations:
          cpus: "1"
          memory: 1G

    # Restart policy
    restart: unless-stopped

    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

    # Privileged mode (for audio/camera)
    privileged: true

    # Network mode
    network_mode: host
```

### Build and Run Docker

```bash
# Build image
docker build -t vision-assistant:1.0 .

# Run container
docker run -d \
  --name vision-assistant \
  --device /dev/snd \
  --device /dev/video0 \
  --privileged \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/database:/app/database \
  -v $(pwd)/logs:/app/logs \
  vision-assistant:1.0

# View logs
docker logs -f vision-assistant

# Stop container
docker stop vision-assistant
docker rm vision-assistant
```

### Docker Compose Usage

```bash
# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down

# Rebuild image
docker-compose up -d --build
```

---

## Cloud Deployment

### AWS Deployment

#### EC2 Instance

**Setup**:

```bash
# Launch Ubuntu 22.04 instance (t3.medium minimum)

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Clone repository
git clone <repo-url>
cd aiforus

# Build and run
docker-compose up -d
```

**CloudWatch Monitoring**:

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Configure metrics and logs
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
```

---

### Google Cloud Deployment

#### Cloud Run

**Dockerfile optimized for Cloud Run**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV DEVICE=cpu
ENV PORT=8080

EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
```

**Deploy**:

```bash
# Build and deploy
gcloud run deploy vision-assistant \
  --source . \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600
```

---

### Azure Deployment

#### Container Instances

```bash
# Create resource group
az group create --name vision-ai --location eastus

# Create container
az container create \
  --resource-group vision-ai \
  --name vision-assistant \
  --image vision-assistant:1.0 \
  --cpu 2 \
  --memory 2 \
  --port 8000 \
  --environment-variables \
    DEVICE=cpu \
    PYTHONUNBUFFERED=1
```

---

## Performance Optimization

### Model Optimization

#### Quantization

```python
# Reduce model size and inference speed
import torch
from ultralytics import YOLO

model = YOLO('yolov8n.pt')

# Quantize to INT8
quantized_model = torch.quantization.quantize_dynamic(
    model,
    {torch.nn.Linear},
    dtype=torch.qint8
)
```

#### Model Pruning

```python
# Remove unneeded weights
import torch
from torch.nn.utils import prune

# Prune 30% of weights
for name, module in model.named_modules():
    if isinstance(module, torch.nn.Linear):
        prune.l1_unstructured(module, name='weight', amount=0.3)
```

#### ONNX Export

```python
# Export to ONNX for faster inference
import torch
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.export(format='onnx')
```

### Runtime Optimization

**config.yaml**:

```yaml
ai:
  # Use smaller models in production
  vision_model: yolov8n # nano for speed
  device: cuda # Use GPU if available

  # Batch processing
  batch_size: 4 # Process multiple images

  # Model caching
  cache_models: true

# Reduce detection frequency
vision:
  detection_interval: 2 # seconds
  confidence_threshold: 0.7 # Skip low confidence
```

---

## Security Hardening

### Environment Security

**Secrets Management**:

```bash
# Use environment variables (never commit secrets)
export OPENAI_API_KEY="sk-..."
export DATABASE_URL="postgresql://user:pass@host/db"

# Or use secrets manager
# AWS Secrets Manager
# Google Secret Manager
# HashiCorp Vault
```

**SSL/TLS for APIs**:

```python
# If exposing as API
import ssl

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
ssl_context.load_cert_chain('certificate.pem', 'private_key.pem')

# Use in FastAPI:
# uvicorn app:app --ssl-keyfile=private_key.pem --ssl-certfile=certificate.pem
```

### Data Security

**Database Encryption**:

```python
# Encrypt sensitive data at rest
from sqlalchemy import Column, String
from sqlalchemy_utils import encrypted_type
from cryptography.fernet import Fernet

key = Fernet.generate_key()

class User(Base):
    __tablename__ = "users"
    emergency_contacts = Column(
        encrypted_type.EncryptedType(String, key),
        nullable=True
    )
```

**Data Privacy**:

```python
# Never store sensitive PII longer than needed
def cleanup_old_data():
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(days=90)

    # Delete old conversations
    db.query(ConversationHistory).filter(
        ConversationHistory.created_at < cutoff
    ).delete()

    db.commit()

# Schedule via cron or task scheduler
# 0 1 * * * /usr/bin/python cleanup_old_data.py
```

### Access Control

**Role-Based Access Control (RBAC)**:

```python
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class User(Base):
    role = Column(String, default=UserRole.USER)

def require_role(required_role: UserRole):
    async def check_role(user: User):
        if user.role not in [required_role, UserRole.ADMIN]:
            raise HTTPException(status_code=403)
    return check_role
```

---

## Monitoring & Logging

### Logging Configuration

**Create `logging_config.py`**:

```python
import logging
import logging.handlers
from datetime import datetime

def setup_logging():
    # Create logger
    logger = logging.getLogger('vision_assistant')
    logger.setLevel(logging.DEBUG)

    # File handler (daily rotation)
    file_handler = logging.handlers.RotatingFileHandler(
        f'logs/vision_assistant_{datetime.now():%Y%m%d}.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging()
```

### Monitoring Metrics

**Health Check Endpoint** (FastAPI):

```python
from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.0.0",
        "components": {
            "database": "ok",
            "vision": "ok",
            "speech": "ok"
        }
    }

# Monitor externally
# curl http://localhost:8000/health
```

**Prometheus Metrics**:

```python
from prometheus_client import Counter, Histogram, start_http_server

request_count = Counter(
    'vision_requests_total',
    'Total vision requests',
    ['endpoint']
)

processing_time = Histogram(
    'vision_processing_seconds',
    'Processing time in seconds'
)

# Export metrics
start_http_server(8001)  # Prometheus scrapes from :8001
```

---

## Backup & Recovery

### Database Backup

```bash
# SQLite backup (simple copy)
cp database/vision_assistant.db database/vision_assistant.db.backup

# Scheduled daily backup
0 2 * * * /usr/bin/sqlite3 /app/database/vision_assistant.db ".backup '/backups/vision_$(date +\%Y\%m\%d).db'"
```

**PostgreSQL Backup** (if migrating):

```bash
# Full backup
pg_dump -h localhost -U user database_name > backup.sql

# Restore
psql -h localhost -U user database_name < backup.sql

# Scheduled backup (cron)
0 2 * * * pg_dump -h localhost -U user dbname | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

### Disaster Recovery

**Recovery Procedure**:

```bash
# 1. Stop application
docker stop vision-assistant

# 2. Restore database
cp database/vision_assistant.db.backup database/vision_assistant.db

# 3. Start application
docker start vision-assistant

# 4. Verify
curl http://localhost:8000/health
```

---

## Scaling

### Horizontal Scaling

**Load Balancer Configuration** (Nginx):

```nginx
upstream vision_backend {
    server 10.0.1.10:8000;
    server 10.0.1.11:8000;
    server 10.0.1.12:8000;
}

server {
    listen 80;
    server_name vision.example.com;

    location / {
        proxy_pass http://vision_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Kubernetes Deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vision-assistant
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vision-assistant
  template:
    metadata:
      labels:
        app: vision-assistant
    spec:
      containers:
        - name: vision-assistant
          image: vision-assistant:1.0
          resources:
            requests:
              memory: "1Gi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "2"
          env:
            - name: DEVICE
              value: cpu
```

### Vertical Scaling

**Hardware Upgrades**:

- Increase CPU cores (better parallel processing)
- More RAM (larger model batches)
- GPU acceleration (CUDA: 5-10x faster)

**Example Configurations**:

| Size   | CPU  | RAM     | GPU      | Use Case    |
| ------ | ---- | ------- | -------- | ----------- |
| Small  | 2    | 4GB     | None     | Development |
| Medium | 4    | 8GB     | RTX 2060 | Production  |
| Large  | 8-16 | 16-32GB | A100     | High-load   |

---

## Maintenance

### Regular Updates

```bash
# Update dependencies monthly
pip install --upgrade -r requirements.txt

# Update model weights
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Test updates in staging
docker run -it vision-assistant:dev python -c "import app"
```

### Health Checks

```bash
# Daily health verification
0 0 * * * /usr/bin/curl -f http://localhost:8000/health || alert_team

# Weekly performance check
0 3 * * 0 /usr/bin/python /app/scripts/performance_check.py
```

---

## See Also

- [INSTALLATION.md](./setup/INSTALLATION.md) - Setup guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Debugging issues
- [README.md](../README.md) - Project overview
