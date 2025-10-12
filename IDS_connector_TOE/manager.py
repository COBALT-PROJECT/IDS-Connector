# ================================================================================
# manager.py
# ================================================================================
"""
Manager - Main management class for TOE Provider API Server
"""
from fastapi import FastAPI
import logging
from catalog_service import ProviderCatalogService
from resource_service import ProviderResourceService
from ids_provider_interface import IDS_ProviderInterface

logger = logging.getLogger(__name__)


class TOEProviderManager:
    """
    Manager class that orchestrates the TOE Provider API Server
    """
    
    def __init__(self, config: dict):
        """
        Initialize the Manager with configuration
        
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
        
        # Initialize IDS Provider Interface
        self.ids_interface = IDS_ProviderInterface(
            catalog_service=self.catalog_service,
            resource_service=self.resource_service,
            config=config
        )
        
        # Register routes through the interface
        self.ids_interface.register_routes(self.app)
        
        logger.info("TOEProviderManager initialized successfully")
    
    def get_app(self):
        """
        Get the FastAPI application instance
        
        Returns:
            FastAPI: The FastAPI application
        """
        return self.app