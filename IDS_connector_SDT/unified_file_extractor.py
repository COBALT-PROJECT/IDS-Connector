#!/usr/bin/env python3
"""
Unified utility to extract files from JSON payloads - OOP Version
Supports: .zip, .ipynb, .py files
Note: implement this file's functionality inside the SDT to get the files directly that were posted into the IDS TOE.
"""
import json
import base64
import sys
import os


class file_extractor:
    """Class to handle extraction of files from JSON payloads, import this class into SDT"""
    
    def __init__(self, json_file_path=None, output_path=None):
        """
        Initialize the file extractor
        
        Args:
            json_file_path: Path to the JSON file to extract from
            output_path: Optional path for the output file
        """
        self.json_file_path = json_file_path
        self.output_path = output_path
        self.json_data = None
        self.file_data = None
        self.metadata = None
        self.data_type = None
    
    def load_json_file(self, json_file_path=None):
        """
        Load JSON data from file
        
        Args:
            json_file_path: Optional path to override instance path
        """
        path = json_file_path or self.json_file_path
        if not path:
            raise ValueError("No JSON file path provided")
        
        try:
            with open(path, 'r') as f:
                self.json_data = json.load(f)
            return True
        except Exception as e:
            print(f"Error reading JSON file: {e}")
            return False
    
    def extract_file_from_json(self, json_data=None):
        """
        Extract file data and metadata from JSON payload
        
        Args:
            json_data: Optional JSON data to override instance data
            
        Returns:
            Tuple of (file_data, metadata, data_type)
        """
        data = json_data or self.json_data
        if not data:
            return None, None, None
        
        try:
            # Parse the main payload
            if isinstance(data, str):
                payload = json.loads(data)
            else:
                payload = data
            
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
                        self.file_data = file_data
                        self.metadata = metadata
                        self.data_type = "binary"
                        return file_data, metadata, "binary"
                    elif file_type == "jupyter_notebook" and "content" in inner_data:
                        file_data = json.dumps(inner_data["content"], indent=2)
                        self.file_data = file_data.encode('utf-8')
                        self.metadata = metadata
                        self.data_type = "text"
                        return self.file_data, metadata, "text"
                    elif file_type == "python_script" and "content" in inner_data:
                        file_data = inner_data["content"]
                        self.file_data = file_data.encode('utf-8')
                        self.metadata = metadata
                        self.data_type = "text"
                        return self.file_data, metadata, "text"
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
                            self.file_data = file_data
                            self.metadata = metadata
                            self.data_type = "binary"
                            return file_data, metadata, "binary"
                            
                    elif file_type == "jupyter_notebook":
                        # Extract Jupyter notebook (JSON)
                        if "content" in inner_data:
                            file_data = json.dumps(inner_data["content"], indent=2)
                            self.file_data = file_data.encode('utf-8')
                            self.metadata = metadata
                            self.data_type = "text"
                            return self.file_data, metadata, "text"
                            
                    elif file_type == "python_script":
                        # Extract Python script (text)
                        if "content" in inner_data:
                            file_data = inner_data["content"]
                            self.file_data = file_data.encode('utf-8')
                            self.metadata = metadata
                            self.data_type = "text"
                            return self.file_data, metadata, "text"
            
            # Alternative: Direct format (without IDS wrapper)
            elif "type" in payload and "metadata" in payload:
                file_type = payload.get("type", "unknown")
                metadata = payload.get("metadata", {})
                
                if file_type == "zip_file" and "data" in payload:
                    file_data = base64.b64decode(payload["data"])
                    self.file_data = file_data
                    self.metadata = metadata
                    self.data_type = "binary"
                    return file_data, metadata, "binary"
                elif file_type == "jupyter_notebook" and "content" in payload:
                    file_data = json.dumps(payload["content"], indent=2)
                    self.file_data = file_data.encode('utf-8')
                    self.metadata = metadata
                    self.data_type = "text"
                    return self.file_data, metadata, "text"
                elif file_type == "python_script" and "content" in payload:
                    file_data = payload["content"]
                    self.file_data = file_data.encode('utf-8')
                    self.metadata = metadata
                    self.data_type = "text"
                    return self.file_data, metadata, "text"
                    
        except Exception as e:
            print(f"Error extracting file: {e}")
            return None, None, None
        
        return None, None, None
    
    def save_file(self, file_data=None, metadata=None, data_type=None, output_path=None):
        """
        Save the extracted file to disk
        
        Args:
            file_data: Optional file data to override instance data
            metadata: Optional metadata to override instance metadata
            data_type: Optional data type to override instance data type
            output_path: Optional output path to override instance path
            
        Returns:
            Path where file was saved
        """
        # Use provided data or fall back to instance data
        file_data = file_data or self.file_data
        metadata = metadata or self.metadata
        data_type = data_type or self.data_type
        output_path = output_path or self.output_path
        
        if not file_data:
            raise ValueError("No file data to save")
        
        if not output_path:
            output_path = metadata.get("filename", "extracted_file") if metadata else "extracted_file"
            
            # Add appropriate extension if missing
            if not os.path.splitext(output_path)[1]:
                mime_type = metadata.get("mime_type", "") if metadata else ""
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
    
    def print_metadata(self, metadata=None):
        """
        Print file metadata in a formatted way
        
        Args:
            metadata: Optional metadata to override instance metadata
        """
        metadata = metadata or self.metadata
        if not metadata:
            print("No metadata available")
            return
        
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
    
    def process(self):
        """
        Main processing method to extract and save file
        
        Returns:
            True if successful, False otherwise
        """
        # Load JSON file
        if not self.json_data:
            if not self.load_json_file():
                return False
        
        # Extract file data
        print("Extracting file from JSON payload...")
        file_data, metadata, data_type = self.extract_file_from_json()
        
        if file_data and metadata:
            # Print metadata
            self.print_metadata(metadata)
            
            # Save file
            saved_path = self.save_file(file_data, metadata, data_type)
            
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
            
            return True
        else:
            print("✗ No file data found in JSON payload")
            print("\nTip: Make sure the JSON file contains data from IDS TOE response")
            return False
    
    def run_cli(self, args=None):
        """
        Run the extractor with command line interface
        
        Args:
            args: Optional list of arguments (defaults to sys.argv)
        """
        if args is None:
            args = sys.argv
        
        if len(args) < 2:
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
        
        self.json_file_path = args[1]
        self.output_path = args[2] if len(args) > 2 else None
        
        # Process the file
        success = self.process()
        
        if not success:
            sys.exit(1)


def main():
    """Main entry point - creates instance and runs it"""
    # Create an instance of file_extractor
    extractor = file_extractor()
    
    # Run with CLI arguments
    extractor.run_cli()


if __name__ == "__main__":
    main()