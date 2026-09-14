# ================================================================================
# resource_service.py
# ================================================================================
"""
Resource Service - Service for retrieving text resources from Consumer
"""
import requests
import logging
from typing import Optional, Dict, List
from datetime import datetime
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class ConsumerResourceService:
    """
    Service class for retrieving all text resources from IDS Consumer
    """
    
    def __init__(
        self,
        consumer_base_url: str,
        username: str,
        password: str,
        request_timeout: int = 30
    ):
        """
        Initialize the Consumer Resource Service
        
        Args:
            consumer_base_url: Base URL of the consumer
            username: Username for Basic Auth
            password: Password for Basic Auth
            request_timeout: Request timeout in seconds
        """
        self.consumer_base_url = consumer_base_url
        self.username = username
        self.password = password
        self.request_timeout = request_timeout

        # Resource listing is intentionally NOT cached by time. Whether a
        # resource is shown again is governed entirely by resource_state_store
        # (AVAILABLE/DELIVERED/CONFIRMED/DEAD) in ids_consumer_interface.py,
        # which reflects actual confirmed SDT ingestion rather than a TTL.
        # Kept for get_resource_summary()'s optional default argument only.
        self._resources_cache = {
            'resources': [],
            'timestamp': None,
            'total_count': 0
        }

        logger.info(f"ConsumerResourceService initialized for {consumer_base_url}")
    
    def get_consumer_catalog(self) -> Optional[Dict]:
        """Get the complete Consumer catalog to discover resources"""
        try:
            logger.info("Fetching Consumer catalog...")
            
            url = f"{self.consumer_base_url}/api/selfDescription/"
            
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                headers={"Accept": "application/json"},
                verify=False,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                catalog_data = response.json()
                logger.info("✓ Consumer catalog retrieved successfully")
                return catalog_data
            else:
                logger.error(f"Failed to get Consumer catalog: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Consumer catalog: {str(e)}")
            return None
    
    def extract_text_resource_ids(self, catalog_data: Dict) -> List[str]:
        """Extract all TextResource identifiers from catalog"""
        resource_ids = []
        
        try:
            catalogs = catalog_data.get('ids:resourceCatalog', [])
            
            for catalog in catalogs:
                offered_resources = catalog.get('ids:offeredResource', [])
                
                for resource in offered_resources:
                    resource_id = resource.get('@id')
                    resource_type = resource.get('@type')
                    
                    # Only get TextResources
                    if resource_id and resource_type == 'ids:TextResource':
                        resource_ids.append(resource_id)
                        logger.debug(f"Found TextResource: {resource_id.split('/')[-1]}")
            
            logger.info(f"✓ Found {len(resource_ids)} TextResources in Consumer catalog")
            return resource_ids
            
        except Exception as e:
            logger.error(f"Error extracting resource IDs: {str(e)}")
            return []
    
    def get_resource_details(self, resource_id: str) -> Optional[Dict]:
        """Get complete details for a specific resource"""
        try:
            resource_name = resource_id.split('/')[-1]
            logger.debug(f"Fetching details for resource: {resource_name}")
            
            url = f"{self.consumer_base_url}/api/offeredResource/"
            
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                headers={
                    "Accept": "application/json",
                    "resource": resource_id
                },
                verify=False,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                resource_data = response.json()
                logger.debug(f"✓ Resource details retrieved: {resource_name}")
                return resource_data
            else:
                logger.error(f"Failed to get resource {resource_name}: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching resource {resource_id}: {str(e)}")
            return None
    
    def get_all_text_resources(self, force_refresh: bool = True) -> List[Dict]:
        """
        Retrieve all text resources from the Consumer.

        Always fetches fresh from the catalog - resource listing has no
        time-based cache. Whether a given resource is worth re-showing to a
        caller is a question for resource_state_store, not this method; this
        always returns the ground truth. `force_refresh` is accepted for
        backward compatibility with existing call sites but has no effect.
        """
        all_resources = self._fetch_all_resources()
        self._update_cache(all_resources)
        return all_resources
    
    def _fetch_all_resources(self) -> List[Dict]:
        """Internal method to fetch all resources from Consumer (extracted from get_all_text_resources)"""
        logger.info("Starting text resource retrieval from Consumer")
        
        all_resources = []
        
        # Get the catalog
        catalog_data = self.get_consumer_catalog()
        if not catalog_data:
            logger.error("Cannot retrieve resources without catalog")
            return []
        
        # Extract text resource IDs
        resource_ids = self.extract_text_resource_ids(catalog_data)
        
        if not resource_ids:
            logger.warning("No text resources found in Consumer")
            return []
        
        # Get details for each resource
        logger.info(f"Retrieving details for {len(resource_ids)} text resources...")
        
        for i, resource_id in enumerate(resource_ids, 1):
            resource_name = resource_id.split('/')[-1]
            logger.info(f"[{i}/{len(resource_ids)}] Fetching: {resource_name}")
            
            resource_data = self.get_resource_details(resource_id)
            if resource_data:
                all_resources.append(resource_data)
                logger.info(f"  ✓ Successfully retrieved {resource_name}")
            else:
                logger.error(f"  ✗ Failed to retrieve {resource_name}")
        
        # Summary
        logger.info(f"Resource retrieval complete: {len(all_resources)}/{len(resource_ids)} successful")
        
        return all_resources
    
    def get_resource_summary(self, resources: Optional[List[Dict]] = None) -> Dict:
        """Get a summary of the text resources"""
        if resources is None:
            resources = self._resources_cache['resources']
        
        summary = {
            'total_count': len(resources),
            'resource_names': [],
            'resource_details': []
        }
        
        for resource in resources:
            resource_id = resource.get('@id', 'unknown')
            resource_name = resource_id.split('/')[-1]
            
            detail = {
                'id': resource_id,
                'name': resource_name,
                'type': resource.get('@type', 'unknown'),
                'title': None,
                'description': None
            }
            
            # Extract title and description
            if 'ids:title' in resource:
                titles = resource['ids:title']
                if isinstance(titles, list) and titles:
                    detail['title'] = titles[0].get('@value', 'No title')
            
            if 'ids:description' in resource:
                descriptions = resource['ids:description']
                if isinstance(descriptions, list) and descriptions:
                    detail['description'] = descriptions[0].get('@value', 'No description')
            
            summary['resource_names'].append(resource_name)
            summary['resource_details'].append(detail)
        
        return summary
    
    def _update_cache(self, resources: List[Dict]):
        """Update the cache with new resources"""
        self._resources_cache['resources'] = resources
        self._resources_cache['timestamp'] = datetime.now()
        self._resources_cache['total_count'] = len(resources)
        logger.debug(f"Cache updated with {len(resources)} resources")
    
    def _get_cache_age(self) -> float:
        """Get the age of the cached resources in seconds"""
        if not self._resources_cache['timestamp']:
            return float('inf')
        return (datetime.now() - self._resources_cache['timestamp']).total_seconds()
    
    # NOTE: "cleared" resource tracking used to live here (_cleared_resource_ids,
    # clear_cache, clear_specific_resources, get_cleared_resource_ids). That
    # concept - "we handed this out once, don't show it again" - is exactly
    # the bug this service had: it remembered *delivery*, not *confirmed
    # ingestion*, and it lived only in memory. It's replaced by
    # resource_state_store.resource_state, which tracks AVAILABLE / DELIVERED
    # / CONFIRMED / DEAD per resource and is used directly from
    # ids_consumer_interface.py. The /clear-cache and /cleared-ids HTTP
    # endpoints still exist but now operate on that store instead.
