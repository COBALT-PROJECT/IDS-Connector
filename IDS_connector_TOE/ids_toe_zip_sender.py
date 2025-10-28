#!/usr/bin/env python3
"""
Test script to POST ZIP file data to IDS TOE Provider
"""
import requests
import json
import urllib3
import base64
import os
import sys
from datetime import datetime

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
IDS_TOE_URL = "http://localhost:8005/api/IDSconnector/post_data"  # Change to your IDS TOE URL
# For pod access: "http://ids-connector-toe-service:8005/api/IDSconnector/post_data"

# ZIP file path - change this to your ZIP file
ZIP_FILE_PATH = "data.zip"  # Default ZIP file name

# Check if ZIP file path is provided as command line argument
if len(sys.argv) > 1:
    ZIP_FILE_PATH = sys.argv[1]

# Check if ZIP file exists
if not os.path.exists(ZIP_FILE_PATH):
    print(f"Error: ZIP file not found at {ZIP_FILE_PATH}")
    print(f"Usage: {sys.argv[0]} [path_to_zip_file]")
    sys.exit(1)

# Read and encode ZIP file
print(f"Reading ZIP file: {ZIP_FILE_PATH}")
with open(ZIP_FILE_PATH, 'rb') as zip_file:
    zip_data = zip_file.read()
    zip_base64 = base64.b64encode(zip_data).decode('utf-8')

print(f"ZIP file size: {len(zip_data)} bytes")
print(f"Base64 encoded size: {len(zip_base64)} characters")

# Generate timestamp
iso_timestamp = datetime.now().isoformat() + "Z"

# Generate unique resource ID
text_resource = f"zip-resource-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

# Create metadata about the ZIP file
zip_metadata = {
    "filename": os.path.basename(ZIP_FILE_PATH),
    "size_bytes": len(zip_data),
    "encoding": "base64",
    "mime_type": "application/zip",
    "upload_timestamp": iso_timestamp
}

# JSON payload containing the ZIP data and metadata
json_payload = {
    "type": "zip_file",
    "metadata": zip_metadata,
    "data": zip_base64  # Base64 encoded ZIP file
}

# Convert to JSON string for the description field
json_payload_as_text = json.dumps(json_payload)

# Build the IDS TextResource data structure
ids_text_resource_data = {
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
            "@value": "ZIP File Upload - Engineering Ingegneria Informatica SpA TEST",
            "@type": "http://www.w3.org/2001/XMLSchema#string"
        }
    ],
    "ids:contentType": {
        "@id": "https://w3id.org/idsa/code/SCHEMA_DEFINITION"
    },
    "ids:description": [
        {
            "@value": json_payload_as_text,  # JSON with base64 ZIP stored as a string
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
                        "@id": "http://w3id.org/engrd/connector/artifact/zip"
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
                            "@value": "ZIP File Usage Policy",
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
                    "@id": "http://w3id.org/engrd/connector/artifact/zip",
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
            "@value": f"ZIP File: {os.path.basename(ZIP_FILE_PATH)}",
            "@type": "http://www.w3.org/2001/XMLSchema#string"
        }
    ],
    "ids:modified": {
        "@value": iso_timestamp,
        "@type": "http://www.w3.org/2001/XMLSchema#dateTimeStamp"
    }
}

# Convert the IDS TextResource to JSON string (this is what goes in the "data" field)
ids_data_as_string = json.dumps(ids_text_resource_data)

# Build the payload for IDS TOE (matching the OpenAPI spec)
payload = {
    "data_type": "json",
    "data": ids_data_as_string  # The entire IDS TextResource as a string
}

# Headers
headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

print("=" * 70)
print("POST Request to IDS TOE Provider - ZIP File Upload")
print("=" * 70)
print(f"URL: {IDS_TOE_URL}")
print(f"Resource ID: {text_resource}")
print(f"Timestamp: {iso_timestamp}")
print(f"ZIP File: {ZIP_FILE_PATH}")
print(f"  - Original size: {len(zip_data)} bytes")
print(f"  - Base64 size: {len(zip_base64)} characters")
print("\nPayload structure:")
print(f"  - data_type: {payload['data_type']}")
print(f"  - data length: {len(payload['data'])} characters")
print(f"  - Total payload size: ~{len(json.dumps(payload))/1024:.2f} KB")
print("\nSending request...")
print("=" * 70)

try:
    # Make the POST request to IDS TOE
    response = requests.post(
        IDS_TOE_URL,
        headers=headers,
        json=payload,  # Use json parameter to automatically serialize
        verify=False,  # Disable SSL verification if needed
        timeout=30
    )
    
    print(f"\nResponse Status Code: {response.status_code}")
    print("-" * 70)
    
    if response.status_code == 200:
        print("✓ SUCCESS! ZIP file posted to IDS TOE successfully")
        print("\nResponse body:")
        print(json.dumps(response.json(), indent=2))
    else:
        print("✗ FAILED! Error posting ZIP file to IDS TOE")
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