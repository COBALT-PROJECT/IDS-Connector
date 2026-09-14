# ================================================================================
# ids_consumer_interface.py
# ================================================================================
"""
IDS Consumer Interface - API endpoint handlers for Consumer Resource Server
"""
from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.responses import JSONResponse, StreamingResponse, Response
import logging
from typing import Dict, Optional
import json
import base64
import io
import hmac
from pydantic import BaseModel
from sdt_config_store import sdt_config
from resource_state_store import resource_state, CONFIRMED, DEAD

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
        @app.get("/api/IDSconnector/get_data_request", tags=["IDSconnector-SDT"])
        async def get_data_request(
            toe_id: str = Query(..., description="entity to be synchronized with"),
            data_type: str = Query(..., description="Data being received", example="json"),
            data_path: str = Query(..., description="Path to the data source"),
            access_token: Optional[str] = Query(
                None,
                description="Caller's access token; must match the token registered with the IDS-SDT"
            ),
            authorization: Optional[str] = Header(
                None,
                description="Optional 'Bearer <token>' header alternative to the access_token query parameter"
            ),
        ):
            return await self.get_data_request(
                toe_id, data_type, data_path,
                access_token=access_token,
                authorization=authorization,
            )
        
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

        # Get cleared resource IDs endpoint
        @app.get("/api/IDSconnector/cleared-ids")
        async def get_cleared_ids():
            return await self.get_cleared_ids()

        # Confirm endpoint - SDT reports back what actually happened to each
        # resource it was handed, so the connector's notion of "already
        # synced" reflects real ingestion instead of a guess.
        @app.post("/api/IDSconnector/confirm", tags=["IDSconnector-SDT"])
        async def confirm_sync_results(
            payload: Dict,
            access_token: Optional[str] = Query(
                None,
                description="Caller's access token; must match the token registered with the IDS-SDT"
            ),
            authorization: Optional[str] = Header(None),
        ):
            return await self.confirm_sync_results(payload, access_token=access_token, authorization=authorization)

        # Reconciliation / diagnostics endpoint - state counts, optionally
        # scoped to one TOE, so "did everything really get confirmed" is a
        # question with a direct answer instead of a guess.
        @app.get("/api/IDSconnector/sync-status", tags=["IDSconnector-SDT"])
        async def get_sync_status(
            toe_id: Optional[str] = Query(None, description="Optional TOE ID to scope the summary to")
        ):
            return await self.get_sync_status(toe_id)
        
        # File extraction endpoint
        @app.get("/api/IDSconnector/extract_file", tags=["IDSconnector-SDT"])
        async def extract_file(
            data_path: str = Query(..., description="Path to the data source containing file"),
            return_format: str = Query("json", description="Response format: 'json' or 'binary'")
        ):
            return await self.extract_file(data_path, return_format)
        
        # SDT config registration endpoint
        @app.post("/api/IDSconnector/SDT/configauth", tags=["IDSconnector-SDT-registration"])
        async def register_sdt_config(payload: Dict):
            return await self.register_sdt_config(payload)

        # SDT config status endpoint
        @app.get("/api/IDSconnector/SDT/configauth", tags=["IDSconnector-SDT-registration"])
        async def get_sdt_config_status():
            return await self.get_sdt_config_status()

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
    # Helper Methods
    # ========================================================================
    
    def _parse_resource_description(self, resource: Dict) -> Optional[Dict]:
        """
        Parse the JSON embedded in a resource's ids:description field. This
        is the sender's upload payload - {"toe_id", "type", "metadata": {...
        "filename" ...}, "data"/"content"} - which arrives multiply-escaped
        depending on how many times it was round-tripped through JSON
        encoding on the way in.

        Args:
            resource: Resource dictionary

        Returns:
            Parsed content dict, or None if there's nothing parseable.
        """
        try:
            resource_id = resource.get("@id", "unknown")
            descriptions = resource.get("ids:description", [])

            if not descriptions:
                logger.debug(f"No descriptions found in resource {resource_id}")
                return None

            # Get the first description value
            desc_value = descriptions[0].get("@value", "{}") if isinstance(descriptions[0], dict) else descriptions[0]

            if not desc_value or desc_value == "{}":
                logger.debug(f"Empty description value in resource {resource_id}")
                return None

            # Log the actual content for debugging
            logger.info(f"Parsing resource {resource_id.split('/')[-1]}: desc_value type={type(desc_value).__name__}, len={len(str(desc_value))}, preview={str(desc_value)[:150]}")

            # Try to parse the JSON content
            if isinstance(desc_value, str):
                content = None

                # Strategy 1: Try standard JSON parse
                try:
                    content = json.loads(desc_value)
                    logger.debug(f"✓ Parsed with standard JSON for {resource_id.split('/')[-1]}")
                except json.JSONDecodeError:
                    pass

                # Strategy 2: Try manual unescape of \" then parse
                # This handles escaped quotes like {\"toe_id\": \"1234\"}
                if content is None:
                    try:
                        # Replace the literal backslash-quote sequence with just quote
                        unescaped = desc_value.replace('\\', '').replace('""', '"')
                        logger.info(f"After removing backslashes: {unescaped[:100]}")
                        content = json.loads(unescaped)
                        logger.info(f"✓ Parsed with manual unescape for {resource_id.split('/')[-1]}")
                    except json.JSONDecodeError as e:
                        logger.info(f"Manual unescape failed: {e}")
                        pass

                # Strategy 3: Try double-decode (handles double-escaped JSON like \\\" )
                if content is None:
                    try:
                        # First decode to unescape the string
                        unescaped = json.loads(desc_value)
                        # Second decode to parse the actual JSON
                        if isinstance(unescaped, str):
                            content = json.loads(unescaped)
                            logger.debug(f"✓ Parsed with double-decode for {resource_id.split('/')[-1]}")
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Strategy 4: Try replacing single quotes with double quotes
                if content is None:
                    try:
                        desc_value_fixed = desc_value.replace("'", '"')
                        content = json.loads(desc_value_fixed)
                        logger.debug(f"✓ Parsed with quote replacement for {resource_id.split('/')[-1]}")
                    except json.JSONDecodeError:
                        pass

                # If all strategies failed, log and return None
                if content is None:
                    logger.warning(f"Failed to parse description for resource {resource_id.split('/')[-1]}")
                    logger.debug(f"Failed content preview: {desc_value[:200]}")
                    return None
            else:
                content = desc_value

            return content if isinstance(content, dict) else None

        except Exception as e:
            logger.error(f"Exception parsing description for resource {resource.get('@id', 'unknown')}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

        return None

    def _extract_toe_id_from_resource(self, resource: Dict, content: Optional[Dict] = None) -> Optional[str]:
        """
        Extract toe_id from resource description field.

        Args:
            resource: Resource dictionary
            content: Already-parsed description content, if the caller has
                     it (avoids re-parsing); parsed fresh if omitted.

        Returns:
            toe_id if found, None otherwise
        """
        resource_id = resource.get("@id", "unknown")
        if content is None:
            content = self._parse_resource_description(resource)
        if content is None:
            return None

        toe_id = content.get("toe_id")
        if toe_id:
            logger.info(f"✓ Extracted toe_id '{toe_id}' from resource {resource_id.split('/')[-1]}")
        else:
            logger.debug(f"No toe_id field found in resource {resource_id.split('/')[-1]}")
        return toe_id

    def _extract_filename_from_resource(self, resource: Dict, content: Optional[Dict] = None) -> Optional[str]:
        """
        Extract the uploaded filename from a resource's embedded metadata
        (payload_content["metadata"]["filename"] in ids_toe_unified_sender.py).
        Used, together with toe_id, to identify "the same file" across
        re-uploads/new versions for duplicate resolution.

        Returns:
            filename if found, None otherwise
        """
        if content is None:
            content = self._parse_resource_description(resource)
        if content is None:
            return None
        return content.get("metadata", {}).get("filename")

    def _validate_caller_token(
        self,
        access_token: Optional[str],
        authorization: Optional[str],
        context: str = "",
    ) -> None:
        """
        Validate the caller's access token against the one SDT registered
        via POST /api/IDSconnector/SDT/configauth. Shared by every endpoint
        that requires the same shared-secret auth model (get_data_request,
        confirm).

        Raises:
            HTTPException(401) on any validation failure.
        """
        # Resolve caller-provided token: prefer explicit query parameter,
        # fall back to 'Authorization: Bearer <token>' header.
        caller_token = access_token
        if not caller_token and authorization:
            auth = authorization.strip()
            if auth.lower().startswith("bearer "):
                caller_token = auth[7:].strip()
            else:
                caller_token = auth

        if not caller_token:
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHORIZED", "message": "access_token is required."}
            )

        # Ensure the IDS-SDT has been registered with an access token
        if not sdt_config.is_configured:
            logger.warning("Token validation requested but SDT config is not initialized")
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHORIZED", "message": "IDS-SDT is not configured with an access token."}
            )

        expected_token = sdt_config.get("access_token")
        if not expected_token:
            logger.warning("No access_token registered in SDT config store")
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHORIZED", "message": "IDS-SDT has no access token registered."}
            )

        # Constant-time comparison to mitigate timing attacks
        if not hmac.compare_digest(str(caller_token), str(expected_token)):
            logger.warning(f"Access token mismatch ({context})" if context else "Access token mismatch")
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHORIZED", "message": "Invalid access token."}
            )

        logger.info(f"Access token validated successfully ({context})" if context else "Access token validated successfully")
    
    # ========================================================================
    # Main Data Request Handler (YAML Spec Compatible)
    # ========================================================================
    
    async def get_data_request(
        self, 
        toe_id: str, 
        data_type: str, 
        data_path: str,
        access_token: Optional[str] = None,
        authorization: Optional[str] = None,
    ):
        """
        Get data request endpoint compatible with YAML specification
        
        Args:
            toe_id: Entity to be synchronized with
            data_type: Type of data being received (e.g., "json")
            data_path: Path to the data source
            access_token: Caller-supplied access token (query parameter)
            authorization: Optional 'Bearer <token>' Authorization header
        
        Returns:
            dict: Data response object
        
        Raises:
            HTTPException: For various error conditions (400, 401, 404, 500)
        """
        try:
            self._validate_caller_token(
                access_token, authorization,
                context=f"toe_id={toe_id}, data_path={data_path}"
            )

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

            # Revert anything stuck DELIVERED past the timeout (SDT crashed
            # mid-ingest, or the confirm call itself got dropped) so it's
            # retried instead of lost forever.
            resource_state.sweep_expired_deliveries()

            # Resource listing has no time-based cache - always fetch fresh.
            # See resource_service.py / resource_state_store.py.
            resources = self.resource_service.get_all_text_resources()

            # Filter resources based on toe_id if provided
            filtered_resources = resources
            if toe_id:
                original_count = len(resources)
                # Filter by checking toe_id in description field
                filtered_resources = [
                    res for res in resources
                    if self._extract_toe_id_from_resource(res) == toe_id
                ]
                logger.info(f"Filtered resources by toe_id '{toe_id}': {original_count} -> {len(filtered_resources)}")

            # Use filtered resources for the rest of the processing
            resources = filtered_resources

            # Check if requesting all resources FIRST
            if data_path.lower() in ['all', '*', 'resources']:
                # Only offer resources SDT hasn't already confirmed ingesting,
                # and that aren't already checked out by another in-flight
                # sync call for this same TOE.
                candidates = [res for res in resources if resource_state.is_available(res.get('@id', ''))]

                # Resolve duplicates: multiple resources sharing the same
                # (toe_id, filename) are re-uploads/new versions of the same
                # file. Keep only the newest and confirm the rest directly -
                # they must never be offered or retried on their own.
                # ids_toe_unified_sender.py suffixes resource IDs with a
                # sortable "YYYYMMDD-HHMMSS" timestamp, so lexical max == newest.
                groups: Dict[tuple, list] = {}
                for res in candidates:
                    content = self._parse_resource_description(res)
                    filename = self._extract_filename_from_resource(res, content=content)
                    key = (toe_id, filename or res.get('@id'))
                    groups.setdefault(key, []).append(res)

                kept = []
                for group in groups.values():
                    if len(group) > 1:
                        group.sort(key=lambda r: r.get('@id', ''))
                        newest, superseded = group[-1], group[:-1]
                        for old in superseded:
                            logger.info(
                                f"Resource {old.get('@id')} superseded by newer upload "
                                f"{newest.get('@id')} of the same file - confirming directly"
                            )
                            resource_state.confirm_superseded(old.get('@id'))
                        kept.append(newest)
                    else:
                        kept.append(group[0])

                # Claim (atomically mark DELIVERED) only what we're actually
                # about to hand back - closes the race between two
                # overlapping sync calls picking up the same resource.
                claimed_ids = set(resource_state.claim_available([res.get('@id') for res in kept]))
                to_return = [res for res in kept if res.get('@id') in claimed_ids]

                logger.info(
                    f"get_data_request(all): {len(resources)} matched toe_id, "
                    f"{len(candidates)} available, {len(to_return)} returned this call"
                )

                payload = {"total": len(to_return), "resources": to_return}
                response_data = json.dumps(payload) if data_type.lower() == "json" else str(payload)

                # An empty result here is a normal, expected outcome -
                # "nothing new for this TOE right now" - not an error. A
                # poller sees 200 / total=0, never a 404, for this path.
                return {
                    "data_type": data_type,
                    "data": response_data
                }

            # Named resource lookup (legacy path): no match really is a 404.
            if not resources:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "NOT_FOUND",
                        "message": f"No data at data_path: {data_path}"
                    }
                )

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
        Operator escape hatch: forget all tracked sync state. Every
        CONFIRMED/DEAD resource becomes AVAILABLE again and will be
        re-offered to SDT (whose own content dedupe will generally no-op
        already-ingested ones straight back to 'skipped'/CONFIRMED).

        This used to clear a time-based cache; there isn't one anymore -
        it now resets resource_state_store instead. Use it to force a full
        re-sync, not as routine maintenance.

        Returns:
            dict: Success message
        """
        count = resource_state.reset_all()
        return {"status": "ok", "message": "Resource sync state reset", "resources_reset": count}

    async def get_cleared_ids(self):
        """
        Get the list of resources SDT has already confirmed ingesting (or
        that were quarantined as DEAD). Kept at its original URL for
        backward compatibility; the underlying source of truth is now
        resource_state_store, not a "cleared" set.

        Returns:
            dict: Confirmed/dead resource IDs and a full state summary
        """
        confirmed_ids = resource_state.get_ids_by_state(CONFIRMED)
        dead_ids = resource_state.get_ids_by_state(DEAD)
        return {
            "cleared_resource_ids": confirmed_ids,  # legacy field name, now means "confirmed"
            "count": len(confirmed_ids),
            "dead_resource_ids": dead_ids,
            "summary": resource_state.get_summary()
        }

    async def confirm_sync_results(
        self,
        payload: Dict,
        access_token: Optional[str] = None,
        authorization: Optional[str] = None,
    ):
        """
        Receive SDT's per-resource ingestion outcomes for a prior sync call
        and update resource_state_store accordingly. This is what makes
        "already synced" mean "SDT actually confirmed it", not "we handed
        it out once".

        Expected JSON body:
        {
            "toe_id": str,
            "results": [
                {"resource_id": str, "outcome": "created"|"updated"|"skipped"|"failed"},
                ...
            ]
        }

        Returns:
            dict: Per-resource resulting state, plus a state summary.
        """
        self._validate_caller_token(access_token, authorization, context="confirm")

        results = payload.get("results", [])
        if not isinstance(results, list) or not results:
            raise HTTPException(
                status_code=400,
                detail={"code": "BAD_REQUEST", "message": "results must be a non-empty list."}
            )

        applied = []
        skipped_entries = []
        for entry in results:
            resource_id = entry.get("resource_id")
            outcome = entry.get("outcome")
            if not resource_id or not outcome:
                logger.warning(f"Ignoring malformed confirm entry (missing resource_id/outcome): {entry}")
                skipped_entries.append(entry)
                continue
            new_state = resource_state.confirm(resource_id, outcome)
            applied.append({"resource_id": resource_id, "outcome": outcome, "state": new_state})

        logger.info(f"Confirm received for toe_id={payload.get('toe_id')}: {len(applied)} applied, {len(skipped_entries)} malformed")

        return {
            "status": "ok",
            "applied": applied,
            "ignored": skipped_entries,
            "summary": resource_state.get_summary()
        }

    async def get_sync_status(self, toe_id: Optional[str] = None):
        """
        Reconciliation/diagnostics endpoint: state counts across all
        tracked resources. `toe_id` is accepted for future per-TOE scoping;
        resource_state_store doesn't key by toe_id today (a resource's
        toe_id lives in its parsed description, not in the state entry), so
        this currently reports the global summary regardless.

        Returns:
            dict: Counts by state (available resources aren't tracked until
                  they transition, so 'available' here means "explicitly
                  tracked and currently available", e.g. after a failed
                  attempt - not the full untracked catalog).
        """
        return {
            "toe_id": toe_id,
            "summary": resource_state.get_summary()
        }

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
    
    # ========================================================================
    # SDT Config Registration Handlers
    # ========================================================================

    async def register_sdt_config(self, payload: Dict):
        """
        Receive SDT registration payload and store it in SDTConfigStore.

        Expected JSON body:
        {
            "sdt_id": str,
            "client_id": str,
            "client_secret": str,
            "access_token": str,
            "components": {
                "sdt": str,
                "ids_connector": str,
                "watchtower": str
            }
        }
        """
        required_fields = ["sdt_id", "client_id", "client_secret", "access_token", "components"]
        missing = [f for f in required_fields if f not in payload]
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "BAD_REQUEST",
                    "message": f"Missing required fields: {', '.join(missing)}"
                }
            )

        sdt_config.set(payload)
        logger.info(f"SDT config registered — sdt_id={payload.get('sdt_id')}")

        return {
            "status": "ok",
            "message": "SDT configuration stored successfully",
            "sdt_id": payload.get("sdt_id"),
            "components": list(payload.get("components", {}).keys())
        }

    async def get_sdt_config_status(self):
        """Return the current SDT configuration status (secrets redacted)."""
        return sdt_config.status()

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