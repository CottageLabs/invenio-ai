#!/usr/bin/env python3
"""Debug blueprint registration in the running app."""

from invenio_app.factory import create_api

app = create_api()

print("=" * 80)
print("ALL REGISTERED BLUEPRINTS:")
print("=" * 80)
for name, blueprint in app.blueprints.items():
    print(f"\nBlueprint: {name}")
    if hasattr(blueprint, 'url_prefix'):
        print(f"  URL prefix: {blueprint.url_prefix}")

print("\n" + "=" * 80)
print("ALL URL RULES:")
print("=" * 80)
for rule in app.url_map.iter_rules():
    if 'aisearch' in str(rule):
        print(f"\n{rule.rule} -> {rule.endpoint}")
        print(f"  Methods: {rule.methods}")

print("\n" + "=" * 80)
print("AISEARCH BLUEPRINT DETAILS:")
print("=" * 80)
if 'invenio_aisearch_api' in app.blueprints:
    bp = app.blueprints['invenio_aisearch_api']
    print(f"Found blueprint: {bp}")
    print(f"URL prefix: {bp.url_prefix}")
    print(f"Deferred functions: {len(bp.deferred_functions)}")
    print("\nRoutes registered:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('invenio_aisearch_api'):
            print(f"  {rule.rule} -> {rule.endpoint}")
else:
    print("Blueprint NOT found in app.blueprints!")

print("\n" + "=" * 80)
print("CHECKING EXTENSION:")
print("=" * 80)
if "invenio-aisearch" in app.extensions:
    ext = app.extensions["invenio-aisearch"]
    print(f"Extension found: {ext}")
    print(f"Extension attributes: {dir(ext)}")
else:
    print("Extension NOT found!")
