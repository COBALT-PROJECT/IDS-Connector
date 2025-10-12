# ================================================================================
# catalog_service.py
# ================================================================================
"""
Catalog Service - Handles catalog operations for Provider
"""
import requests
import json
import re
import urllib3
from datetime import datetime
from typing import Optional, Dict
import logging

# Disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ProviderCatalogService:
    """
    Service class for managing IDS Provider catalog operations
    """
    
    def __init__(
        self,
        provider_base_url: str,
        username: str,
        password: str,
        self_description_path: str = '/api/selfDescription/',
        cache_ttl: int = 300,
        request_timeout: int = 30
    ):
        """
        Initialize the Provider Catalog Service
        
        Args:
            provider_base_url: Base URL of the provider
            username: Username for Basic Auth
            password: Password for Basic Auth
            self_description_path: Path to self-description endpoint
            cache_ttl: Cache time-to-live in seconds
            request_timeout: Request timeout in seconds
        """
        self.provider_base_url = provider_base_url
        self.username = username
        self.password = password
        self.self_description_path = self_description_path
        self.cache_ttl = cache_ttl
        self.request_timeout = request_timeout
        
        # Cache storage
        self._cache: Dict = {
            'value': None,
            'timestamp': None
        }
        
        logger.info(f"ProviderCatalogService initialized for {provider_base_url}")
    
    def get_catalog_value(self, force_refresh: bool = False) -> Optional[str]:
        """
        Retrieve the catalog value from the self-description API endpoint
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh value
        
        Returns:
            str: The catalog URL if found, None otherwise
        """
        # Check cache first
        if not force_refresh and self._is_cache_valid():
            cache_age = self._get_cache_age()
            logger.info(f"Using cached catalog value (age: {cache_age:.0f}s)")
            return self._cache['value']
        
        # Fetch fresh catalog value
        catalog_value = self._fetch_catalog_from_api()
        
        if catalog_value:
            self._update_cache(catalog_value)
            
        return catalog_value
    
    def _fetch_catalog_from_api(self) -> Optional[str]:
        """
        Fetch catalog value from the provider's self-description endpoint
        """
        url = f"{self.provider_base_url}{self.self_description_path}"
        
        headers = {
            'Accept': 'application/json'
        }
        
        try:
            logger.info(f"Fetching catalog value from {url}...")
            
            response = requests.get(
                url,
                auth=(self.username, self.password),
                headers=headers,
                verify=False,
                timeout=self.request_timeout
            )
            
            logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Try regex pattern matching first
                catalog_value = self._extract_catalog_by_regex(response_data)
                
                if catalog_value:
                    logger.info(f"✓ Catalog value retrieved: {catalog_value}")
                    return catalog_value
                
                # Try recursive search as fallback
                catalog_value = self._extract_catalog_by_recursion(response_data)
                
                if catalog_value:
                    logger.info(f"✓ Catalog value found via fallback: {catalog_value}")
                    return catalog_value
                
                logger.warning("Catalog URL not found in self-description response")
                return None
            else:
                logger.error(f"Failed to fetch self-description. Status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching catalog value: {str(e)}")
            return None
    
    def _extract_catalog_by_regex(self, data: dict) -> Optional[str]:
        """Extract catalog value using regex pattern matching"""
        catalog_pattern = r'https://w3id\.org/idsa/autogen/resourceCatalog/[a-f0-9\-]+'
        response_text = json.dumps(data)
        matches = re.findall(catalog_pattern, response_text)
        
        return matches[0] if matches else None
    
    def _extract_catalog_by_recursion(self, data, key_pattern: str = 'resourceCatalog') -> Optional[str]:
        """Recursively search for catalog value in nested dictionary"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key_pattern in key:
                    if isinstance(value, str) and 'resourceCatalog' in value:
                        return value
                    elif isinstance(value, dict) and '@id' in value:
                        return value['@id']
                result = self._extract_catalog_by_recursion(value, key_pattern)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._extract_catalog_by_recursion(item, key_pattern)
                if result:
                    return result
        return None
    
    def _is_cache_valid(self) -> bool:
        """Check if the cached value is still valid"""
        if not self._cache['value'] or not self._cache['timestamp']:
            return False
        
        cache_age = self._get_cache_age()
        return cache_age < self.cache_ttl
    
    def _get_cache_age(self) -> float:
        """Get the age of the cached value in seconds"""
        if not self._cache['timestamp']:
            return float('inf')
        return (datetime.now() - self._cache['timestamp']).total_seconds()
    
    def _update_cache(self, value: str):
        """Update the cache with a new value"""
        self._cache['value'] = value
        self._cache['timestamp'] = datetime.now()
        logger.debug(f"Cache updated with value: {value}")
    
    def get_cache_info(self) -> Dict:
        """Get information about the current cache state"""
        return {
            'value': self._cache['value'],
            'timestamp': self._cache['timestamp'],
            'age_seconds': self._get_cache_age() if self._cache['timestamp'] else None,
            'is_valid': self._is_cache_valid()
        }
    
    def clear_cache(self):
        """Clear the catalog cache"""
        self._cache['value'] = None
        self._cache['timestamp'] = None
        logger.info("Cache cleared")