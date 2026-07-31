# ================================================================================
# ids_provider_interface.py
# ================================================================================
"""
IDS Provider Interface - API endpoint handlers for TOE Provider Server
"""
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging
from typing import Dict, Optional, Any
import json
import uuid

logger = logging.getLogger(__name__)


class DataResponse(BaseModel):
    """Data response model matching OpenAPI spec"""
    data_type: str = Field(..., description="Type of data returned")
    data: str = Field(..., description="The actual data payload")


class ToeIdRequest(BaseModel):
    """Request model for setting the TOE ID used by post_data"""
    toe_id: str = Field(..., description="TOE UUID, e.g. 3e671687-395b-41f5-a30f-a58921a69b79")


class AuthenticatedRequest(BaseModel):
    """Request model for calls made with the stored JWT"""
    method: str = Field("GET", description="HTTP method to use")
    path: str = Field(..., description="Authentication Manager API path, e.g. /api/digital-twins")
    payload: Optional[Dict[str, Any]] = Field(None, description="Optional JSON payload")


class IDS_ProviderInterface:
    """
    IDS Provider Interface class containing all API endpoint handlers
    """
    
    def __init__(self, catalog_service, resource_service, config: Dict,
                 authentication_manager=None):
        """
        Initialize the IDS Provider Interface
        
        Args:
            catalog_service: Instance of ProviderCatalogService
            resource_service: Instance of ProviderResourceService
            config: Configuration dictionary
            authentication_manager: Instance of AuthenticationManager (optional)
        """
        self.catalog_service = catalog_service
        self.resource_service = resource_service
        self.config = config
        self.authentication_manager = authentication_manager
        self.toe_id: Optional[str] = None
        
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

        # TOE ID state endpoints
        @app.post("/api/IDSconnector/TOE/id", tags=["IDSconnector-provider"])
        async def set_toe_id(
            request: ToeIdRequest,
            authorization: Optional[str] = Header(None),
        ):
            return await self.set_toe_id(request, authorization)

        @app.get("/api/IDSconnector/TOE/id", tags=["IDSconnector-provider"])
        async def get_toe_id():
            return await self.get_toe_id()

        # ===== Authentication endpoints =====

        @app.post("/api/IDSconnector/TOE/jwt/refresh", tags=["Authentication"])
        async def refresh_jwt():
            """Fetch and store a new JWT from the Authentication Manager."""
            return await self.refresh_jwt()

        @app.get("/api/IDSconnector/TOE/jwt/status", tags=["Authentication"])
        async def jwt_status():
            """Return metadata for the stored JWT without exposing the token."""
            return await self.jwt_status()

        @app.post("/api/IDSconnector/TOE/jwt/request", tags=["Authentication"])
        async def authenticated_jwt_request(request: AuthenticatedRequest):
            """Call the Authentication Manager using the stored JWT."""
            return await self.authenticated_jwt_request(request)

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
            dict: Health status information including authentication state
        """
        response = {
            'status': 'healthy',
            'service': 'IDS TOE Provider API Server',
            'provider': self.config['provider_base_url'],
            'toe_id': self.toe_id,
        }

        return response
    
    # ========================================================================
    # Post Data Handler (Main Endpoint)
    # ========================================================================
    
    async def post_data(self, data_response: DataResponse):
        """
        Post data from TOE to Provider IDS instance
        
        Args:
            data_response: DataResponse object containing data_type and data
        
        Returns:
            dict: Data response confirming successful post, including hash if zip file
        
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

            if not self.toe_id:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "TOE_ID_NOT_SET",
                        "message": "Set TOE ID first using POST /api/IDSconnector/TOE/id."
                    }
                )

            data_to_post = self._inject_toe_id(data_response.data)
            
            # Get catalog value for the header
            catalog_value = self.catalog_service.get_catalog_value()
            if not catalog_value:
                logger.warning("Could not retrieve catalog value, attempting without catalog header")
            
            # Step 1: Post resource to provider (this now computes hash for zip files)
            result = self.resource_service.post_resource_to_provider(
                data_type=data_response.data_type,
                data=data_to_post,
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
            
            # Build response
            response = {
                "data_type": data_response.data_type,
                "toe_id": self.toe_id,
                "data": data_to_post,
                "status": "success",
                "message": "Data posted successfully to provider"
            }
            
            # Add hash info if it was computed (for zip files)
            if result.get('zip_hash'):
                response['zip_hash'] = {
                    "algorithm": "SHA-256",
                    "value": result['zip_hash'],
                    "message": "Hash computed from zip file (without extracting contents)"
                }
                logger.info(f"✓ Returning zip hash in response: {result['zip_hash'][:16]}...")
            
            return response
            
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
            'catalog_cache_ttl': self.config['cache_ttl'],
            'toe_id': self.toe_id,
        }

    # ========================================================================
    # TOE ID Endpoint Handlers
    # ========================================================================

    async def set_toe_id(self, request: ToeIdRequest, authorization: Optional[str]):
        """
        Store the TOE ID that will be injected into future post_data payloads.
        Requires a valid caller JWT from the Authentication Manager.
        """
        self._require_valid_caller_jwt(authorization)

        toe_id = request.toe_id.strip()

        try:
            uuid.UUID(toe_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "BAD_REQUEST",
                    "message": "toe_id must be a valid UUID."
                }
            )

        self.toe_id = toe_id
        logger.info(f"TOE ID set for future post_data requests: {toe_id}")

        return {
            "status": "success",
            "toe_id": self.toe_id,
            "message": "TOE ID stored successfully"
        }

    def _require_valid_caller_jwt(self, authorization: Optional[str]) -> Dict:
        """Validate the caller's bearer JWT before accepting sensitive writes."""
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "MISSING_BEARER_TOKEN",
                    "message": "Send Authorization: Bearer <jwt> when posting the TOE ID."
                }
            )

        if not self.authentication_manager:
            raise HTTPException(
                status_code=503,
                detail="AuthenticationManager not configured"
            )

        token = authorization.split(" ", 1)[1].strip()
        if not token:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "MISSING_BEARER_TOKEN",
                    "message": "Bearer token is empty."
                }
            )

        try:
            validation = self.authentication_manager.validate_jwt(token)
        except Exception as e:
            logger.error(f"Caller JWT validation failed: {e}")
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "INVALID_BEARER_TOKEN",
                    "message": "Could not validate caller JWT with IAM /oauth/userinfo."
                }
            )

        if validation.get("active") is not True:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "INACTIVE_BEARER_TOKEN",
                    "message": "Caller JWT is not active."
                }
            )

        return validation

    async def get_toe_id(self):
        """
        Return the currently stored TOE ID, if one has been set.
        """
        if not self.toe_id:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "TOE_ID_NOT_SET",
                    "message": "No TOE ID has been set."
                }
            )

        return {
            "toe_id": self.toe_id,
            "status": "set"
        }

    def _inject_toe_id(self, data: str) -> str:
        """
        Inject the stored TOE ID into an IDS TextResource payload.

        The unified sender stores the file payload as JSON text in the first
        ids:description entry, so update that nested payload. Also set a
        top-level toe_id for callers that send simpler JSON documents.
        """
        try:
            resource_data = json.loads(data)
        except json.JSONDecodeError:
            logger.warning("Could not inject TOE ID because data is not JSON")
            return data

        resource_data["toe_id"] = self.toe_id

        descriptions = resource_data.get("ids:description")
        if isinstance(descriptions, list):
            for description in descriptions:
                if not isinstance(description, dict):
                    continue

                desc_value = description.get("@value")
                if not isinstance(desc_value, str):
                    continue

                try:
                    nested_payload = json.loads(desc_value)
                except json.JSONDecodeError:
                    continue

                if isinstance(nested_payload, dict):
                    nested_payload["toe_id"] = self.toe_id
                    description["@value"] = json.dumps(nested_payload)
                    logger.debug("Injected TOE ID into ids:description payload")
                    break

        return json.dumps(resource_data)

    # ========================================================================
    # Authentication Endpoint Handlers
    # ========================================================================


    async def refresh_jwt(self):
        """
        Fetch a JWT from the Authentication Manager and store it in SQLite.
        """
        if not self.authentication_manager:
            raise HTTPException(
                status_code=503,
                detail="AuthenticationManager not configured"
            )

        try:
            metadata = self.authentication_manager.refresh_jwt()
            return {
                "status": "success",
                "message": "JWT refreshed and stored successfully",
                "token": metadata,
            }
        except Exception as e:
            logger.error(f"Failed to refresh JWT: {e}")
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "JWT_REFRESH_FAILED",
                    "message": str(e),
                }
            )

    async def jwt_status(self):
        """
        Return metadata for the stored JWT without returning the raw token.
        """
        if not self.authentication_manager:
            raise HTTPException(
                status_code=503,
                detail="AuthenticationManager not configured"
            )

        return self.authentication_manager.get_token_metadata()

    async def authenticated_jwt_request(self, request: AuthenticatedRequest):
        """
        Call the Authentication Manager using the JWT stored in SQLite.
        """
        if not self.authentication_manager:
            raise HTTPException(
                status_code=503,
                detail="AuthenticationManager not configured"
            )

        try:
            return self.authentication_manager.authenticated_request(
                method=request.method,
                path=request.path,
                payload=request.payload,
            )
        except RuntimeError as e:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "JWT_NOT_AVAILABLE",
                    "message": str(e),
                }
            )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "BAD_REQUEST",
                    "message": str(e),
                }
            )
        except Exception as e:
            logger.error(f"Authenticated JWT request failed: {e}")
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "JWT_REQUEST_FAILED",
                    "message": str(e),
                }
            )
