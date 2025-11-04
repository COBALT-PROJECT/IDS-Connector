# ================================================================================
# file_extractor_service.py
# ================================================================================
"""
File Extractor Service - Extracts files from JSON payloads
Supports: .zip, .ipynb, .py files
"""
import json
import base64
import logging
from typing import Optional, Dict, Tuple, Any
from datetime import datetime
import io

logger = logging.getLogger(__name__)


class FileExtractorService:
    """
    Service class for extracting files from JSON payloads
    Handles ZIP files, Jupyter notebooks, and Python scripts
    """
    
    SUPPORTED_FILE_TYPES = {
        'zip_file': {
            'extensions': ['.zip'],
            'mime_types': ['application/zip', 'application/x-zip-compressed'],
            'encoding': 'base64'
        },
        'jupyter_notebook': {
            'extensions': ['.ipynb'],
            'mime_types': ['application/x-ipynb+json'],
            'encoding': 'json'
        },
        'python_script': {
            'extensions': ['.py'],
            'mime_types': ['text/x-python', 'application/x-python'],
            'encoding': 'text'
        }
    }
    
    def __init__(self):
        """Initialize the File Extractor Service"""
        logger.info("FileExtractorService initialized")
    
    def extract_file_from_json(self, json_data: Any) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """
        Extract file data and metadata from JSON payload
        
        Args:
            json_data: JSON data (string or dict) containing file information
        
        Returns:
            Tuple containing:
                - file_data (bytes): The extracted file content
                - metadata (dict): File metadata
                - data_type (str): 'binary' or 'text'
        """
        try:
            # Parse the main payload if it's a string
            if isinstance(json_data, str):
                payload = json.loads(json_data)
            else:
                payload = json_data
            
            # Try IDS format first (nested structure)
            if "data" in payload and "data_type" in payload:
                return self._extract_from_ids_format(payload)
            
            # Try direct format (without IDS wrapper)
            elif "type" in payload and ("data" in payload or "content" in payload):
                return self._extract_from_direct_format(payload)
            
            # Try to detect file in resource description
            elif "ids:description" in payload:
                return self._extract_from_resource_description(payload)
                
        except Exception as e:
            logger.error(f"Error extracting file from JSON: {str(e)}")
            return None, None, None
        
        logger.warning("No extractable file found in JSON payload")
        return None, None, None
    
    def _extract_from_ids_format(self, payload: Dict) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """Extract file from IDS TOE format"""
        try:
            # Parse the nested IDS data
            ids_data = json.loads(payload["data"]) if isinstance(payload["data"], str) else payload["data"]
            
            # Check for description field containing file data
            descriptions = ids_data.get("ids:description", [])
            if descriptions:
                # Get the first description value
                desc_value = descriptions[0].get("@value", "{}") if isinstance(descriptions[0], dict) else descriptions[0]
                
                # Parse the inner JSON
                inner_data = json.loads(desc_value) if isinstance(desc_value, str) else desc_value
                
                # Extract based on file type
                return self._process_file_data(inner_data)
            
            # Check if the data itself contains file information
            if "type" in ids_data and ("data" in ids_data or "content" in ids_data):
                return self._process_file_data(ids_data)
                
        except Exception as e:
            logger.error(f"Error extracting from IDS format: {str(e)}")
        
        return None, None, None
    
    def _extract_from_direct_format(self, payload: Dict) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """Extract file from direct format (without IDS wrapper)"""
        return self._process_file_data(payload)
    
    def _extract_from_resource_description(self, payload: Dict) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """Extract file from resource description field"""
        try:
            descriptions = payload.get("ids:description", [])
            if descriptions:
                # Get the first description value
                desc_value = descriptions[0].get("@value", "{}") if isinstance(descriptions[0], dict) else descriptions[0]
                
                # Try to parse as JSON containing file data
                try:
                    file_data_json = json.loads(desc_value) if isinstance(desc_value, str) else desc_value
                    if "type" in file_data_json:
                        return self._process_file_data(file_data_json)
                except:
                    # If it's not JSON, treat it as plain text content
                    if isinstance(desc_value, str) and len(desc_value) > 0:
                        metadata = {
                            "type": "text",
                            "filename": "extracted_content.txt",
                            "mime_type": "text/plain",
                            "size_bytes": len(desc_value),
                            "extraction_timestamp": datetime.now().isoformat()
                        }
                        return desc_value.encode('utf-8'), metadata, "text"
        except Exception as e:
            logger.error(f"Error extracting from resource description: {str(e)}")
        
        return None, None, None
    
    def _process_file_data(self, data: Dict) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """
        Process file data based on type
        
        Args:
            data: Dictionary containing file data and metadata
        
        Returns:
            Tuple of (file_bytes, metadata, data_type)
        """
        file_type = data.get("type", "unknown")
        metadata = data.get("metadata", {})
        
        # Add extraction timestamp if not present
        if "extraction_timestamp" not in metadata:
            metadata["extraction_timestamp"] = datetime.now().isoformat()
        
        # Add type to metadata
        metadata["type"] = file_type
        
        try:
            if file_type == "zip_file":
                # Extract ZIP file (base64 encoded)
                if "data" in data:
                    file_bytes = base64.b64decode(data["data"])
                    metadata["size_bytes"] = len(file_bytes)
                    return file_bytes, metadata, "binary"
                    
            elif file_type == "jupyter_notebook":
                # Extract Jupyter notebook (JSON)
                if "content" in data:
                    content = data["content"]
                    if isinstance(content, dict):
                        file_str = json.dumps(content, indent=2)
                    else:
                        file_str = str(content)
                    file_bytes = file_str.encode('utf-8')
                    metadata["size_bytes"] = len(file_bytes)
                    metadata["lines"] = file_str.count('\n') + 1
                    return file_bytes, metadata, "text"
                    
            elif file_type == "python_script":
                # Extract Python script (text)
                if "content" in data:
                    content = data["content"]
                    file_bytes = content.encode('utf-8') if isinstance(content, str) else str(content).encode('utf-8')
                    metadata["size_bytes"] = len(file_bytes)
                    metadata["lines_of_code"] = content.count('\n') + 1 if isinstance(content, str) else 0
                    return file_bytes, metadata, "text"
            
            # Generic text extraction
            elif "content" in data:
                content = data["content"]
                file_bytes = content.encode('utf-8') if isinstance(content, str) else str(content).encode('utf-8')
                metadata["size_bytes"] = len(file_bytes)
                metadata["type"] = "text"
                return file_bytes, metadata, "text"
            
            # Generic binary extraction
            elif "data" in data:
                try:
                    # Assume base64 encoding for binary data
                    file_bytes = base64.b64decode(data["data"])
                    metadata["size_bytes"] = len(file_bytes)
                    metadata["type"] = "binary"
                    return file_bytes, metadata, "binary"
                except:
                    # If not base64, treat as text
                    file_bytes = data["data"].encode('utf-8') if isinstance(data["data"], str) else str(data["data"]).encode('utf-8')
                    metadata["size_bytes"] = len(file_bytes)
                    metadata["type"] = "text"
                    return file_bytes, metadata, "text"
                    
        except Exception as e:
            logger.error(f"Error processing file data of type '{file_type}': {str(e)}")
        
        return None, None, None
    
    def create_file_response(self, file_bytes: bytes, metadata: Dict, data_type: str) -> Dict:
        """
        Create a response object for file extraction
        
        Args:
            file_bytes: The file content as bytes
            metadata: File metadata
            data_type: 'binary' or 'text'
        
        Returns:
            Dictionary containing file data and metadata for API response
        """
        response = {
            "success": True,
            "metadata": metadata,
            "data_type": data_type
        }
        
        # For binary data, encode as base64 for JSON response
        if data_type == "binary":
            response["data"] = base64.b64encode(file_bytes).decode('ascii')
            response["encoding"] = "base64"
        else:
            # For text data, include as string
            try:
                response["data"] = file_bytes.decode('utf-8')
                response["encoding"] = "utf-8"
            except UnicodeDecodeError:
                # If decoding fails, fall back to base64
                response["data"] = base64.b64encode(file_bytes).decode('ascii')
                response["encoding"] = "base64"
        
        return response
    
    def get_file_extension(self, metadata: Dict) -> str:
        """
        Determine appropriate file extension based on metadata
        
        Args:
            metadata: File metadata dictionary
        
        Returns:
            Suggested file extension with dot (e.g., '.zip')
        """
        # Check if filename already has extension
        filename = metadata.get("filename", "")
        if filename and '.' in filename:
            return ""  # Already has extension
        
        # Determine extension based on type or mime_type
        file_type = metadata.get("type", "")
        mime_type = metadata.get("mime_type", "")
        
        # Check against known types
        for known_type, type_info in self.SUPPORTED_FILE_TYPES.items():
            if file_type == known_type:
                return type_info['extensions'][0]
            
            if mime_type in type_info['mime_types']:
                return type_info['extensions'][0]
        
        # Fallback based on mime_type patterns
        if "zip" in mime_type:
            return ".zip"
        elif "ipynb" in mime_type or "jupyter" in mime_type:
            return ".ipynb"
        elif "python" in mime_type:
            return ".py"
        elif "json" in mime_type:
            return ".json"
        elif "text" in mime_type:
            return ".txt"
        elif file_type == "binary":
            return ".bin"
        else:
            return ".dat"
    
    def extract_from_resource(self, resource: Dict) -> Optional[Dict]:
        """
        Extract file from an IDS resource if it contains embedded file data
        
        Args:
            resource: IDS resource dictionary
        
        Returns:
            File response dictionary or None if no file found
        """
        # Try to extract file from the resource
        file_bytes, metadata, data_type = self.extract_file_from_json(resource)
        
        if file_bytes and metadata:
            # Create response
            response = self.create_file_response(file_bytes, metadata, data_type)
            
            # Add resource information to metadata
            resource_id = resource.get('@id', 'unknown')
            response["metadata"]["source_resource"] = resource_id
            response["metadata"]["resource_name"] = resource_id.split('/')[-1]
            
            logger.info(f"Successfully extracted file from resource: {resource_id}")
            return response
        
        return None