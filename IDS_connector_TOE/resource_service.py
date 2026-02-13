# ================================================================================
# resource_service.py
# ================================================================================
"""
Resource Service - Service for posting resources to Provider
"""
import requests
import json
import logging
import base64
import hashlib
import re
from typing import Optional, Dict, List, Tuple
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
    
    # Supported zip data types
    ZIP_DATA_TYPES = ['zip', 'application/zip', 'application/x-zip-compressed']
    
    # Zip file indicators in payload
    ZIP_MIME_TYPES = ['application/zip', 'application/x-zip-compressed']
    ZIP_EXTENSIONS = ['.zip']
    
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
    
    def _is_zip_data_type(self, data_type: str) -> bool:
        """
        Check if the data type indicates a zip file
        
        Args:
            data_type: The data type string
            
        Returns:
            bool: True if data type is a zip type
        """
        return data_type.lower() in self.ZIP_DATA_TYPES
    
    def _detect_zip_in_payload(self, data: dict) -> Tuple[bool, Optional[str]]:
        """
        Detect if the JSON payload contains zip file data
        
        Checks for:
        - mime_type field containing zip types
        - filename field ending with .zip
        - type field indicating zip
        
        Args:
            data: Parsed JSON payload
            
        Returns:
            Tuple[bool, Optional[str]]: (is_zip, base64_data)
        """
        try:
            # Convert to string for searching
            data_str = json.dumps(data).lower()
            
            # Check for zip mime types
            has_zip_mime = any(mime in data_str for mime in ['application/zip', 'application/x-zip-compressed'])
            
            # Check for .zip filename
            has_zip_extension = '.zip' in data_str
            
            # Check for type indicators
            has_zip_type = '"type": "zip"' in data_str or '"type":"zip"' in data_str
            
            is_zip = has_zip_mime or has_zip_extension or has_zip_type
            
            if is_zip:
                logger.info("Detected zip file content in JSON payload")
                # Try to extract base64 data
                base64_data = self._extract_base64_data(data)
                return True, base64_data
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error detecting zip in payload: {str(e)}")
            return False, None
    
    def _extract_base64_data(self, data: dict) -> Optional[str]:
        """
        Extract base64-encoded data from the payload
        
        Searches for the 'data' field in nested structures
        
        Args:
            data: Parsed JSON payload
            
        Returns:
            str: Base64 encoded data if found, None otherwise
        """
        try:
            # Check ids:description field (common in IDS TextResource)
            if 'ids:description' in data:
                descriptions = data['ids:description']
                if isinstance(descriptions, list) and descriptions:
                    desc_value = descriptions[0].get('@value', '')
                    if desc_value:
                        # Parse the nested JSON in description
                        try:
                            nested_data = json.loads(desc_value)
                            if 'data' in nested_data:
                                logger.debug("Found base64 data in ids:description")
                                return nested_data['data']
                        except json.JSONDecodeError:
                            pass
            
            # Direct data field
            if 'data' in data:
                if isinstance(data['data'], str) and len(data['data']) > 100:
                    # Likely base64 data
                    logger.debug("Found base64 data in direct 'data' field")
                    return data['data']
            
            # Recursive search for 'data' field with base64 content
            base64_data = self._recursive_find_base64(data)
            if base64_data:
                logger.debug("Found base64 data via recursive search")
                return base64_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting base64 data: {str(e)}")
            return None
    
    def _recursive_find_base64(self, obj, depth: int = 0) -> Optional[str]:
        """
        Recursively search for base64 data in nested structures
        
        Args:
            obj: Object to search
            depth: Current recursion depth
            
        Returns:
            str: Base64 data if found
        """
        if depth > 10:  # Prevent infinite recursion
            return None
            
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == 'data' and isinstance(value, str):
                    # Check if it looks like base64
                    if len(value) > 100 and self._is_valid_base64(value):
                        return value
                result = self._recursive_find_base64(value, depth + 1)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = self._recursive_find_base64(item, depth + 1)
                if result:
                    return result
        elif isinstance(obj, str):
            # Try to parse as JSON
            try:
                parsed = json.loads(obj)
                return self._recursive_find_base64(parsed, depth + 1)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return None
    
    def _is_valid_base64(self, data: str) -> bool:
        """
        Check if a string is valid base64
        
        Args:
            data: String to check
            
        Returns:
            bool: True if valid base64
        """
        try:
            # Remove whitespace
            clean_data = data.replace('\n', '').replace('\r', '').replace(' ', '')
            # Check base64 pattern
            if re.match(r'^[A-Za-z0-9+/]*={0,2}$', clean_data):
                base64.b64decode(clean_data)
                return True
            return False
        except Exception:
            return False
    
    def _compute_zip_hash(self, base64_data: str) -> Optional[str]:
        """
        Compute SHA-256 hash of a base64-encoded zip file
        
        Args:
            base64_data: Base64 encoded zip file data
            
        Returns:
            str: Hex-encoded SHA-256 hash, or None if error
        """
        try:
            # Decode base64 to get raw zip bytes
            zip_bytes = base64.b64decode(base64_data)
            
            # Compute SHA-256 hash of the raw bytes
            sha256_hash = hashlib.sha256(zip_bytes).hexdigest()
            
            logger.info(f"✓ Computed SHA-256 hash for zip file: {sha256_hash}")
            return sha256_hash
            
        except base64.binascii.Error as e:
            logger.error(f"Failed to decode base64 data: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to compute hash: {str(e)}")
            return None
    
    def _add_hash_to_payload(self, data: dict, zip_hash: str) -> dict:
        """
        Add hash metadata to the payload
        
        Args:
            data: Original payload
            zip_hash: Computed SHA-256 hash
            
        Returns:
            dict: Payload with hash metadata added
        """
        # Add hash metadata at the top level
        data['metadata'] = data.get('metadata', {})
        data['metadata']['zip_hash'] = {
            'algorithm': 'SHA-256',
            'value': zip_hash,
            'computed_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Also try to add hash to the IDS description if present
        if 'ids:description' in data:
            descriptions = data['ids:description']
            if isinstance(descriptions, list) and descriptions:
                desc_value = descriptions[0].get('@value', '')
                if desc_value:
                    try:
                        nested_data = json.loads(desc_value)
                        nested_data['metadata'] = nested_data.get('metadata', {})
                        nested_data['metadata']['zip_hash'] = {
                            'algorithm': 'SHA-256',
                            'value': zip_hash
                        }
                        descriptions[0]['@value'] = json.dumps(nested_data)
                        logger.info("Added hash to ids:description metadata")
                    except json.JSONDecodeError:
                        pass
        
        logger.info(f"✓ Tagged payload with SHA-256 hash: {zip_hash[:16]}...")
        return data
    
    def post_resource_to_provider(self, data_type: str, data: str, catalog_value: Optional[str] = None) -> Dict:
        """
        Post resource data to the IDS Provider
        
        Args:
            data_type: Type of data (json, csv, zip, etc.)
            data: The actual data content (should be IDS TextResource JSON structure, or base64 for zip)
            catalog_value: Optional catalog ID to include in header
        
        Returns:
            dict: Response with success status, details, and zip_hash if applicable
        """
        zip_hash = None  # Track the hash for return value
        
        try:
            # The endpoint for posting resources to IDS Provider
            url = f"{self.provider_base_url}/api/offeredResource/"
            
            logger.info(f"Posting resource to provider at {url}...")
            logger.debug(f"Data type: {data_type}, Size: {len(data)} bytes")
            
            # Check if this is explicitly a zip file by data_type
            if self._is_zip_data_type(data_type):
                logger.info("Detected zip data type - computing hash and preparing payload")
                zip_hash = self._compute_zip_hash(data)
                resource_data = {
                    "data_type": data_type,
                    "data": data,
                    "metadata": {
                        "hash_algorithm": "SHA-256",
                        "hash_value": zip_hash,
                        "content_type": "application/zip"
                    }
                }
            else:
                # Parse the data as JSON
                try:
                    resource_data = json.loads(data) if isinstance(data, str) else data
                except json.JSONDecodeError as e:
                    logger.error(f"Data is not valid JSON: {e}")
                    return {
                        'success': False,
                        'error': f'Invalid JSON data: {str(e)}'
                    }
                
                # Check if JSON payload contains zip file data
                is_zip, base64_data = self._detect_zip_in_payload(resource_data)
                
                if is_zip and base64_data:
                    logger.info("JSON payload contains zip file - computing hash")
                    zip_hash = self._compute_zip_hash(base64_data)
                    
                    if zip_hash:
                        resource_data = self._add_hash_to_payload(resource_data, zip_hash)
                    else:
                        logger.warning("Could not compute hash for zip file in payload")
            
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
                result = {
                    'success': True,
                    'status_code': response.status_code,
                    'response': response.json() if response.content else None
                }
                # Include zip_hash in result if computed
                if zip_hash:
                    result['zip_hash'] = zip_hash
                return result
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