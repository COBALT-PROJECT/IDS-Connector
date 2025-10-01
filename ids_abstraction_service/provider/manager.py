"""
Manager - Main management class for IDS TrueConnector API Relay Server
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
from catalog_service import CatalogService
from relay_manager import RelayManager

logger = logging.getLogger(__name__)


class Manager:
    """
    Manager class that orchestrates the entire IDS TrueConnector API Relay Server
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
            title="IDS TrueConnector API Relay Server",
            description="Relay server for IDS TrueConnector with dynamic catalog management",
            version="1.0.0"
        )
        
        # Initialize services
        self.catalog_service = CatalogService(
            provider_base_url=config['provider_base_url'],
            username=config['username'],
            password=config['password'],
            self_description_path=config['self_description_path'],
            cache_ttl=config['cache_ttl'],
            request_timeout=config['request_timeout']
        )
        
        self.relay_manager = RelayManager(
            catalog_service=self.catalog_service,
            provider_base_url=config['provider_base_url'],
            username=config['username'],
            password=config['password'],
            request_timeout=config['request_timeout']
        )
        
        # Register routes
        self._register_routes()
        
        logger.info("Manager initialized successfully")
    
    def _register_routes(self):
        """Register all FastAPI routes"""
        
        # Startup event
        @self.app.on_event("startup")
        async def startup_event():
            await self._startup()
        
        # Management endpoints
        @self.app.get("/health")
        async def health():
            return await self._health()
        
        @self.app.get("/provider/info")
        async def provider_info():
            return await self._provider_info()
        
        # IDS TrueConnector API endpoints
        @self.app.post("/api/offeredResource/")
        async def create_offered_resource(request: Request):
            return await self._create_offered_resource(request)
        
        @self.app.get("/api/offeredResource/")
        async def list_offered_resources(request: Request):
            return await self._list_offered_resources(request)
        
        @self.app.get("/api/offeredResource/{resource_id}")
        async def get_offered_resource(resource_id: str, request: Request):
            return await self._get_offered_resource(resource_id, request)
        
        @self.app.put("/api/offeredResource/{resource_id}")
        async def update_offered_resource(resource_id: str, request: Request):
            return await self._update_offered_resource(resource_id, request)
        
        @self.app.delete("/api/offeredResource/{resource_id}")
        async def delete_offered_resource(resource_id: str, request: Request):
            return await self._delete_offered_resource(resource_id, request)
    
    # ========================================================================
    # Startup Handler
    # ========================================================================
    
    async def _startup(self):
        """Initialize catalog on startup"""
        logger.info("=" * 60)
        logger.info("Starting IDS TrueConnector API Relay Server")
        logger.info("=" * 60)
        
        catalog = self.catalog_service.get_catalog_value()
        if catalog:
            logger.info(f"Initial catalog value: {catalog}")
        else:
            logger.warning("Could not retrieve catalog value on startup")
    
    # ========================================================================
    # Management Endpoint Handlers
    # ========================================================================
    
    async def _health(self):
        """
        Health check endpoint
        
        Returns:
            dict: Health status information
        """
        return {
            'status': 'healthy',
            'service': 'IDS TrueConnector API Relay Server',
            'provider': self.config['provider_base_url']
        }
    
    async def _get_catalog(self, refresh: bool = False):
        """
        Get the current catalog value
        
        Args:
            refresh: If true, force refresh from provider
        
        Returns:
            dict: Catalog information
        """
        catalog_value = self.catalog_service.get_catalog_value(force_refresh=refresh)
        
        if catalog_value:
            cache_info = self.catalog_service.get_cache_info()
            return {
                'catalog': catalog_value,
                'cached': not refresh,
                'cache_age_seconds': cache_info['age_seconds'],
                'cache_valid': cache_info['is_valid']
            }
        else:
            return JSONResponse(
                status_code=500,
                content={'error': 'Failed to retrieve catalog value'}
            )
    
    async def _catalog_info(self):
        """
        Get detailed cache information
        
        Returns:
            dict: Detailed cache information
        """
        return self.catalog_service.get_cache_info()
    
    async def _clear_catalog_cache(self):
        """
        Clear the catalog cache
        
        Returns:
            dict: Success message
        """
        self.catalog_service.clear_cache()
        return {'message': 'Catalog cache cleared successfully'}
    
    async def _provider_info(self):
        """
        Get provider configuration information
        
        Returns:
            dict: Provider information
        """
        return self.relay_manager.get_provider_info()
    
    # ========================================================================
    # IDS TrueConnector API Endpoint Handlers
    # ========================================================================
    
    async def _create_offered_resource(self, request: Request):
        """
        Create a new offered resource
        
        This endpoint relays POST requests to create new resources in the IDS catalog.
        The catalog header is automatically added to the request.
        """
        return await self.relay_manager.relay_request(
            request,
            '/api/offeredResource/',
            include_catalog=True
        )
    
    async def _list_offered_resources(self, request: Request):
        """
        List all offered resources
        
        This endpoint relays GET requests to retrieve all offered resources.
        """
        return await self.relay_manager.relay_request(
            request,
            '/api/offeredResource/',
            include_catalog=False
        )
    
    async def _get_offered_resource(self, resource_id: str, request: Request):
        """
        Get a specific offered resource
        
        Args:
            resource_id: The ID of the resource to retrieve
        """
        return await self.relay_manager.relay_request(
            request,
            f'/api/offeredResource/{resource_id}',
            include_catalog=False
        )
    
    async def _update_offered_resource(self, resource_id: str, request: Request):
        """
        Update an offered resource
        
        Args:
            resource_id: The ID of the resource to update
        """
        return await self.relay_manager.relay_request(
            request,
            f'/api/offeredResource/{resource_id}',
            include_catalog=True
        )
    
    async def _delete_offered_resource(self, resource_id: str, request: Request):
        """
        Delete an offered resource
        
        Args:
            resource_id: The ID of the resource to delete
        """
        return await self.relay_manager.relay_request(
            request,
            f'/api/offeredResource/{resource_id}',
            include_catalog=False
        )
    
    def get_app(self):
        """
        Get the FastAPI application instance
        
        Returns:
            FastAPI: The FastAPI application
        """
        return self.app