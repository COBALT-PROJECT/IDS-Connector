# ================================================================================
# main.py
# ================================================================================
"""
Main Application Entry Point
"""
import uvicorn
import logging
import os
from manager import ConsumerResourceManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Configuration with environment variable support
CONFIG = {
    'consumer_base_url': os.environ.get('CONSUMER_BASE_URL', 'https://tc-consumer:8444'),
    'self_description_path': os.environ.get('SELF_DESCRIPTION_PATH', '/api/selfDescription/'),
    'username': os.environ.get('USERNAME', 'admin'),
    'password': os.environ.get('PASSWORD', 'password'),
    'cache_ttl': int(os.environ.get('CACHE_TTL', '300')),  # 5 minutes
    'request_timeout': int(os.environ.get('REQUEST_TIMEOUT', '30'))
}

# Instantiate the Manager class
manager = ConsumerResourceManager(CONFIG)

# Get the FastAPI app from the manager
app = manager.get_app()

if __name__ == '__main__':
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8004,  # consumer on port 8004
        log_level="info"
    )