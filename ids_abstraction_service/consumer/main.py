# ================================================================================
# main.py
# ================================================================================
"""
Main Application Entry Point
"""
import uvicorn
import logging
from manager import ConsumerResourceManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Configuration
CONFIG = {
    'consumer_base_url': 'https://10.254.3.188:8444',
    'self_description_path': '/api/selfDescription/',
    'username': 'admin',
    'password': 'password',
    'cache_ttl': 300,  # 5 minutes
    'request_timeout': 30
}

# Instantiate the Manager class
manager = ConsumerResourceManager(CONFIG)

# Get the FastAPI app from the manager
app = manager.get_app()

if __name__ == '__main__':
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,  # consumer on port 8004
        reload=True,
        log_level="info"
    )