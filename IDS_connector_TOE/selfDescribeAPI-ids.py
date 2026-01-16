import requests
from requests.auth import HTTPBasicAuth

# API endpoint
#note: 8090 -> provider, 8444 -> consumer
#url = "https://10.254.3.188:8444/api/selfDescription/"

# we check the tc-provider from the nodePort
url = "https://localhost:30578/api/selfDescription/"

# Credentials
username = "admin"
password = "password"

# Disable SSL verification warning (since we're using -k equivalent)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Make the GET request with basic auth
response = requests.get(
    url,
    auth=HTTPBasicAuth(username, password),
    headers={"Accept": "application/json"},
    verify=False  # Equivalent to curl -k
)

# Check and print result
if response.status_code == 200:
    print("✅ Self-description retrieved successfully:")
    print(response.json())  # pretty-print with json.dumps(response.json(), indent=2) if needed
else:
    print(f"❌ Failed to retrieve self-description. Status: {response.status_code}")
    print(response.text)
