"""
Relay Manager - Manages API request relaying with catalog service integration
"""
import requests
from typing import Dict, Optional
from fastapi import Request, Response, HTTPException
import logging

logger = logging.getLogger(__name__)


class RelayManager:
    """
    Manager class for handling API request relaying to IDS TrueConnector
    """
    
    def __init__(
        self,
        catalog_service,
        provider_base_url: str,
        username: str,
        password: str,
        request_timeout: int = 30
    ):
        """
        Initialize the Relay Manager
        
        Args:
            catalog_service: Instance of CatalogService
            provider_base_url: Base URL of the provider
            username: Username for Basic Auth
            password: Password for Basic Auth
            request_timeout: Request timeout in seconds
        """
        self.catalog_service = catalog_service
        self.provider_base_url = provider_base_url
        self.username = username
        self.password = password
        self.request_timeout = request_timeout
        
        logger.info(f"RelayManager initialized for {provider_base_url}")
    
    async def relay_request(
        self,
        request: Request,
        target_path: str,
        include_catalog: bool = False
    ) -> Response:
        """
        Relay an incoming request to the target API endpoint
        
        Args:
            request: The incoming FastAPI request
            target_path: The path to relay to (e.g., '/api/offeredResource/')
            include_catalog: If True, add the catalog header to the request
        
        Returns:
            Response: The response from the target API
        
        Raises:
            HTTPException: If the request fails
        """
        # Construct the full URL
        url = f"{self.provider_base_url}{target_path}"
        
        # Prepare headers
        headers = await self._prepare_headers(request, include_catalog)
        
        # Get query parameters
        params = dict(request.query_params)
        
        # Get request body
        body = await request.body()
        
        logger.info(f"Relaying {request.method} request to {url}")
        
        try:
            # Make the request to the target API
            response = requests.request(
                method=request.method,
                url=url,
                auth=(self.username, self.password),
                headers=headers,
                params=params,
                data=body,
                timeout=self.request_timeout,
                allow_redirects=False,
                verify=False  # Disable SSL verification for provider pod
            )
            
            logger.info(f"Received response with status code: {response.status_code}")
            
            # Return the response from the target API
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            raise HTTPException(status_code=504, detail='Request timeout')
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise HTTPException(status_code=502, detail=f'Request failed: {str(e)}')
    
    async def _prepare_headers(
        self,
        request: Request,
        include_catalog: bool
    ) -> Dict[str, str]:
        """
        Prepare headers for the relay request
        
        Args:
            request: The incoming FastAPI request
            include_catalog: If True, add the catalog header
        
        Returns:
            dict: Prepared headers
        
        Raises:
            HTTPException: If catalog value cannot be retrieved
        """
        headers = dict(request.headers)
        headers['Content-Type'] = 'application/json'
        
        # Remove host header to avoid conflicts
        headers.pop('host', None)
        
        # Add catalog header if requested
        if include_catalog:
            catalog_value = self.catalog_service.get_catalog_value()
            if catalog_value:
                headers['catalog'] = catalog_value
                logger.info(f"Added catalog header: {catalog_value}")
            else:
                logger.error("Could not retrieve catalog value")
                raise HTTPException(
                    status_code=500,
                    detail='Failed to retrieve catalog value from provider'
                )
        
        return headers
    
    def get_provider_info(self) -> Dict:
        """
        Get information about the provider configuration
        
        Returns:
            dict: Provider information
        """
        return {
            'provider_base_url': self.provider_base_url,
            'username': self.username,
            'timeout': self.request_timeout
        }