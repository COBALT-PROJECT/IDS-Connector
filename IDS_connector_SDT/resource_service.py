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
        
        # Cache for resources
        self._resources_cache = {
            'resources': [],
            'timestamp': None,
            'total_count': 0
        }
        
        # Set to track cleared resource IDs (to ignore in future fetches)
        self._cleared_resource_ids = set()
        
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
    
    def get_all_text_resources(self, force_refresh: bool = False) -> List[Dict]:
        """Retrieve all text resources from the Consumer, filtering out cleared ones"""
        # Always fetch fresh if cleared resources exist or force_refresh is True
        if force_refresh or self._cleared_resource_ids:
            logger.info("Forcing refresh due to cleared resources or explicit request")
            # Fetch fresh data
            all_resources = self._fetch_all_resources()
        elif self._resources_cache['resources']:
            cache_age = self._get_cache_age()
            logger.info(f"Using cached resources (age: {cache_age:.0f}s)")
            return self._resources_cache['resources']
        else:
            all_resources = self._fetch_all_resources()
        
        # Filter out cleared resources
        if self._cleared_resource_ids:
            filtered_resources = [
                res for res in all_resources 
                if res.get('@id') not in self._cleared_resource_ids
            ]
            logger.info(f"Filtered out {len(all_resources) - len(filtered_resources)} cleared resources")
            all_resources = filtered_resources
        
        # Update cache with filtered results
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
    
    def clear_cache(self):
        """Clear the resources cache and mark current resources as cleared"""
        # Add current cached resource IDs to cleared set
        current_ids = {res.get('@id') for res in self._resources_cache['resources'] if res.get('@id')}
        self._cleared_resource_ids.update(current_ids)
        logger.info(f"Marked {len(current_ids)} resources as cleared: {list(current_ids)}")
        
        # Clear the cache
        self._resources_cache['resources'] = []
        self._resources_cache['timestamp'] = None
        self._resources_cache['total_count'] = 0
        logger.info("Resources cache cleared")
    
    def clear_specific_resources(self, resource_ids: List[str]):
        """Clear specific resources by their IDs"""
        if not resource_ids:
            logger.info("No resources to clear")
            return
        
        # Add specified resource IDs to cleared set
        self._cleared_resource_ids.update(resource_ids)
        logger.info(f"Marked {len(resource_ids)} specific resources as cleared")
        
        # Remove these resources from cache if they exist
        if self._resources_cache['resources']:
            original_count = len(self._resources_cache['resources'])
            self._resources_cache['resources'] = [
                res for res in self._resources_cache['resources']
                if res.get('@id') not in resource_ids
            ]
            removed_count = original_count - len(self._resources_cache['resources'])
            logger.info(f"Removed {removed_count} resources from cache")
            self._resources_cache['total_count'] = len(self._resources_cache['resources'])
    
    def get_cleared_resource_ids(self) -> List[str]:
        """Get the list of cleared resource IDs"""
        return list(self._cleared_resource_ids)
