# ================================================================================
# ids_consumer_interface.py
# ================================================================================
"""
IDS Consumer Interface - API endpoint handlers for Consumer Resource Server
"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, Response
import logging
from typing import Dict, Optional
import json
import base64
import io

logger = logging.getLogger(__name__)


class IDS_ConsumerInterface:
    """
    IDS Consumer Interface class containing all API endpoint handlers
    """
    
    def __init__(self, catalog_service, resource_service, file_extractor_service, config: Dict):
        """
        Initialize the IDS Consumer Interface
        
        Args:
            catalog_service: Instance of ConsumerCatalogService
            resource_service: Instance of ConsumerResourceService
            file_extractor_service: Instance of FileExtractorService
            config: Configuration dictionary
        """
        self.catalog_service = catalog_service
        self.resource_service = resource_service
        self.file_extractor_service = file_extractor_service
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
        
        # Main data request endpoint - updated to match YAML spec
        @app.get("/api/IDSconnector/get_data_request", tags=["IDSconnector-consumer"])
        async def get_data_request(
            toe_id: str = Query(..., description="entity to be synchronized with"),
            data_type: str = Query(..., description="Data being received", example="json"),
            data_path: str = Query(..., description="Path to the data source")
        ):
            return await self.get_data_request(toe_id, data_type, data_path)
        
        # Resource by name endpoint (keeping for backward compatibility)
        #Get resource by name
        """
        @app.get("/api/IDSconnector/get_data_request/{resource_name}")
        async def get_resource_by_name(resource_name: str):
            return await self.get_resource_by_name(resource_name)
        """
        
        # Clear cache endpoint
        @app.post("/api/IDSconnector/clear-cache")
        async def clear_resources_cache():
            return await self.clear_resources_cache()
        
        # File extraction endpoint
        @app.get("/api/IDSconnector/extract_file", tags=["IDSconnector-consumer"])
        async def extract_file(
            data_path: str = Query(..., description="Path to the data source containing file"),
            return_format: str = Query("json", description="Response format: 'json' or 'binary'")
        ):
            return await self.extract_file(data_path, return_format)
        
        # Consumer info endpoint
        @app.get("/api/IDSconnector/SDT/info")
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
    # Main Data Request Handler (YAML Spec Compatible)
    # ========================================================================
    
    async def get_data_request(
        self, 
        toe_id: str, 
        data_type: str, 
        data_path: str
    ):
        """
        Get data request endpoint compatible with YAML specification
        
        Args:
            toe_id: Entity to be synchronized with
            data_type: Type of data being received (e.g., "json")
            data_path: Path to the data source
        
        Returns:
            dict: Data response object
        
        Raises:
            HTTPException: For various error conditions (400, 404, 500)
        """
        try:
            # Validate required parameters
            if not toe_id:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "BAD_REQUEST",
                        "message": "toe_id is required."
                    }
                )
            
            if not data_type:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "BAD_REQUEST",
                        "message": "data_type is required."
                    }
                )
            
            if not data_path:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "BAD_REQUEST",
                        "message": "data_path is required."
                    }
                )
            
            logger.info(f"Processing data request - toe_id: {toe_id}, data_type: {data_type}, data_path: {data_path}")
            
            # Check if requesting all resources and clear cache if so
            if data_path.lower() in ['all', '*', 'resources']:
                # Clear cache before fetching all resources
                logger.info("Clearing cache for 'all' resources request")
                self.resource_service.clear_cache()
                self.catalog_service.clear_cache()
            
            # Get all text resources
            resources = self.resource_service.get_all_text_resources()
            
            if not resources:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "NOT_FOUND",
                        "message": f"No data at data_path: {data_path}"
                    }
                )
            
            # Check if requesting all resources FIRST
            if data_path.lower() in ['all', '*', 'resources']:
                # Return all resources
                if data_type.lower() == "json":
                    response_data = json.dumps({
                        "total": len(resources),
                        "resources": resources
                    })
                else:
                    # For CSV or other formats, convert appropriately
                    response_data = str({
                        "total": len(resources),
                        "resources": resources
                    })
                
                return {
                    "data_type": data_type,
                    "data": response_data
                }
            
            # Search for the resource matching the criteria
            matching_resource = None
            
            # Strategy 1: Match by data_path in resource ID
            for resource in resources:
                resource_id = resource.get('@id', '')
                # Extract the last segment of the resource ID
                resource_name = resource_id.split('/')[-1]
                
                if data_path == resource_name or data_path in resource_id:
                    matching_resource = resource
                    break
            
            # Strategy 2: Match by artifact ID in contract offer
            if not matching_resource:
                for resource in resources:
                    contract_offers = resource.get('ids:contractOffer', [])
                    for offer in contract_offers:
                        permissions = offer.get('ids:permission', [])
                        for permission in permissions:
                            target = permission.get('ids:target', {})
                            target_id = target.get('@id', '')
                            if data_path in target_id:
                                matching_resource = resource
                                break
                        if matching_resource:
                            break
                    if matching_resource:
                        break
            
            # Strategy 3: Match by title or description
            if not matching_resource:
                for resource in resources:
                    titles = resource.get('ids:title', [])
                    descriptions = resource.get('ids:description', [])
                    
                    for title in titles:
                        if data_path.lower() in title.get('@value', '').lower():
                            matching_resource = resource
                            break
                    
                    if not matching_resource:
                        for desc in descriptions:
                            if data_path.lower() in desc.get('@value', '').lower():
                                matching_resource = resource
                                break
                    
                    if matching_resource:
                        break
            
            if not matching_resource:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "NOT_FOUND",
                        "message": f"No data at data_path: {data_path}"
                    }
                )
            
            # Check if the resource contains an embedded file
            file_response = self.file_extractor_service.extract_from_resource(matching_resource)
            
            if file_response:
                logger.info(f"File detected in resource, extracting as {data_type}")
                
                # If a file was found, return it according to requested data_type
                if data_type.lower() == "file" or data_type.lower() == "binary":
                    # Return the file extraction response
                    return {
                        "data_type": "file",
                        "data": json.dumps(file_response)
                    }
                elif data_type.lower() == "json":
                    # Return both resource and extracted file info
                    combined_response = {
                        "resource": matching_resource,
                        "extracted_file": file_response
                    }
                    response_data = json.dumps(combined_response)
                else:
                    # For other types, just include file metadata
                    response_data = json.dumps({
                        "resource_id": matching_resource.get('@id', 'unknown'),
                        "file_metadata": file_response.get("metadata", {}),
                        "file_available": True
                    })
            else:
                # No file detected, proceed with normal resource handling
                # Format the response based on data_type
                response_data = None
                
                if data_type.lower() == "json":
                    # Return the resource as JSON
                    response_data = json.dumps(matching_resource)
                elif data_type.lower() == "csv":
                    # Convert resource data to CSV format
                    response_data = self._convert_to_csv(matching_resource)
                else:
                    # For other data types, return as string
                    response_data = str(matching_resource)
            
            # Return response matching the schema
            return {
                "data_type": data_type,
                "data": response_data
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_data_request: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected error while fetching data."
                }
            )
    
    def _convert_to_csv(self, resource: Dict) -> str:
        """
        Convert resource data to CSV format
        
        Args:
            resource: Resource dictionary
        
        Returns:
            str: CSV formatted string
        """
        # Example CSV conversion - adjust based on actual data structure
        csv_lines = []
        csv_lines.append("timestamp,value")
        
        # If the resource has timestamp/value data, format it
        # This is an example - adjust based on your actual data structure
        resource_id = resource.get('@id', 'unknown')
        resource_type = resource.get('@type', 'unknown')
        
        # Create a sample CSV line
        import datetime
        timestamp = datetime.datetime.now().isoformat() + "Z"
        csv_lines.append(f"{timestamp},{resource_id}")
        
        return "\n".join(csv_lines) + "\n"
    
    # ========================================================================
    # Legacy Resource Endpoint Handlers
    # ========================================================================
    
    async def get_resource_by_name(self, resource_name: str):
        """
        Get a specific resource by name (legacy endpoint)
        
        Args:
            resource_name: The name of the resource to retrieve
        
        Returns:
            dict: Resource data or error response
        """
        try:
            resources = self.resource_service.get_all_text_resources()
            
            for resource in resources:
                resource_id = resource.get('@id', '')
                if resource_name in resource_id:
                    return resource
            
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "NOT_FOUND",
                    "message": f"Resource {resource_name} not found"
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in get_resource_by_name: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected error while fetching resource."
                }
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
    # File Extraction Handlers
    # ========================================================================
    
    async def extract_file(self, data_path: str, return_format: str = "json"):
        """
        Extract file from a resource
        
        Args:
            data_path: Path to the data source containing file
            return_format: Response format ('json' or 'binary')
        
        Returns:
            File data in requested format
        """
        try:
            logger.info(f"Extracting file from data_path: {data_path}, format: {return_format}")
            
            # Get all resources
            resources = self.resource_service.get_all_text_resources()
            
            if not resources:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "NOT_FOUND",
                        "message": f"No resources available"
                    }
                )
            
            # Find the matching resource
            matching_resource = None
            
            # Search strategies (same as in get_data_request)
            for resource in resources:
                resource_id = resource.get('@id', '')
                resource_name = resource_id.split('/')[-1]
                
                if data_path == resource_name or data_path in resource_id:
                    matching_resource = resource
                    break
            
            if not matching_resource:
                # Try matching by title or description
                for resource in resources:
                    titles = resource.get('ids:title', [])
                    for title in titles:
                        if data_path.lower() in title.get('@value', '').lower():
                            matching_resource = resource
                            break
                    if matching_resource:
                        break
            
            if not matching_resource:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "NOT_FOUND",
                        "message": f"No resource found for data_path: {data_path}"
                    }
                )
            
            # Extract file from the resource
            file_response = self.file_extractor_service.extract_from_resource(matching_resource)
            
            if not file_response:
                # Try to extract from description field directly
                file_bytes, metadata, data_type = self.file_extractor_service.extract_file_from_json(matching_resource)
                
                if file_bytes and metadata:
                    file_response = self.file_extractor_service.create_file_response(
                        file_bytes, metadata, data_type
                    )
                else:
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "code": "NO_FILE",
                            "message": f"No extractable file found in resource: {data_path}"
                        }
                    )
            
            # Return based on format
            if return_format == "binary" and file_response.get("encoding") == "base64":
                # Return raw binary data
                binary_data = base64.b64decode(file_response["data"])
                metadata = file_response["metadata"]
                
                mime_type = metadata.get("mime_type", "application/octet-stream")
                filename = metadata.get("filename", "extracted_file")
                
                # Add extension if missing
                extension = self.file_extractor_service.get_file_extension(metadata)
                if extension and not '.' in filename:
                    filename += extension
                
                return StreamingResponse(
                    io.BytesIO(binary_data),
                    media_type=mime_type,
                    headers={
                        "Content-Disposition": f"attachment; filename={filename}"
                    }
                )
            else:
                # Return JSON response
                return JSONResponse(content=file_response)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in extract_file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "INTERNAL_ERROR",
                    "message": f"Error extracting file: {str(e)}"
                }
            )
    
    async def download_file(self, data_path: str):
        """
        Download file directly as binary
        
        Args:
            data_path: Path to the data source containing file
        
        Returns:
            Binary file stream
        """
        return await self.extract_file(data_path, return_format="binary")
    
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