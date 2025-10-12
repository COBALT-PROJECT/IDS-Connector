# ================================================================================
# ids_provider_interface.py
# ================================================================================
"""
IDS Provider Interface - API endpoint handlers for TOE Provider Server
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging
from typing import Dict
import json

logger = logging.getLogger(__name__)


class DataResponse(BaseModel):
    """Data response model matching OpenAPI spec"""
    data_type: str = Field(..., description="Type of data returned")
    data: str = Field(..., description="The actual data payload")


class IDS_ProviderInterface:
    """
    IDS Provider Interface class containing all API endpoint handlers
    """
    
    def __init__(self, catalog_service, resource_service, config: Dict):
        """
        Initialize the IDS Provider Interface
        
        Args:
            catalog_service: Instance of ProviderCatalogService
            resource_service: Instance of ProviderResourceService
            config: Configuration dictionary
        """
        self.catalog_service = catalog_service
        self.resource_service = resource_service
        self.config = config
        
        logger.info("IDS_ProviderInterface initialized")
    
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
        
        # Main post data endpoint - matching YAML spec
        @app.post("/api/IDSconnector/post_data", tags=["IDSconnector-provider"])
        async def post_data(data_response: DataResponse):
            return await self.post_data(data_response)
        
        # Clear cache endpoint
        @app.post("/api/IDSconnector/clear-cache")
        async def clear_cache():
            return await self.clear_cache()
        
        # Provider info endpoint
        @app.get("/api/IDSconnector/TOE/info")
        async def provider_info():
            return await self.provider_info()
    
    # ========================================================================
    # Startup Handler
    # ========================================================================
    
    async def startup(self):
        """Initialize services on startup"""
        logger.info("=" * 60)
        logger.info("Starting IDS TOE Provider API Server")
        logger.info("=" * 60)
        
        # Get initial catalog value
        catalog = self.catalog_service.get_catalog_value()
        if catalog:
            logger.info(f"Initial catalog value: {catalog}")
        else:
            logger.warning("Could not retrieve catalog value on startup")
        
        # Get initial resource count from provider
        resources = self.resource_service.get_all_text_resources()
        logger.info(f"Initial text resources count from provider: {len(resources)}")
    
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
            'service': 'IDS TOE Provider API Server',
            'provider': self.config['provider_base_url']
        }
    
    # ========================================================================
    # Post Data Handler (Main Endpoint)
    # ========================================================================
    
    async def post_data(self, data_response: DataResponse):
        """
        Post data from TOE to Provider IDS instance
        
        Args:
            data_response: DataResponse object containing data_type and data
        
        Returns:
            dict: Data response confirming successful post
        
        Raises:
            HTTPException: For various error conditions (400, 404, 500)
        """
        try:
            # Validate data_type
            if not data_response.data_type:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "BAD_REQUEST",
                        "message": "data_type is required."
                    }
                )
            
            # Validate data
            if not data_response.data:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "BAD_REQUEST",
                        "message": "data is required."
                    }
                )
            
            logger.info(f"Processing data post request - data_type: {data_response.data_type}, data_size: {len(data_response.data)} bytes")
            
            # Get catalog value for the header
            catalog_value = self.catalog_service.get_catalog_value()
            if not catalog_value:
                logger.warning("Could not retrieve catalog value, attempting without catalog header")
            
            # Step 1: Post resource to provider
            result = self.resource_service.post_resource_to_provider(
                data_type=data_response.data_type,
                data=data_response.data,
                catalog_value=catalog_value
            )
            
            if not result['success']:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "code": "INTERNAL_ERROR",
                        "message": f"Failed to post data to provider: {result.get('error', 'Unknown error')}"
                    }
                )
            
            logger.info(f"✓ Data posted successfully to provider")
            
            # Step 2: Clear cache to ensure fresh data
            logger.info("Clearing cache after successful post...")
            self.catalog_service.clear_cache()
            
            # Step 3: Fetch all text resource IDs from the catalog
            logger.info("Fetching updated text resources from provider...")
            resources = self.resource_service.get_all_text_resources(force_refresh=True)
            logger.info(f"✓ Synchronized with provider - {len(resources)} text resources available")
            
            # Return the same data response to confirm receipt
            return {
                "data_type": data_response.data_type,
                "data": data_response.data
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error in post_data: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected error while posting data."
                }
            )
    
    # ========================================================================
    # Clear Cache Handler
    # ========================================================================
    
    async def clear_cache(self):
        """
        Clear the catalog cache
        
        Returns:
            dict: Success message
        """
        self.catalog_service.clear_cache()
        return {'message': 'Catalog cache cleared successfully'}
    
    # ========================================================================
    # Provider Info Handler
    # ========================================================================
    
    async def provider_info(self):
        """
        Get provider configuration information
        
        Returns:
            dict: Provider information
        """
        return {
            'provider_base_url': self.config['provider_base_url'],
            'username': self.config['username'],
            'timeout': self.config['request_timeout'],
            'catalog_cache_ttl': self.config['cache_ttl']
        }