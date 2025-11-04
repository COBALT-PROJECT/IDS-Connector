# ================================================================================
# manager.py
# ================================================================================
"""
Manager - Main management class for Consumer Resource API Server
"""
from fastapi import FastAPI
import logging
from catalog_service import ConsumerCatalogService
from resource_service import ConsumerResourceService
from file_extractor_service import FileExtractorService
from ids_consumer_interface import IDS_ConsumerInterface

logger = logging.getLogger(__name__)


class ConsumerResourceManager:
    """
    Manager class that orchestrates the Consumer Resource API Server
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
            title="IDS Consumer API Server",
            description="IDS Consumer API Server",
            version="1.0.0"
        )
        
        # Initialize services
        self.catalog_service = ConsumerCatalogService(
            consumer_base_url=config['consumer_base_url'],
            username=config['username'],
            password=config['password'],
            self_description_path=config['self_description_path'],
            cache_ttl=config['cache_ttl'],
            request_timeout=config['request_timeout']
        )
        
        self.resource_service = ConsumerResourceService(
            consumer_base_url=config['consumer_base_url'],
            username=config['username'],
            password=config['password'],
            request_timeout=config['request_timeout']
        )
        
        self.file_extractor_service = FileExtractorService()
        
        # Initialize IDS Consumer Interface
        self.ids_interface = IDS_ConsumerInterface(
            catalog_service=self.catalog_service,
            resource_service=self.resource_service,
            file_extractor_service=self.file_extractor_service,
            config=config
        )
        
        # Register routes through the interface
        self.ids_interface.register_routes(self.app)
        
        logger.info("ConsumerResourceManager initialized successfully")
    
    def get_app(self):
        """
        Get the FastAPI application instance
        
        Returns:
            FastAPI: The FastAPI application
        """
        return self.app