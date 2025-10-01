
# ================================================================================
# ids_consumer_interface.py
# ================================================================================
"""
IDS Consumer Interface - API endpoint handlers for Consumer Resource Server
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class IDS_ConsumerInterface:
    """
    IDS Consumer Interface class containing all API endpoint handlers
    """
    
    def __init__(self, catalog_service, resource_service, config: Dict):
        """
        Initialize the IDS Consumer Interface
        
        Args:
            catalog_service: Instance of ConsumerCatalogService
            resource_service: Instance of ConsumerResourceService
            config: Configuration dictionary
        """
        self.catalog_service = catalog_service
        self.resource_service = resource_service
        self.config = config
        
        logger.info("IDS_ConsumerInterface initialized")
    
    def register_routes(self, app: FastAPI):
        """
        Register all FastAPI routes
        
        Args:
            app: FastAPI application instance
        """
        
        # Startup event
        @app.on_event("startup")
        async def startup_event():
            await self.startup()
        
        # Health endpoint
        @app.get("/health")
        async def health():
            return await self.health()
        
        # Catalog endpoints
        #@app.get("/catalog")
        #async def get_catalog(refresh: bool = False):
         #   return await self.get_catalog(refresh)
        
        #@app.get("/catalog/info")
        #async def catalog_info():
         #   return await self.catalog_info()
        
        #@app.post("/catalog/clear")
        #async def clear_catalog_cache():
         #   return await self.clear_catalog_cache()
        
        # Resource endpoints
        @app.get("/api/IDSconnector/get_data_request")
        async def get_text_resources(refresh: bool = False):
            return await self.get_text_resources(refresh)
        
        #@app.get("/resources/text/summary")
        #async def get_resources_summary():
         #   return await self.get_resources_summary()
        
        @app.get("/api/IDSconnector/get_data_request/{resource_name}")
        async def get_resource_by_name(resource_name: str):
            return await self.get_resource_by_name(resource_name)
        
        @app.post("/api/IDSconnector/clear-cache")
        async def clear_resources_cache():
            return await self.clear_resources_cache()
        
        # Consumer info endpoint
        @app.get("/api/IDSconnector/consumer/info")
        async def consumer_info():
            return await self.consumer_info()
    
    # ========================================================================
    # Startup Handler
    # ========================================================================
    
    async def startup(self):
        """Initialize services on startup"""
        logger.info("=" * 60)
        logger.info("Starting IDS Consumer Resource API Server")
        logger.info("=" * 60)
        
        # Get initial catalog value
        catalog = self.catalog_service.get_catalog_value()
        if catalog:
            logger.info(f"Initial catalog value: {catalog}")
        else:
            logger.warning("Could not retrieve catalog value on startup")
        
        # Get initial resource count
        resources = self.resource_service.get_all_text_resources()
        logger.info(f"Initial text resources count: {len(resources)}")
    
    # ========================================================================
    # Health Endpoint Handler
    # ========================================================================
    
    async def health(self):
        """
        Health check endpoint
        
        Returns:
            dict: Health status information
        """
        return {
            'status': 'healthy',
            'service': 'IDS Consumer Resource API Server',
            'consumer': self.config['consumer_base_url']
        }
    
    # ========================================================================
    # Catalog Endpoint Handlers
    # ========================================================================
    
    async def get_catalog(self, refresh: bool = False):
        """
        Get the current catalog value
        
        Args:
            refresh: If true, force refresh from consumer
        
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
    
    async def catalog_info(self):
        """
        Get detailed cache information
        
        Returns:
            dict: Detailed cache information
        """
        return self.catalog_service.get_cache_info()
    
    async def clear_catalog_cache(self):
        """
        Clear the catalog cache
        
        Returns:
            dict: Success message
        """
        self.catalog_service.clear_cache()
        return {'message': 'Catalog cache cleared successfully'}
    
    # ========================================================================
    # Resource Endpoint Handlers
    # ========================================================================
    
    async def get_text_resources(self, refresh: bool = False):
        """
        Get all text resources
        
        Args:
            refresh: If true, force refresh from consumer
        
        Returns:
            dict: Text resources data
        """
        resources = self.resource_service.get_all_text_resources(force_refresh=refresh)
        
        if resources:
            return {
                'total': len(resources),
                'resources': resources,
                'cached': not refresh
            }
        else:
            return JSONResponse(
                status_code=404,
                content={'message': 'No text resources found'}
            )
    
    async def get_resources_summary(self):
        """
        Get summary of text resources
        
        Returns:
            dict: Resources summary
        """
        summary = self.resource_service.get_resource_summary()
        return summary
    
    async def get_resource_by_name(self, resource_name: str):
        """
        Get a specific resource by name
        
        Args:
            resource_name: The name of the resource to retrieve
        
        Returns:
            dict: Resource data or error response
        """
        resources = self.resource_service.get_all_text_resources()
        
        for resource in resources:
            resource_id = resource.get('@id', '')
            if resource_name in resource_id:
                return resource
        
        return JSONResponse(
            status_code=404,
            content={'error': f'Resource {resource_name} not found'}
        )
    
    async def clear_resources_cache(self):
        """
        Clear the resources cache
        
        Returns:
            dict: Success message
        """
        self.resource_service.clear_cache()
        return {'message': 'Resources cache cleared successfully'}
    
    # ========================================================================
    # Consumer Info Handler
    # ========================================================================
    
    async def consumer_info(self):
        """
        Get consumer configuration information
        
        Returns:
            dict: Consumer information
        """
        return {
            'consumer_base_url': self.config['consumer_base_url'],
            'username': self.config['username'],
            'timeout': self.config['request_timeout'],
            'catalog_cache_ttl': self.config['cache_ttl']
        }
