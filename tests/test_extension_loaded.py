#!/usr/bin/env python3
"""Check if invenio-aisearch extension is loaded in the running app."""
from invenio_app.factory import create_api

app = create_api()

with app.app_context():
    print("=" * 60)
    print("Extension Check")
    print("=" * 60)

    # Check if extension is in app.extensions
    if "invenio-aisearch" in app.extensions:
        print("✓ Extension 'invenio-aisearch' is loaded")
        print(f"  Extension object: {app.extensions['invenio-aisearch']}")
    else:
        print("✗ Extension 'invenio-aisearch' is NOT loaded")
        print(f"  Available extensions: {list(app.extensions.keys())}")

    print("\n" + "=" * 60)
    print("Blueprint Check")
    print("=" * 60)

    # Check if blueprint is registered (refactored name: ai_search_api)
    if 'ai_search_api' in app.blueprints:
        print("✓ Blueprint 'ai_search_api' is registered")
        bp = app.blueprints['ai_search_api']
        print(f"  Blueprint object: {bp}")
        print(f"  URL prefix: {bp.url_prefix}")
    else:
        print("✗ Blueprint 'ai_search_api' is NOT registered")

    print("\n" + "=" * 60)
    print("URL Rules")
    print("=" * 60)

    # Check URL rules
    aisearch_rules = [rule for rule in app.url_map.iter_rules() if 'aisearch' in str(rule)]
    if aisearch_rules:
        print("✓ Found aisearch URL rules:")
        for rule in aisearch_rules:
            print(f"  {rule} -> {rule.endpoint}")
    else:
        print("✗ No aisearch URL rules found")

    print("\n" + "=" * 60)
    print("Entry Points Check")
    print("=" * 60)

    import pkg_resources

    # Check app entry point
    app_eps = list(pkg_resources.iter_entry_points('invenio_base.apps', 'invenio_aisearch'))
    if app_eps:
        print("✓ Found app entry point:")
        print(f"  {app_eps[0]}")
    else:
        print("✗ App entry point not found")

    # Check API blueprint entry point (refactored name: ai_search_api)
    api_eps = list(pkg_resources.iter_entry_points('invenio_base.api_blueprints', 'ai_search_api'))
    if api_eps:
        print("✓ Found API blueprint entry point:")
        print(f"  {api_eps[0]}")
        try:
            func = api_eps[0].load()
            print(f"  Loaded function: {func}")
        except Exception as e:
            print(f"  ERROR loading: {e}")
    else:
        print("✗ API blueprint entry point not found")
