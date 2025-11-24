import requests
import json
from datetime import datetime
import urllib3

# Disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Ask the user to input a value for the text resource
text_resource = input("Please enter the text resource identifier (e.g., 'dummyPOST'): ")

# JSON object to store as text value
json_payload_as_text = '''
{
    "services": [
        {
            "service_id": {
                "context_id": {
                    "context_uuid": {
                        "uuid": "admin"
                        }
                    },
                "service_uuid": {
                    "uuid": "dc-2-dc-svc"
                }
            },
            "service_type": 2,
            "service_status": {"service_status": 1},
            "service_endpoint_ids": [
                {"device_id":{"device_uuid":{"uuid":"DC1"}},"endpoint_uuid":{"uuid":"int"}},
                {"device_id":{"device_uuid":{"uuid":"DC2"}},"endpoint_uuid":{"uuid":"int"}}
            ],
            "service_constraints": [
                {"sla_capacity": {"capacity_gbps": 10.0}},
                {"sla_latency": {"e2e_latency_ms": 15.2}}
            ],
            "service_config": {"config_rules": [
                {"action": 1, "custom": {"resource_key": "/settings", "resource_value": {
                    "address_families": ["IPV4"], "bgp_as": 65000, "bgp_route_target": "65000:123",
                    "mtu": 1512, "vlan_id": 300
                }}},
                {"action": 1, "custom": {"resource_key": "/device[PE1]/endpoint[1/1]/settings", "resource_value": {
                    "route_distinguisher": "65000:123", "router_id": "10.0.0.1",
                    "address_ip": "3.3.1.1", "address_prefix": 24, "sub_interface_index": 1, "vlan_id": 300
                }}},
                {"action": 1, "custom": {"resource_key": "/device[PE2]/endpoint[1/1]/settings", "resource_value": {
                    "route_distinguisher": "65000:123", "router_id": "10.0.0.2",
                    "address_ip": "3.3.2.1", "address_prefix": 24, "sub_interface_index": 1, "vlan_id": 300
                }}},
                {"action": 1, "custom": {"resource_key": "/device[PE3]/endpoint[1/1]/settings", "resource_value": {
                    "route_distinguisher": "65000:123", "router_id": "10.0.0.3",
                    "address_ip": "3.3.3.1", "address_prefix": 24, "sub_interface_index": 1, "vlan_id": 300
                }}},
                {"action": 1, "custom": {"resource_key": "/device[PE4]/endpoint[1/1]/settings", "resource_value": {
                    "route_distinguisher": "65000:123", "router_id": "10.0.0.4",
                    "address_ip": "3.3.4.1", "address_prefix": 24, "sub_interface_index": 1, "vlan_id": 300
                }}}
            ]}
        }
    ]
}
'''

# Credentials for Basic Authentication
username = 'apiUser'
password = 'passwordApiUser'

# The IDS TrueConnector API endpoint URL
url = 'https://localhost:8090/api/offeredResource/'

# The catalog value for the header
catalog_value = "https://w3id.org/idsa/autogen/resourceCatalog/bc99f877-e855-4e6a-ab31-67bd38716b8d"

# Get current ISO timestamp without microseconds and append 'Z' for UTC
iso_timestamp = datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

# JSON object to be posted as the resource
data = {
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
            "@value": json_payload_as_text,  # JSON stored as a string in the value
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

# Headers, including the catalog header
headers = {
    'Content-Type': 'application/json',
    'catalog': catalog_value  # Custom header for catalog
}

# Print the request body for debugging
print("Request body:", json.dumps(data, indent=4))

# Make the POST request with basic auth and disable SSL certificate verification
response = requests.put(
    url,
    auth=(username, password),
    headers=headers,
    data=json.dumps(data),
    verify=False  # Disable SSL certificate verification
)

# Check the response status code and print the result
if response.status_code == 200:  # Status code 201 for successful resource creation
    print('Resource successfully created.')
else:
    print(f'Failed to create resource. Status code: {response.status_code}')
    print(f'Response: {response.text}')
