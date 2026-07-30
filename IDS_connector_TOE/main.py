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

    # Direct JWT client-credentials configuration
    'auth_base_url': os.environ.get('AUTH_BASE_URL', 'http://iam.cobalt.local:3100'),
    'auth_client_id': os.environ.get('AUTH_CLIENT_ID', 'idstoe'),
    'auth_client_secret': os.environ.get(
        'AUTH_CLIENT_SECRET',
        '3061426b1ae5a36de114580e30f860475e3b9dcc91d15baf125a30cd8c9b7330'
    ),
    'auth_scope': os.environ.get('AUTH_SCOPE', 'digital_twins profile'),
    'auth_db_path': os.environ.get('AUTH_DB_PATH', 'authentication_tokens.db'),
    'auth_introspection_path': os.environ.get('AUTH_INTROSPECTION_PATH', '/oauth/introspect'),
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