#!/usr/bin/env python3
"""Quick test to check if API blueprint registers."""
from flask import Flask

app = Flask(__name__)

# Import and register blueprint
from invenio_aisearch.api_views import api_blueprint
app.register_blueprint(api_blueprint)

print("✓ Blueprint registered successfully")
print("\nRegistered routes:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.rule} -> {rule.endpoint}")
