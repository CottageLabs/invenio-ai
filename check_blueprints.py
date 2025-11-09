#!/usr/bin/env python3
"""Check what blueprints are registered in the InvenioRDM app."""
from invenio_app.factory import create_api

app = create_api()

print("Registered API blueprints:")
for name, blueprint in app.blueprints.items():
    if 'api' in name or 'aisearch' in name:
        print(f"  {name}: {blueprint}")

print("\nAll URL rules containing 'aisearch':")
with app.app_context():
    for rule in app.url_map.iter_rules():
        if 'aisearch' in str(rule):
            print(f"  {rule} -> {rule.endpoint}")

if not any('aisearch' in str(rule) for rule in app.url_map.iter_rules()):
    print("  (none found - aisearch blueprint not registered)")
