# IDS TOE Provider API

IDS TOE Provider component that receives data from Trusted Operational Environments (TOE) and posts it to the IDS ToE instance.

## Table of Contents
- [Architecture](#architecture)
- [Components](#components)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Local Development](#local-development)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Testing](#testing)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)

## Architecture

```
TOE → POST data → ids_toe_service:8005 → POST → tc-provider:8090
```

### Data Flow
1. TOE sends IDS TextResource to `ids_toe:8005`
2. `ids_toe` retrieves catalog from `tc-provider:8090`
3. `ids_toe` posts data to `tc-provider:8090/api/offeredResource/` with catalog header
4. `ids_toe` clears cache
5. `ids_toe` fetches updated resources to stay synchronized
6. `ids_toe` returns success confirmation

## Components

### Python Files
- **main.py** - Application entry point, runs on port 8005
- **manager.py** - Orchestrates catalog and resource services
- **catalog_service.py** - Manages catalog operations and caching
- **resource_service.py** - Posts resources to provider and retrieves resource lists
- **ids_provider_interface.py** - FastAPI endpoint handlers

### Configuration Files
- **.env** - Local development configuration (uses IP: `10.254.3.188:8090`) and for Pod configuration reference (uses service name: `tc-provider:8090`)
- **requirements.txt** - Python dependencies
- **Dockerfile** - Container image definition
- **ids_connector_toe_k8s_deployment.yml** - Kubernetes manifests files to deploy the IDS ToE service

### Scripts
- **setup_local.sh** - Sets up local Python environment (one-time)
- **run_local.sh** - Runs application locally for testing
- **build.sh** - Builds Docker image and loads into K3s
- **deploy.sh** - Deploys to Kubernetes cluster
- **post_ids_toe_wrapper.py** - Test script for POST endpoint

## Prerequisites

### For Local Development
- Python 3.11+
- pip and venv
- Access to `tc-provider` (within the cluster) at `10.254.3.188:8090` (from outside the cluster)

### For Kubernetes Deployment
- K3s cluster (or kind/minikube)
- kubectl configured
- Docker
- `tc-provider` service running in same namespace

## Quick Start

### Local Development (Recommended for first-time testing)

```bash
# 1. Setup environment (one-time)
chmod +x setup_local.sh
./setup_local.sh

# 2. Review/edit configuration
nano .env

# 3. Run locally
chmod +x run_local.sh
./run_local.sh

# 4. Test (in another terminal)
python3 test_post_to_ids_toe.py
```

### Kubernetes Deployment

```bash
# 1. Build Docker image and load to K3s
chmod +x build.sh
./build.sh

# 2. Deploy to K3s
chmod +x deploy.sh
./deploy.sh

# 3. Check status
kubectl get pods -l app=ids-connector-toe
kubectl logs -f deployment/ids-connector-toe-deployment
```

## Local Development

### Initial Setup

```bash
# Make scripts executable
chmod +x setup_local.sh run_local.sh

# Run setup (creates venv, installs dependencies, creates .env)
./setup_local.sh
```

This creates:
- Python virtual environment in `./venv/`
- `.env` file with local configuration

### Configuration

Edit `.env` to match your environment:

```bash
# Provider Connection (use direct IP for local development)
PROVIDER_BASE_URL=https://10.254.3.188:8090
SELF_DESCRIPTION_PATH=/api/selfDescription/

# Authentication
USERNAME=admin
PASSWORD=password

# Cache and Timeout Settings
CACHE_TTL=300
REQUEST_TIMEOUT=30

# Server Settings
HOST=0.0.0.0
PORT=8005
LOG_LEVEL=info
```

### Running Locally

```bash
# Start the server
./run_local.sh

# Access the API
# - API: http://localhost:8005
# - Docs: http://localhost:8005/docs
# - Health: http://localhost:8005/health
```

### Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.

## Kubernetes Deployment

### Step 1: Build Docker Image

```bash
chmod +x build.sh
./build.sh
```

**What this does:**
- Builds Docker image: `ids-connector-toe:v1.0.0`
- Detects your K3s cluster
- Imports image: `docker save ids-connector-toe:v1.0.0 | sudo k3s ctr images import -`

**Expected output:**
```
Starting IDS TOE Provider API build process...
Step 1: Building Docker image...
[+] Building...
Docker image built successfully!
Step 2: Loading Docker image to Kubernetes...
Detected K3s cluster. Importing image...
Image imported to K3s successfully!
Build process completed successfully!
```

### Step 2: Deploy to Kubernetes

```bash
chmod +x deploy.sh
./deploy.sh
```

**What this does:**
- Creates ConfigMap with `tc-provider:8090` URL
- Creates Secret with credentials
- Creates Deployment (1 replica)
- Creates Service (ClusterIP)
- Waits for pod to be ready
- Shows deployment status

**Expected output:**
```
Starting IDS TOE Provider API deployment process...
Step 1: Applying Kubernetes manifests...
Kubernetes resources created successfully!
Step 2: Waiting for deployment to be ready...
Deployment is ready!
Step 3: Deployment Status:
NAME                                            READY   STATUS    RESTARTS   AGE
ids-connector-toe-deployment-xxxxx-yyyyy        1/1     Running   0          30s
tc-provider-xxxxxxxxx-yyyyy                     1/1     Running   0          40s
```

### Step 3: Verify Deployment

```bash
# Check pods
kubectl get pods -l app=ids-connector-toe

# Check logs (should show startup sequence)
kubectl logs -f deployment/ids-connector-toe-deployment

# Expected log output:
# ============================================================
# Starting IDS TOE Provider API Server
# ============================================================
# Initial catalog value: https://w3id.org/idsa/autogen/resourceCatalog/...
# ✓ Found 2 TextResources in Provider catalog
# Resource retrieval complete: 2/2 successful
# Initial text resources count from provider: 2
```

### Step 4: Access the Service

**Within the cluster:**
```bash
# Other pods can access at:
http://ids-connector-toe-service:8005
```

**From outside the cluster (for testing):**
```bash
# Port forward to localhost
kubectl port-forward service/ids-connector-toe-service 8005:8005

# Access at:
# - API: http://localhost:8005
# - Docs: http://localhost:8005/docs
```

## Testing

### Test Script

Use the provided test script to send sample data:

```bash
python3 post_ids_toe_wrapper.py
```

**Expected output:**
```
======================================================================
POST Request to IDS TOE Provider
======================================================================
URL: http://localhost:8005/api/IDSconnector/post_data
Resource ID: test-resource-20251012-144943
Timestamp: 2025-10-12T14:49:43.813729Z

Sending request...
======================================================================

Response Status Code: 200
----------------------------------------------------------------------
✓ SUCCESS! Data posted to IDS TOE successfully
```

### Manual Testing with curl

```bash
# Health check
curl http://localhost:8005/health

# Get provider info
curl http://localhost:8005/api/IDSconnector/TOE/info

# Post data (example)
curl -X POST http://localhost:8005/api/IDSconnector/post_data \
  -H "Content-Type: application/json" \
  -d '{
    "data_type": "json",
    "data": "{\"@type\":\"ids:TextResource\",\"@id\":\"test-123\"}"
  }'

# Clear cache
curl -X POST http://localhost:8005/api/IDSconnector/clear-cache
```

### Checking Logs

```bash
# Follow logs in real-time
kubectl logs -f deployment/ids-connector-toe-deployment

# Get last 100 lines
kubectl logs --tail=100 deployment/ids-connector-toe-deployment

# Logs from previous pod (if crashed)
kubectl logs --previous deployment/ids-connector-toe-deployment
```

## Configuration

### Environment Variables

| Variable | Local | Pod | Description |
|----------|-------|-----|-------------|
| PROVIDER_BASE_URL | https://10.254.3.188:8090 | https://tc-provider:8090 | Provider URL |
| SELF_DESCRIPTION_PATH | /api/selfDescription/ | /api/selfDescription/ | Self-description path |
| USERNAME | admin | admin | Basic auth username |
| PASSWORD | password | password | Basic auth password |
| CACHE_TTL | 300 | 300 | Cache TTL in seconds |
| REQUEST_TIMEOUT | 30 | 30 | Request timeout in seconds |
| HOST | 0.0.0.0 | 0.0.0.0 | Server host |
| PORT | 8005 | 8005 | Server port |
| LOG_LEVEL | info | info | Logging level |

### Kubernetes Configuration

Edit `ids_connector_toe_k8s_deployment.yml` to customize:

```yaml
# ConfigMap - Change provider URL or settings
data:
  PROVIDER_BASE_URL: "https://tc-provider:8090"
  CACHE_TTL: "300"

# Secret - Change credentials
stringData:
  username: admin
  password: password

# Deployment - Change resources
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## API Endpoints

### POST /api/IDSconnector/post_data
Posts data from TOE to the IDS ToE instance.

**Request:**
```json
{
  "data_type": "json",
  "data": "<IDS TextResource as JSON string>"
}
```

**Response (200):**
```json
{
  "data_type": "json",
  "data": "<same data echoed back>"
}
```

**Workflow:**
1. Posts data to `/api/IDSconnector/post_data`
2. Clears catalog cache
3. Fetches all updated resources
4. Returns confirmation

### GET /health
Health check endpoint.

**Response (200):**
```json
{
  "status": "healthy",
  "service": "IDS TOE Provider API Server",
  "provider": "https://tc-provider:8090"
}
```

### GET /api/IDSconnector/TOE/info
Provider information.

**Response (200):**
```json
{
  "provider_base_url": "https://tc-provider:8090",
  "username": "admin",
  "timeout": 30,
  "catalog_cache_ttl": 300
}
```

### POST /api/IDSconnector/clear-cache
Clears the catalog cache.

**Response (200):**
```json
{
  "message": "Catalog cache cleared successfully"
}
```

## Troubleshooting

### Image Pull Error (ErrImagePull)

**Problem:**
```
Failed to pull image "ids-connector-toe:latest"
```

**Solution:**
```bash
# Run build.sh to create and import the image
./build.sh

# Or manually import
docker save ids-connector-toe:latest | sudo k3s ctr images import -

# Verify image is in K3s
sudo k3s ctr images ls | grep ids-connector-toe

# Delete failed deployment and redeploy
kubectl delete deployment ids-connector-toe-deployment
./deploy.sh
```

### Connection Refused to Provider

**Problem:**
```
Error posting resource to provider: Connection refused
```

**Solution:**
- Verify tc-provider is running: `kubectl get pods | grep tc-provider`
- Check service exists: `kubectl get svc tc-provider`
- Verify port is correct (8090)
- Check provider logs: `kubectl logs <tc-provider-pod>`

### Pod CrashLoopBackOff

**Problem:**
```
NAME                                            READY   STATUS             RESTARTS   AGE
ids-connector-toe-deployment-xxxxx-yyyyy        0/1     CrashLoopBackOff   5          5m
```

**Solution:**
```bash
# Check logs for error messages
kubectl logs deployment/ids-connector-toe-deployment

# Check previous container logs
kubectl logs --previous deployment/ids-connector-toe-deployment

# Describe pod for events
kubectl describe pod <pod-name>

# Common issues:
# - Missing Python dependencies (rebuild image)
# - Wrong PROVIDER_BASE_URL (check ConfigMap)
# - Provider not accessible (check network)
```

### 404 Not Found from Provider

**Problem:**
```
Provider returned status 404: No message available
```

**Solution:**
- Verify endpoint: Should be `/api/offeredResource/`
- Check provider is IDS-compliant
- Verify catalog value is correct
- Check provider logs for rejected requests

### Local Development Issues

**Problem:** `python3: command not found`

**Solution:**
```bash
# Install Python 3.11+
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**Problem:** `Permission denied` on scripts

**Solution:**
```bash
chmod +x setup_local.sh run_local.sh build.sh deploy.sh
```

**Problem:** Cannot connect to provider locally

**Solution:**
- Check `.env` has correct IP: `PROVIDER_BASE_URL=https://10.254.3.188:8090`
- Verify provider is accessible: `curl -k https://10.254.3.188:8090/health`
- Check firewall rules

## Directory Structure

```
ids_toe/
├── main.py                              # Entry point
├── manager.py                           # Service orchestrator
├── catalog_service.py                   # Catalog operations
├── resource_service.py                  # Resource posting/retrieval
├── ids_provider_interface.py            # API endpoints
├── requirements.txt                     # Python dependencies
├── Dockerfile                           # Container image
├── .env                                 # Local config (gitignored)
├── ids_connector_toe_k8s_deployment.yml # K8s manifests
├── be-dataapp-provider-configmap.yaml
├── ca-pemstore.yaml
├── ecc-provider-configmap-v.2.yaml
├── provider-compiled-v-0.3.yaml
├── setup_local.sh                       # Local setup script
├── run_local.sh                         # Local run script
├── build.sh                             # Build & load image
├── deploy.sh                            # Deploy to K8s
├── test_post_to_ids_toe.py              # Test script
├── README.md                            # This file
└── venv/                                # Virtual environment (created by setup)
```

## Startup Behavior

On startup, `ids_toe`:
1. Connects to `tc-provider:8090`
2. Fetches catalog value from `/api/selfDescription/`
3. Retrieves all text resources from provider
4. Logs synchronization status

**Example startup logs:**
```
============================================================
Starting IDS TOE Provider API Server
============================================================
✓ Catalog value retrieved: https://w3id.org/idsa/autogen/resourceCatalog/...
✓ Found 2 TextResources in Provider catalog
Retrieving details for 2 text resources...
[1/2] Fetching: 62e0faac-7494-4ea7-9653-51923855ea01
  ✓ Successfully retrieved 62e0faac-7494-4ea7-9653-51923855ea01
[2/2] Fetching: a23a753a-a444-497c-a359-47ca3257a9af
  ✓ Successfully retrieved a23a753a-a444-497c-a359-47ca3257a9af
Resource retrieval complete: 2/2 successful
Initial text resources count from provider: 2
```

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs: `kubectl logs -f deployment/ids-connector-toe-deployment`
3. Verify configuration in ConfigMap and Secret
4. Test locally first before deploying to K8s

## License

MIT Apache License