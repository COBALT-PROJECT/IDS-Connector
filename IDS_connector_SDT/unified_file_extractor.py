#!/usr/bin/env python3
"""
Unified utility to extract files from JSON payloads
Supports: .zip, .ipynb, .py files
Note: implement this file's functionality inside the SDT to get the files directly that were posted into the IDS TOE.
"""
import json
import base64
import sys
import os

def extract_file_from_json(json_data):
    """
    Extract file data and metadata from JSON payload
    """
    try:
        # Parse the main payload
        if isinstance(json_data, str):
            payload = json.loads(json_data)
        else:
            payload = json_data
        
        # Check for response format with escaped JSON in data field FIRST
        if "success" in payload and "data" in payload and "data_type" in payload:
            try:
                # The data field contains escaped JSON
                data_str = payload["data"]
                
                # Replace escaped quotes to make it valid JSON
                data_str = data_str.replace('\\\\"', '"')
                
                # Try to parse the data field
                inner_data = json.loads(data_str)
                
                file_type = inner_data.get("type", "unknown")
                metadata = inner_data.get("metadata", {})
                
                if file_type == "zip_file" and "data" in inner_data:
                    file_data = base64.b64decode(inner_data["data"])
                    return file_data, metadata, "binary"
                elif file_type == "jupyter_notebook" and "content" in inner_data:
                    file_data = json.dumps(inner_data["content"], indent=2)
                    return file_data.encode('utf-8'), metadata, "text"
                elif file_type == "python_script" and "content" in inner_data:
                    file_data = inner_data["content"]
                    return file_data.encode('utf-8'), metadata, "text"
            except json.JSONDecodeError as e:
                print(f"JSON decode error in data field: {e}")
                pass
        
        # Extract the IDS data if present
        elif "data" in payload and "data_type" in payload:
            # This is the outer IDS TOE payload
            ids_data = json.loads(payload["data"])
            
            # Find the description field which contains our file data
            descriptions = ids_data.get("ids:description", [])
            if descriptions:
                inner_json = descriptions[0].get("@value", "{}")
                inner_data = json.loads(inner_json)
                
                # Determine file type and extract accordingly
                file_type = inner_data.get("type", "unknown")
                metadata = inner_data.get("metadata", {})
                
                if file_type == "zip_file":
                    # Extract ZIP file (base64 encoded)
                    if "data" in inner_data:
                        file_data = base64.b64decode(inner_data["data"])
                        return file_data, metadata, "binary"
                        
                elif file_type == "jupyter_notebook":
                    # Extract Jupyter notebook (JSON)
                    if "content" in inner_data:
                        file_data = json.dumps(inner_data["content"], indent=2)
                        return file_data.encode('utf-8'), metadata, "text"
                        
                elif file_type == "python_script":
                    # Extract Python script (text)
                    if "content" in inner_data:
                        file_data = inner_data["content"]
                        return file_data.encode('utf-8'), metadata, "text"
        
        # Alternative: Direct format (without IDS wrapper)
        elif "type" in json_data and "metadata" in json_data:
            file_type = json_data.get("type", "unknown")
            metadata = json_data.get("metadata", {})
            
            if file_type == "zip_file" and "data" in json_data:
                file_data = base64.b64decode(json_data["data"])
                return file_data, metadata, "binary"
            elif file_type == "jupyter_notebook" and "content" in json_data:
                file_data = json.dumps(json_data["content"], indent=2)
                return file_data.encode('utf-8'), metadata, "text"
            elif file_type == "python_script" and "content" in json_data:
                file_data = json_data["content"]
                return file_data.encode('utf-8'), metadata, "text"
                
    except Exception as e:
        print(f"Error extracting file: {e}")
        return None, None, None
    
    return None, None, None

def save_file(file_data, metadata, data_type, output_path=None):
    """
    Save the extracted file to disk
    """
    if not output_path:
        output_path = metadata.get("filename", "extracted_file")
        
        # Add appropriate extension if missing
        if not os.path.splitext(output_path)[1]:
            mime_type = metadata.get("mime_type", "")
            if "zip" in mime_type:
                output_path += ".zip"
            elif "ipynb" in mime_type or "jupyter" in mime_type:
                output_path += ".ipynb"
            elif "python" in mime_type:
                output_path += ".py"
    
    # Write file
    mode = 'wb' if data_type == "binary" else 'wb'
    with open(output_path, mode) as f:
        f.write(file_data)
    
    return output_path

def print_metadata(metadata):
    """Print file metadata in a formatted way"""
    print("\nFile Metadata:")
    print("-" * 40)
    
    # Define the order of keys to display
    priority_keys = ['filename', 'mime_type', 'size_bytes', 'encoding', 'upload_timestamp']
    
    # Print priority keys first
    for key in priority_keys:
        if key in metadata:
            print(f"  {key.replace('_', ' ').title()}: {metadata[key]}")
    
    # Print remaining keys
    for key, value in metadata.items():
        if key not in priority_keys:
            # Format the key nicely
            formatted_key = key.replace('_', ' ').title()
            
            # Handle different value types
            if isinstance(value, list):
                if len(value) <= 5:
                    print(f"  {formatted_key}: {', '.join(str(v) for v in value)}")
                else:
                    print(f"  {formatted_key}: {', '.join(str(v) for v in value[:5])}... ({len(value)} total)")
            else:
                print(f"  {formatted_key}: {value}")
    print("-" * 40)

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_file_unified.py <json_file> [output_file_path]")
        print("\nThis utility extracts files from JSON payloads")
        print("Supported formats:")
        print("  - ZIP files (base64 encoded)")
        print("  - Jupyter notebooks (.ipynb)")
        print("  - Python scripts (.py)")
        print("\nExample:")
        print("  python extract_file_unified.py response.json")
        print("  python extract_file_unified.py response.json output.zip")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Read JSON file
    try:
        with open(json_file, 'r') as f:
            json_data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)
    
    # Extract file data
    print("Extracting file from JSON payload...")
    file_data, metadata, data_type = extract_file_from_json(json_data)
    
    if file_data and metadata:
        # Print metadata
        print_metadata(metadata)
        
        # Save file
        saved_path = save_file(file_data, metadata, data_type, output_path)
        
        print(f"\n✓ File extracted and saved to: {saved_path}")
        print(f"  File size: {len(file_data)} bytes")
        
        # Provide type-specific information
        mime_type = metadata.get("mime_type", "")
        if "zip" in mime_type:
            print("  Type: ZIP archive")
            print("  Tip: You can unzip it with: unzip " + saved_path)
        elif "ipynb" in mime_type:
            print("  Type: Jupyter Notebook")
            print("  Tip: Open with: jupyter notebook " + saved_path)
        elif "python" in mime_type:
            print("  Type: Python script")
            lines = metadata.get("lines_of_code", "?")
            print(f"  Lines of code: {lines}")
    else:
        print("✗ No file data found in JSON payload")
        print("\nTip: Make sure the JSON file contains data from IDS TOE response")
        sys.exit(1)

if __name__ == "__main__":
    main()