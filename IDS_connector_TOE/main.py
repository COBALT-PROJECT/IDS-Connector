# ================================================================================
# main.py - IDS TOE Provider
# ================================================================================
"""
Main Application Entry Point for IDS TOE Provider
"""
import uvicorn
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from manager import TOEProviderManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Configuration with environment variable support
#note: when running as a local app, provider_base_url=https://10.254.3.188:8090, if as a pod: https://tc-provider:8090
CONFIG = {
    # Provider connection
    'provider_base_url': os.environ.get('PROVIDER_BASE_URL', 'https://10.254.3.188:8090'),
    'self_description_path': os.environ.get('SELF_DESCRIPTION_PATH', '/api/selfDescription/'),
    'username': os.environ.get('USERNAME', 'admin'),
    'password': os.environ.get('PASSWORD', 'password'),
    'cache_ttl': int(os.environ.get('CACHE_TTL', '300')),  # 5 minutes
    'request_timeout': int(os.environ.get('REQUEST_TIMEOUT', '30')),

    # Authentication Manager configuration
    'am_base_url': os.environ.get('AM_BASE_URL'),
    'wallet_controller_url': os.environ.get('WALLET_CONTROLLER_URL'),
    'wallet_controller_key': os.environ.get('WALLET_CONTROLLER_KEY'),
    'digital_twin_api_key': os.environ.get('DIGITAL_TWIN_API_KEY'),
}

# Instantiate the Manager class
manager = TOEProviderManager(CONFIG)

# Get the FastAPI app from the manager
app = manager.get_app()

if __name__ == '__main__':
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8005,  # provider on port 8005
        log_level="info"
    )