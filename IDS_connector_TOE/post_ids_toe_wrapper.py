#!/usr/bin/env python3
"""
Test script to POST data to IDS TOE Provider
"""
import requests
import json
import urllib3
from datetime import datetime

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
IDS_TOE_URL = "http://localhost:8005/api/IDSconnector/post_data"  # Change to your IDS TOE URL
# For pod access: "http://ids-connector-toe-service:8005/api/IDSconnector/post_data"

# Generate timestamp
iso_timestamp = datetime.now().isoformat() + "Z"

# Generate unique resource ID
text_resource = f"test-resource-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

# JSON payload (the actual data you want to send)
json_payload_as_text = '''{
  "id":  "cloud-storage",
  "timestamp":  "2024-09-17T09:17:42.128171Z",
  "cloudServiceId":  "00000000-0000-0000-0000-000000000000",
  "toolId":  "Clouditor Evidences Collection",
  "raw":  "{\\"*armstorage.Account\\":[{\\"id\\":\\"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/DemoClouditorHappy/providers/Microsoft.Storage/storageAccounts/democlouditordiagnostics\\"}]}",
  "resource":  {
    "@type":  "type.googleapis.com/clouditor.ontology.v1.ObjectStorage",
    "creationTime":  "2023-07-09T10:35:18.246911100Z",
    "id":  "/subscriptions/11111111-1111-1111-1111-111111111111/resourcegroups/democlouditorhappy/providers/microsoft.storage/storageaccounts/democlouditordiagnostics/blobservices/default/containers/bootdiagnostics-happyvm-11111111-1111-1111-1111-111111111111",
    "name":  "bootdiagnostics-happyvm-11111111-1111-1111-1111-111111111111",
    "publicAccess":  false
  }
}'''

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
            "@value": "Engineering Ingegneria Informatica SpA TEST",
            "@type": "http://www.w3.org/2001/XMLSchema#string"
        }
    ],
    "ids:contentType": {
        "@id": "https://w3id.org/idsa/code/SCHEMA_DEFINITION"
    },
    "ids:description": [
        {
            "@value": json_payload_as_text,  # JSON stored as a string
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
                        "@id": "http://w3id.org/engrd/connector/artifact/postman"
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
                            "@value": "Example Usage Policy POSTMAN",
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
                    "@id": "http://w3id.org/engrd/connector/artifact/postman",
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
            "@value": "World class literature",
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
print("POST Request to IDS TOE Provider")
print("=" * 70)
print(f"URL: {IDS_TOE_URL}")
print(f"Resource ID: {text_resource}")
print(f"Timestamp: {iso_timestamp}")
print("\nPayload structure:")
print(f"  - data_type: {payload['data_type']}")
print(f"  - data length: {len(payload['data'])} characters")
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
        print("✓ SUCCESS! Data posted to IDS TOE successfully")
        print("\nResponse body:")
        print(json.dumps(response.json(), indent=2))
    else:
        print("✗ FAILED! Error posting data to IDS TOE")
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