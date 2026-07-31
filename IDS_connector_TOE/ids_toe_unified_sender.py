#!/usr/bin/env python3
"""
Unified script to POST various file types to IDS TOE Provider
Supports: .zip, .ipynb, .py, .json files
Usage: python3 ids_toe_unified_sender.py <file_path>
"""
import requests
import json
import urllib3
import base64
import os
import sys
import ast
from datetime import datetime

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
IDS_TOE_BASE_URL = os.environ.get("IDS_TOE_BASE_URL", "http://localhost:30005")
IDS_TOE_URL = f"{IDS_TOE_BASE_URL}/api/IDSconnector/post_data"
IDS_TOE_ID_URL = f"{IDS_TOE_BASE_URL}/api/IDSconnector/TOE/id"

def get_toe_id():
    """Fetch the active TOE ID from IDS-TOE before sending data."""
    try:
        response = requests.get(IDS_TOE_ID_URL, headers={"Accept": "application/json"}, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not fetch TOE ID from IDS-TOE: {e}")
        print(f"Make sure IDS-TOE is reachable at {IDS_TOE_ID_URL}")
        sys.exit(1)
    except ValueError:
        print("Error: IDS-TOE returned a non-JSON response for TOE ID")
        sys.exit(1)

    toe_id = data.get("toe_id")
    if not toe_id:
        print("Error: IDS-TOE has no TOE ID set. CCM Manager must post the TOE ID first.")
        sys.exit(1)

    return toe_id

def analyze_python_file(content):
    """Analyze Python file content and extract metadata"""
    metadata = {}
    try:
        tree = ast.parse(content)
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        
        metadata["functions_count"] = len(functions)
        metadata["classes_count"] = len(classes)
        metadata["imports_count"] = len(imports)
        metadata["lines_of_code"] = len(content.splitlines())
        
        if functions:
            metadata["function_names"] = [f.name for f in functions[:10]]
        if classes:
            metadata["class_names"] = [c.name for c in classes[:10]]
        
        metadata["has_main_block"] = "if __name__ == '__main__':" in content or 'if __name__ == "__main__":' in content
        metadata["syntax_valid"] = True
    except SyntaxError:
        metadata["syntax_valid"] = False
    except Exception:
        pass
    return metadata

def analyze_notebook_file(content):
    """Analyze Jupyter notebook content and extract metadata"""
    metadata = {}
    if "metadata" in content:
        nb_meta = content["metadata"]
        if "kernelspec" in nb_meta:
            metadata["kernel"] = nb_meta["kernelspec"].get("display_name", "Unknown")
        if "language_info" in nb_meta:
            metadata["language"] = nb_meta["language_info"].get("name", "Unknown")
            metadata["language_version"] = nb_meta["language_info"].get("version", "Unknown")
    
    metadata["total_cells"] = len(content.get("cells", []))
    metadata["code_cells"] = sum(1 for cell in content.get("cells", []) if cell.get("cell_type") == "code")
    metadata["markdown_cells"] = sum(1 for cell in content.get("cells", []) if cell.get("cell_type") == "markdown")
    return metadata

def process_file(file_path, toe_id):
    """Process file based on its type"""
    file_ext = os.path.splitext(file_path)[1].lower()
    file_size = os.path.getsize(file_path)
    iso_timestamp = datetime.now().isoformat() + "Z"
    
    base_metadata = {
        "filename": os.path.basename(file_path),
        "size_bytes": file_size,
        "upload_timestamp": iso_timestamp
    }
    
    if file_ext == '.zip':
        # Process ZIP file
        with open(file_path, 'rb') as f:
            zip_data = f.read()
            zip_base64 = base64.b64encode(zip_data).decode('utf-8')
        
        metadata = {
            **base_metadata,
            "encoding": "base64",
            "mime_type": "application/zip"
        }
        
        payload_content = {
            "toe_id": toe_id,
            "type": "zip_file",
            "metadata": metadata,
            "data": zip_base64
        }
        
        resource_type = "zip"
        
    elif file_ext == '.ipynb':
        # Process Jupyter notebook
        with open(file_path, 'r', encoding='utf-8') as f:
            notebook_content = json.load(f)
        
        notebook_json = json.dumps(notebook_content, indent=2)
        notebook_base64 = base64.b64encode(notebook_json.encode('utf-8')).decode('utf-8')
        
        notebook_meta = analyze_notebook_file(notebook_content)
        metadata = {
            **base_metadata,
            "encoding": "base64",
            "mime_type": "application/x-ipynb+json",
            **notebook_meta
        }
        
        payload_content = {
            "toe_id": toe_id,
            "type": "jupyter_notebook",
            "metadata": metadata,
            "content": notebook_base64
        }
        
        resource_type = "notebook"
        
    elif file_ext == '.py':
        # Process Python file
        with open(file_path, 'r', encoding='utf-8') as f:
            python_content = f.read()
        
        python_base64 = base64.b64encode(python_content.encode('utf-8')).decode('utf-8')
        
        python_meta = analyze_python_file(python_content)
        metadata = {
            **base_metadata,
            "encoding": "base64",
            "mime_type": "text/x-python",
            **python_meta
        }
        
        payload_content = {
            "toe_id": toe_id,
            "type": "python_script",
            "metadata": metadata,
            "content": python_base64
        }
        
        resource_type = "python"
        
    elif file_ext == '.json':
        # Process JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            json_content = f.read()
        
        # Validate it's parseable JSON
        json_data = json.loads(json_content)
        json_base64 = base64.b64encode(json_content.encode('utf-8')).decode('utf-8')
        
        metadata = {
            **base_metadata,
            "encoding": "base64",
            "mime_type": "application/json",
            "json_keys_count": len(json_data) if isinstance(json_data, dict) else "N/A (array)",
            "json_size_chars": len(json_content)
        }
        
        payload_content = {
            "toe_id": toe_id,
            "type": "json_file",
            "metadata": metadata,
            "content": json_base64
        }
        
        resource_type = "json"
        
    else:
        print(f"Error: Unsupported file type: {file_ext}")
        print("Supported types: .zip, .ipynb, .py")
        sys.exit(1)
    
    return payload_content, resource_type, iso_timestamp, metadata

def build_ids_resource(payload_content, resource_type, iso_timestamp):
    """Build IDS TextResource structure"""
    text_resource = f"{resource_type}-resource-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    json_payload_as_text = json.dumps(payload_content)
    
    return {
        "@context": {
            "ids": "https://w3id.org/idsa/core/",
            "idsc": "https://w3id.org/idsa/code/"
        },
        "@type": "ids:TextResource",
        "@id": f"https://w3id.org/idsa/autogen/textResource/{text_resource}",
        "ids:language": [
            {
                "@id": "https://w3id.org/idsa/code/EN"
            }
        ],
        "ids:version": "1.0.0",
        "ids:keyword": [
            {
                "@value": f"{resource_type.upper()} File Upload - Engineering Ingegneria Informatica SpA TEST",
                "@type": "http://www.w3.org/2001/XMLSchema#string"
            }
        ],
        "ids:contentType": {
            "@id": "https://w3id.org/idsa/code/SCHEMA_DEFINITION"
        },
        "ids:description": [
            {
                "@value": json_payload_as_text,
                "@type": "http://www.w3.org/2001/XMLSchema#string"
            }
        ],
        "ids:created": {
            "@value": iso_timestamp,
            "@type": "http://www.w3.org/2001/XMLSchema#dateTimeStamp"
        },
        "ids:theme": [],
        "ids:contractOffer": [
            {
                "@type": "ids:ContractOffer",
                "@id": f"https://w3id.org/idsa/autogen/contractOffer/{text_resource}",
                "ids:permission": [
                    {
                        "@type": "ids:Permission",
                        "@id": f"https://w3id.org/idsa/autogen/permission/{text_resource}",
                        "ids:target": {
                            "@id": f"http://w3id.org/engrd/connector/artifact/{resource_type}"
                        },
                        "ids:description": [
                            {
                                "@value": "provide-access",
                                "@type": "http://www.w3.org/2001/XMLSchema#string"
                            }
                        ],
                        "ids:constraint": [
                            {
                                "@type": "ids:Constraint",
                                "@id": f"https://w3id.org/idsa/autogen/constraint/{text_resource}",
                                "ids:operator": {
                                    "@id": "https://w3id.org/idsa/code/AFTER"
                                },
                                "ids:leftOperand": {
                                    "@id": "https://w3id.org/idsa/code/POLICY_EVALUATION_TIME"
                                },
                                "ids:rightOperand": {
                                    "@value": iso_timestamp,
                                    "@type": "http://www.w3.org/2001/XMLSchema#dateTimeStamp"
                                }
                            }
                        ],
                        "ids:action": [
                            {
                                "@id": "https://w3id.org/idsa/code/USE"
                            }
                        ],
                        "ids:title": [
                            {
                                "@value": f"{resource_type.title()} File Usage Policy",
                                "@type": "http://www.w3.org/2001/XMLSchema#string"
                            }
                        ]
                    }
                ],
                "ids:provider": {
                    "@id": "https://w3id.org/engrd/connector/"
                },
                "ids:contractStart": {
                    "@value": iso_timestamp,
                    "@type": "http://www.w3.org/2001/XMLSchema#dateTimeStamp"
                },
                "ids:contractDate": {
                    "@value": iso_timestamp,
                    "@type": "http://www.w3.org/2001/XMLSchema#dateTimeStamp"
                }
            }
        ],
        "ids:representation": [
            {
                "@type": "ids:TextRepresentation",
                "@id": text_resource,
                "ids:instance": [
                    {
                        "@type": "ids:Artifact",
                        "@id": f"http://w3id.org/engrd/connector/artifact/{resource_type}",
                        "ids:creationDate": {
                            "@value": iso_timestamp,
                            "@type": "http://www.w3.org/2001/XMLSchema#dateTimeStamp"
                        }
                    }
                ],
                "ids:language": {
                    "@id": "https://w3id.org/idsa/code/EN"
                },
                "ids:created": {
                    "@value": iso_timestamp,
                    "@type": "http://www.w3.org/2001/XMLSchema#dateTimeStamp"
                }
            }
        ],
        "ids:title": [
            {
                "@value": f"{resource_type.title()} File: {payload_content['metadata']['filename']}",
                "@type": "http://www.w3.org/2001/XMLSchema#string"
            }
        ],
        "ids:modified": {
            "@value": iso_timestamp,
            "@type": "http://www.w3.org/2001/XMLSchema#dateTimeStamp"
        }
    }, text_resource

def main():
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python ids_toe_unified_sender.py <file_path>")
        print("\nSupported file types:")
        print("  - .zip  : ZIP archives (sent as base64)")
        print("  - .ipynb: Jupyter notebooks (sent as JSON)")
        print("  - .py   : Python scripts (sent as text)")
        print("  - .json : JSON data files (sent as base64)")
        print("\nExample:")
        print("  python ids_toe_unified_sender.py myfile.zip")
        print("  python ids_toe_unified_sender.py notebook.ipynb")
        print("  python ids_toe_unified_sender.py script.py")
        print("  python ids_toe_unified_sender.py data.json")
        print("  IDS_TOE_BASE_URL=http://ai-target-of-evaluation.cobalt.local:30005 python ids_toe_unified_sender.py data.json")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
    
    print(f"Processing file: {file_path}")

    toe_id = get_toe_id()
    print(f"Using TOE ID from IDS-TOE: {toe_id}")
    
    # Process file based on type
    payload_content, resource_type, iso_timestamp, metadata = process_file(file_path, toe_id)
    
    # Build IDS resource
    ids_resource, text_resource = build_ids_resource(payload_content, resource_type, iso_timestamp)
    
    # Build final payload
    ids_data_as_string = json.dumps(ids_resource)
    payload = {
        "data_type": "json",
        "toe_id": toe_id,
        "data": ids_data_as_string
    }
    
    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Print information
    print("=" * 70)
    print(f"POST Request to IDS TOE Provider - {resource_type.title()} File Upload")
    print("=" * 70)
    print(f"URL: {IDS_TOE_URL}")
    print(f"Resource ID: {text_resource}")
    print(f"TOE ID: {toe_id}")
    print(f"Timestamp: {iso_timestamp}")
    print(f"File: {file_path}")
    print(f"  - Type: {resource_type}")
    print(f"  - Size: {metadata['size_bytes']} bytes")
    
    # Print type-specific metadata
    for key, value in metadata.items():
        if key not in ['filename', 'size_bytes', 'upload_timestamp', 'encoding', 'mime_type']:
            if not (isinstance(value, list) and len(value) > 3):  # Don't print long lists
                print(f"  - {key.replace('_', ' ').title()}: {value}")
    
    print(f"\nPayload size: ~{len(json.dumps(payload))/1024:.2f} KB")
    print("\nSending request...")
    print("=" * 70)
    
    try:
        # Make the POST request
        response = requests.post(
            IDS_TOE_URL,
            headers=headers,
            json=payload,
            verify=False,
            timeout=30
        )
        
        print(f"\nResponse Status Code: {response.status_code}")
        print("-" * 70)
        
        if response.status_code == 200:
            print(f"✓ SUCCESS! {resource_type.title()} file posted to IDS TOE successfully")
            print("\nResponse body:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"✗ FAILED! Error posting {resource_type} file to IDS TOE")
            print("\nResponse body:")
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text)
        
        print("=" * 70)
        
    except requests.exceptions.ConnectionError as e:
        print(f"\n✗ Connection Error: {e}")
        print("Make sure IDS TOE is running at", IDS_TOE_URL)
    except requests.exceptions.Timeout as e:
        print(f"\n✗ Timeout Error: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
    
    print("\nTest completed.")

if __name__ == "__main__":
    main()