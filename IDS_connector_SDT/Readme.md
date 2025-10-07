# IDS SDT Connector Pod Deployment Guide

## Overview
The IDS SDT Connector is a FastAPI-based service that interfaces with IDS Consumer of trueconnector to retrieve and serve resource data. This service acts as an abstraction layer for accessing IDS Consumer resources through a standardized API.

## Prerequisites
- Docker installed on your system
- Kubernetes cluster (K3s/K8s) running
- kubectl configured to access your cluster
- Python 3.11+ (for local development only)

## Quick Start

### 1. Clone/Copy the Files
Ensure you have all the required files in your project directory:
```
ids-consumer-api/
├── main.py
├── manager.py
├── catalog_service.py
├── resource_service.py
├── ids_consumer_interface.py
├── requirements.txt
├── Dockerfile
├── .env
├── docker-compose.yaml
├── ids_connector_sdt_k8s_deployment.yml
├── build_and_deploy.sh
├── deploy.sh
├── quick_redeploy.sh
├── port_forward.sh
└── port_forward_remote.sh
```

### 2. Build and Deploy (First Time)
```bash
# Make scripts executable
sudo chmod +x build_and_deploy.sh deploy.sh quick_redeploy.sh port_forward.sh port_forward_remote.sh

# Build Docker image and deploy to Kubernetes
./build_and_deploy.sh
```

### 3. Subsequent Deployments
If the Docker image is already built:
```bash
./deploy.sh
```

### 4. Access the API
After deployment, start port forwarding to access the API:
```bash
# Local access only
./port_forward.sh

# OR for remote access (from other machines)
./port_forward_remote.sh
```

Then access:
- **API Documentation**: http://localhost:8004/docs
- **Alternative Docs**: http://localhost:8004/redoc
- **Health Check**: http://localhost:8004/health
- **Consumer Info**: http://localhost:8004/api/IDSconnector/SDT/info

To run, execute the following commands:
```bash
kubectl apply -f ids_connector_sdt_k8s_deployment.yml (or ./deploy.sh)
./quick_redeploy.sh
```

## API Endpoints

### Main Endpoints
- `GET /api/IDSconnector/get_data_request` - Retrieve resource data
  - Query Parameters:
    - `toe_id`: Entity to be synchronized with (required)
    - `data_type`: Data format (json/csv) (required)
    - `data_path`: Resource path or "all" for all resources (required)
  
- `GET /api/IDSconnector/SDT/info` - Get consumer configuration info
- `POST /api/IDSconnector/clear-cache` - Clear resource cache
- `GET /health` - Health check endpoint

### Example API Calls
```bash
# Get all resources as JSON
curl "http://localhost:8004/api/IDSconnector/get_data_request?toe_id=test&data_type=json&data_path=all"

# Get specific resource
curl "http://localhost:8004/api/IDSconnector/get_data_request?toe_id=test&data_type=json&data_path=resource-name"

# Check health
curl http://localhost:8004/health

# Get consumer info
curl http://localhost:8004/api/IDSconnector/SDT/info
```

## Deployment Scripts

### build_and_deploy.sh
Builds Docker image and deploys to Kubernetes. Use for initial deployment or after code changes.

### deploy.sh
Deploys to Kubernetes using existing Docker image. Use for redeployment without rebuilding.

### quick_redeploy.sh
Quickly restarts the deployment with the same image. Useful for applying config changes.

### port_forward.sh
Sets up local port forwarding to access the API from localhost.

### port_forward_remote.sh
Sets up port forwarding on all interfaces for remote access.

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -l app=ids-consumer-api
```

### View Logs
```bash
kubectl logs -f deployment/ids-consumer-api
```

### Pod Not Starting (ImagePullBackOff)
If using K3s, import the Docker image:
```bash
docker save ids-consumer-api:latest | sudo k3s ctr images import -
```

### Connection Issues to tc-consumer
1. Verify tc-consumer service is running:
```bash
kubectl get svc tc-consumer
```

2. Check if the pod can resolve tc-consumer:
```bash
kubectl exec -it deployment/ids-consumer-api -- nslookup tc-consumer
```

3. Verify credentials in the secret:
```bash
kubectl get secret ids-consumer-secret -o yaml
```

### Clear and Restart
If you need to completely remove and redeploy:
```bash
# Delete all resources
kubectl delete -f ids_connector_sdt_k8s_deployment.yml

# Redeploy
./deploy.sh
```

## Local Development

### Using Docker Compose
For local development and testing:
```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Running Directly with Python
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Architecture

The IDS SDT Connector consists of:

1. **ConsumerCatalogService**: Handles catalog retrieval and caching
2. **ConsumerResourceService**: Manages resource fetching and caching
3. **IDS_ConsumerInterface**: FastAPI endpoint handlers
4. **ConsumerResourceManager**: Orchestrates all services

The service communicates with the tc-consumer pod internally within the Kubernetes cluster, caches responses for performance, and provides a RESTful API for external access.

## Security Notes

- The service uses Basic Authentication to connect to tc-consumer
- SSL/TLS verification is disabled for internal cluster communication
- Credentials are stored in Kubernetes Secrets
- The pod runs as a non-root user (appuser) for security

## Performance

- Resources are cached for 5 minutes (configurable via CACHE_TTL)
- Initial resource fetch may take time depending on the number of resources
- Use the `/api/IDSconnector/clear-cache` endpoint to force refresh

## Support

For issues or questions:
1. Check pod logs: `kubectl logs -f deployment/ids-connector-sdt-deployment`
2. Ensure all required environment variables are set
3. Check network connectivity within the cluster