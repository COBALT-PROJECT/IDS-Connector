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
from auth_token_store import AuthTokenStore
from authentication_manager import AuthenticationManager

logger = logging.getLogger(__name__)


class TOEProviderManager:
    """
    Manager class that orchestrates the TOE Provider API Server
    """
    
    def __init__(self, config: dict):
        """
        Initialize the Manager with configuration.

        During initialization the IDS-TOE service fetches its own IAM JWT
        in a background thread and stores it in SQLite.
        
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

        self.auth_token_store = AuthTokenStore(
            db_path=config.get('auth_db_path', 'authentication_tokens.db')
        )
        self.authentication_manager = AuthenticationManager(
            auth_base_url=config.get('auth_base_url', 'http://iam.cobalt.local:3100'),
            client_id=config.get('auth_client_id', 'idstoe'),
            client_secret=config.get('auth_client_secret'),
            scope=config.get('auth_scope', 'digital_twins profile'),
            request_timeout=config['request_timeout'],
            token_store=self.auth_token_store,
            token_validation_path=config.get('auth_token_validation_path', '/oauth/userinfo'),
        )
        logger.info("AuthenticationManager has been instantiated")

        self._jwt_thread = threading.Thread(
            target=self._run_jwt_refresh,
            daemon=True,
            name="ids-toe-jwt",
        )
        self._jwt_thread.start()
        logger.info("AuthenticationManager JWT refresh started in background thread")

        # Initialize IDS Provider Interface
        self.ids_interface = IDS_ProviderInterface(
            catalog_service=self.catalog_service,
            resource_service=self.resource_service,
            config=config,
            authentication_manager=self.authentication_manager,
        )
        
        # Register routes through the interface
        self.ids_interface.register_routes(self.app)
        
        logger.info("TOEProviderManager initialized successfully")

    def _run_jwt_refresh(self):
        """
        Fetch IDS-TOE's own JWT from IAM and store it in SQLite.
        """
        try:
            metadata = self.authentication_manager.refresh_jwt()
            logger.info(
                "IDS-TOE JWT acquired and stored - "
                f"expires_at={metadata.get('expires_at')}"
            )
        except Exception as e:
            logger.error(f"IDS-TOE JWT refresh failed: {e}")

    def get_app(self):
        """
        Get the FastAPI application instance
        
        Returns:
            FastAPI: The FastAPI application
        """
        return self.app