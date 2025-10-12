# ================================================================================
# resource_service.py
# ================================================================================
"""
Resource Service - Service for posting resources to Provider
"""
import requests
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime
from requests.auth import HTTPBasicAuth
import urllib3

# Disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ProviderResourceService:
    """
    Service class for posting resources to IDS Provider
    """
    
    def __init__(
        self,
        provider_base_url: str,
        username: str,
        password: str,
        request_timeout: int = 30
    ):
        """
        Initialize the Provider Resource Service
        
        Args:
            provider_base_url: Base URL of the provider
            username: Username for Basic Auth
            password: Password for Basic Auth
            request_timeout: Request timeout in seconds
        """
        self.provider_base_url = provider_base_url
        self.username = username
        self.password = password
        self.request_timeout = request_timeout
        
        logger.info(f"ProviderResourceService initialized for {provider_base_url}")
    
    def post_resource_to_provider(self, data_type: str, data: str, catalog_value: Optional[str] = None) -> Dict:
        """
        Post resource data to the IDS Provider
        
        Args:
            data_type: Type of data (json, csv, etc.)
            data: The actual data content (should be IDS TextResource JSON structure)
            catalog_value: Optional catalog ID to include in header
        
        Returns:
            dict: Response with success status and details
        """
        try:
            # The endpoint for posting resources to IDS Provider
            url = f"{self.provider_base_url}/api/offeredResource/"
            
            logger.info(f"Posting resource to provider at {url}...")
            logger.debug(f"Data type: {data_type}, Size: {len(data)} bytes")
            
            # Parse the data to get the actual IDS resource structure
            # The data should already be the IDS TextResource JSON string
            try:
                resource_data = json.loads(data) if isinstance(data, str) else data
            except json.JSONDecodeError as e:
                logger.error(f"Data is not valid JSON: {e}")
                return {
                    'success': False,
                    'error': f'Invalid JSON data: {str(e)}'
                }
            
            # Build headers
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # Add catalog header if provided
            if catalog_value:
                headers['catalog'] = catalog_value
                logger.debug(f"Using catalog: {catalog_value}")
            
            response = requests.post(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                headers=headers,
                data=json.dumps(resource_data),  # Send as JSON string
                verify=False,
                timeout=self.request_timeout
            )
            
            logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                logger.info("✓ Resource posted successfully to provider")
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'response': response.json() if response.content else None
                }
            else:
                error_msg = f"Provider returned status {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f": {error_detail}"
                except:
                    error_msg += f": {response.text}"
                
                logger.error(f"Failed to post resource: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error posting resource to provider: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error in post_resource_to_provider: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
            
            logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                logger.info("✓ Resource posted successfully to provider")
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'response': response.json() if response.content else None
                }
            else:
                error_msg = f"Provider returned status {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f": {error_detail}"
                except:
                    error_msg += f": {response.text}"
                
                logger.error(f"Failed to post resource: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error posting resource to provider: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_provider_catalog(self) -> Optional[Dict]:
        """Get the complete Provider catalog"""
        try:
            logger.info("Fetching Provider catalog...")
            
            url = f"{self.provider_base_url}/api/selfDescription/"
            
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                headers={"Accept": "application/json"},
                verify=False,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                catalog_data = response.json()
                logger.info("✓ Provider catalog retrieved successfully")
                return catalog_data
            else:
                logger.error(f"Failed to get Provider catalog: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Provider catalog: {str(e)}")
            return None
    
    def extract_text_resource_ids(self, catalog_data: Dict) -> list:
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
            
            logger.info(f"✓ Found {len(resource_ids)} TextResources in Provider catalog")
            return resource_ids
            
        except Exception as e:
            logger.error(f"Error extracting resource IDs: {str(e)}")
            return []
    
    def get_resource_details(self, resource_id: str) -> Optional[Dict]:
        """Get complete details for a specific resource"""
        try:
            resource_name = resource_id.split('/')[-1]
            logger.debug(f"Fetching details for resource: {resource_name}")
            
            url = f"{self.provider_base_url}/api/offeredResource/"
            
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
    
    def get_all_text_resources(self, force_refresh: bool = False) -> list:
        """Retrieve all text resources from the Provider"""
        logger.info("Starting text resource retrieval from Provider")
        
        all_resources = []
        
        # Get the catalog
        catalog_data = self.get_provider_catalog()
        if not catalog_data:
            logger.error("Cannot retrieve resources without catalog")
            return []
        
        # Extract text resource IDs
        resource_ids = self.extract_text_resource_ids(catalog_data)
        
        if not resource_ids:
            logger.warning("No text resources found in Provider")
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
    
    def get_resource_summary(self, resources: Optional[list] = None) -> Dict:
        """Get a summary of the text resources"""
        if resources is None:
            resources = []
        
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
    
    def test_provider_connection(self) -> bool:
        """
        Test connection to the provider
        
        Returns:
            bool: True if connection successful
        """
        try:
            url = f"{self.provider_base_url}/health"
            
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                verify=False,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                logger.info("✓ Provider connection test successful")
                return True
            else:
                logger.warning(f"Provider connection returned: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Provider connection test failed: {str(e)}")
            return False