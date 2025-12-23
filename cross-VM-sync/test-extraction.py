#!/usr/bin/env python3
import requests
from requests.auth import HTTPBasicAuth
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://10.10.2.20:30578/api/selfDescription/"

response = requests.get(
    url,
    auth=HTTPBasicAuth("admin", "password"),
    headers={"Accept":  "application/json"},
    verify=False
)

catalog_data = response.json()

print("=" * 70)
print("CATALOG DATA ANALYSIS")
print("=" * 70)

# Check what keys exist
print("\n1. Top-level keys:")
for key in catalog_data. keys():
    print(f"   - {key}")

# Try to get resource catalog
print("\n2. Extracting resource catalog:")
catalogs = catalog_data.get('ids:resourceCatalog', [])
print(f"   Found {len(catalogs)} catalog(s)")

if not catalogs:
    print("   ❌ No catalogs found!  Check if key name is correct.")
    print(f"   Available keys: {list(catalog_data.keys())}")
else:
    print(f"   ✅ Catalogs found!")
    
    for i, catalog in enumerate(catalogs):
        print(f"\n3. Catalog {i} details:")
        print(f"   Type: {catalog.get('@type')}")
        print(f"   ID: {catalog.get('@id')}")
        
        offered_resources = catalog.get('ids:offeredResource', [])
        print(f"   Offered resources: {len(offered_resources)}")
        
        if not offered_resources:
            print("   ❌ No offered resources found!")
            print(f"   Catalog keys: {list(catalog.keys())}")
        else:
            print(f"   ✅ Found {len(offered_resources)} resources")
            
            for j, resource in enumerate(offered_resources):
                print(f"\n   Resource {j + 1}:")
                print(f"      @id: {resource.get('@id')}")
                print(f"      @type: {resource.get('@type')}")
                title = resource.get('ids:title', [{}])[0].get('@value', 'No title')
                print(f"      title: {title}")
                
                # Check if it matches our filter
                if resource.get('@type') == 'ids:TextResource':
                    print(f"      ✅ Matches filter (TextResource)")
                else: 
                    print(f"      ❌ Does NOT match filter")

print("\n" + "=" * 70)
print("EXTRACTION TEST COMPLETE")
print("=" * 70)