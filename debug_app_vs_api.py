#!/usr/bin/env python3
"""Check difference between create_app and create_api."""

from invenio_app.factory import create_app, create_api

print("=" * 80)
print("CHECKING create_app():")
print("=" * 80)
app = create_app()
print(f"Has aisearch blueprint: {'invenio_aisearch_api' in app.blueprints}")
if 'invenio_aisearch_api' in app.blueprints:
    print("Routes:")
    for rule in app.url_map.iter_rules():
        if 'aisearch' in str(rule):
            print(f"  {rule.rule} -> {rule.endpoint}")

print("\n" + "=" * 80)
print("CHECKING create_api():")
print("=" * 80)
api = create_api()
print(f"Has aisearch blueprint: {'invenio_aisearch_api' in api.blueprints}")
if 'invenio_aisearch_api' in api.blueprints:
    print("Routes:")
    for rule in api.url_map.iter_rules():
        if 'aisearch' in str(rule):
            print(f"  {rule.rule} -> {rule.endpoint}")

print("\n" + "=" * 80)
print("ENTRY POINTS:")
print("=" * 80)
import pkg_resources
print("api_apps:")
for ep in pkg_resources.iter_entry_points('invenio_base.api_apps'):
    if 'aisearch' in ep.name:
        print(f"  {ep.name} = {ep}")

print("\napi_blueprints:")
for ep in pkg_resources.iter_entry_points('invenio_base.api_blueprints'):
    if 'aisearch' in ep.name:
        print(f"  {ep.name} = {ep}")
