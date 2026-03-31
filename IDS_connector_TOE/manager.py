# ================================================================================
# manager.py
# ================================================================================
"""
Manager - Main management class for TOE Provider API Server
"""
import threading
import logging
from fastapi import FastAPI
from catalog_service import ProviderCatalogService
from resource_service import ProviderResourceService
from ids_provider_interface import IDS_ProviderInterface
from toe_authentication_manager import TOEAuthenticationManager

logger = logging.getLogger(__name__)


class TOEProviderManager:
    """
    Manager class that orchestrates the TOE Provider API Server
    """
    
    def __init__(self, config: dict):
        """
        Initialize the Manager with configuration.

        During initialization the authentication flow is started in a
        background thread so the FastAPI server can begin accepting
        requests immediately.  The access token will be available once
        the wallet registration + AM polling + OAuth2 exchange completes.
        
        Args:
            config: Dictionary containing configuration parameters
        """
        self.config = config
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="IDS TOE Provider API Server",
            description="IDS TOE Provider API Server",
            version="1.0.0"
        )
        
        # Initialize services
        self.catalog_service = ProviderCatalogService(
            provider_base_url=config['provider_base_url'],
            username=config['username'],
            password=config['password'],
            self_description_path=config['self_description_path'],
            cache_ttl=config['cache_ttl'],
            request_timeout=config['request_timeout']
        )
        
        self.resource_service = ProviderResourceService(
            provider_base_url=config['provider_base_url'],
            username=config['username'],
            password=config['password'],
            request_timeout=config['request_timeout']
        )

        # Initialize TOE Authentication Manager
        self.auth_manager = TOEAuthenticationManager(
            am_base_url=config.get('am_base_url'),
            wallet_controller_url=config.get('wallet_controller_url'),
            wallet_controller_key=config.get('wallet_controller_key'),
            digital_twin_api_key=config.get('digital_twin_api_key'),
        )
        logger.info("TOE Authentication Manager has been instantiated")

        # Start the authentication flow in a background thread so that
        # the server can start serving requests while the (potentially
        # slow) wallet registration + AM polling completes.
        self._auth_thread = threading.Thread(
            target=self._run_auth_flow,
            daemon=True,
            name="toe-auth",
        )
        self._auth_thread.start()
        logger.info("Authentication flow started in background thread")

        # Initialize IDS Provider Interface
        self.ids_interface = IDS_ProviderInterface(
            catalog_service=self.catalog_service,
            resource_service=self.resource_service,
            config=config,
            auth_manager=self.auth_manager,
        )
        
        # Register routes through the interface
        self.ids_interface.register_routes(self.app)
        
        logger.info("TOEProviderManager initialized successfully")

    def _run_auth_flow(self):
        """
        Execute the full authentication flow in a background thread:
          1. Register with wallet controller
          2. Poll AM until credential is issued
          3. Fetch OAuth2 access token
          4. Store token in memory via TOEAuthenticationManager
        """
        try:
            success, access_token = self.auth_manager.register_and_get_token()

            if success and access_token:
                logger.info(
                    f"IDS-TOE authentication completed — "
                    f"toe_id={self.auth_manager.get_toe_id()}"
                )
            else:
                logger.error(
                    "IDS-TOE authentication flow failed — "
                    "component will run without an access token"
                )
        except Exception as e:
            logger.error(f"IDS-TOE authentication flow exception: {e}")

    def get_app(self):
        """
        Get the FastAPI application instance
        
        Returns:
            FastAPI: The FastAPI application
        """
        return self.app