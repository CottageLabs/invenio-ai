#!/usr/bin/env python3
"""Test what the live app sees."""
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Test if server is up
try:
    response = requests.get("https://127.0.0.1:5000/api/records", verify=False, timeout=5)
    print(f"Server is up: {response.status_code}")
except Exception as e:
    print(f"Server connection failed: {e}")
    exit(1)

# Test our endpoint
response = requests.get("https://127.0.0.1:5000/api/aisearch/status", verify=False)
print(f"\n/api/aisearch/status: {response.status_code}")
print(f"Response: {response.json()}")

# Try other paths
for path in ["/api/aisearch", "/api/aisearch/", "/aisearch/status"]:
    response = requests.get(f"https://127.0.0.1:5000{path}", verify=False)
    print(f"\n{path}: {response.status_code}")
    if response.status_code != 404:
        print(f"  Response: {response.text[:200]}")
