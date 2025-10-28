#!/usr/bin/env python3
"""
Create a sample ZIP file for testing the IDS TOE upload
"""
import zipfile
import json
from datetime import datetime

# Create sample data files
sample_data = {
    "test_data.json": {
        "id": "cloud-storage",
        "timestamp": datetime.now().isoformat() + "Z",
        "cloudServiceId": "00000000-0000-0000-0000-000000000000",
        "toolId": "Clouditor Evidences Collection",
        "resource": {
            "@type": "type.googleapis.com/clouditor.ontology.v1.ObjectStorage",
            "creationTime": "2023-07-09T10:35:18.246911100Z",
            "id": "/subscriptions/11111111-1111-1111-1111-111111111111/resourcegroups/demo",
            "name": "test-storage",
            "publicAccess": False,
            "creator": "Allen Abishek"
        }
    },
    "metadata.txt": "Sample metadata file for testing ZIP upload to IDS TOE\nCreated: " + datetime.now().isoformat(),
    "config.ini": """[DEFAULT]
server = localhost
port = 8005
protocol = http
timeout = 30

[IDS]
provider = https://w3id.org/engrd/connector/
language = EN
version = 1.0.0
"""
}

# Create ZIP file
zip_filename = "test_data.zip"
print(f"Creating sample ZIP file: {zip_filename}")

with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for filename, content in sample_data.items():
        print(f"  Adding: {filename}")
        if filename.endswith('.json'):
            content_str = json.dumps(content, indent=2)
        else:
            content_str = content
        zipf.writestr(filename, content_str)

print(f"\n✓ Sample ZIP file created: {zip_filename}")
print(f"  You can now test the upload with: python ids_toe_zip_sender.py {zip_filename}")