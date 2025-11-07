# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an InvenioRDM v13 instance named "v13-ai", a research data management repository platform built on the Invenio framework. InvenioRDM is a turn-key research data management repository based on the Invenio Framework, developed at CERN.

**Key details:**
- Project: v13-ai
- Package: v13_ai
- Python version: 3.12
- Database: PostgreSQL
- Search: OpenSearch 2
- Framework: InvenioRDM ~=13.0.0
- Site URL: https://127.0.0.1 (dev), https://invenio-ai.cottagelabs.com (production)

## Development Commands

### Starting the Application

**Full containerized environment (recommended for first-time setup):**
```bash
invenio-cli containers start --lock --build --setup
```

This builds Docker images, starts all services (PostgreSQL, OpenSearch, Redis, RabbitMQ), and sets up the application. Access at https://127.0.0.1

**Container management:**
```bash
invenio-cli containers build      # Build application Docker image
invenio-cli containers start      # Start containers
invenio-cli containers stop       # Stop containers
invenio-cli containers status     # Check container status
invenio-cli containers destroy    # Remove all containers
```

**Local services (for local development without containerized app):**
```bash
invenio-cli services start        # Start backend services (DB, search, cache, MQ)
invenio-cli services stop         # Stop services
invenio-cli services status       # Check services status
invenio-cli services setup        # Setup/initialize services
invenio-cli services destroy      # Remove services
```

**Local development servers:**
```bash
invenio-cli run all              # Start both web and worker servers
invenio-cli run web              # Start web server only
invenio-cli run worker           # Start Celery worker only
```

### Assets and Frontend

**Build assets:**
```bash
invenio-cli assets build         # Build static and asset files locally
invenio-cli assets watch         # Watch and rebuild on changes
```

**React module development:**
```bash
invenio-cli assets install       # Install and link a React module
invenio-cli assets watch-module  # Watch a specific React module
```

**Note:** For containerized environments, rebuild the container instead: `invenio-cli containers build`

### Python and Dependencies

**Install dependencies:**
```bash
pipenv install                   # Install from Pipfile.lock
pipenv install --dev             # Include dev dependencies
```

**Access Python shell:**
```bash
invenio-cli pyshell              # Python shell with app context
invenio-cli shell                # Regular shell in container
```

### Testing

The project uses pytest with pytest-invenio. Tests are located in `site/tests/`.

```bash
# Run tests (configure based on your test setup)
pipenv run pytest site/tests/
```

## Architecture

### Directory Structure

- **`site/v13_ai/`** - Custom Python package for instance-specific code
  - `views.py` - Flask blueprints for custom routes/views
  - `webpack.py` - Webpack bundle configuration for custom JS/CSS
  - `templates/` - Jinja2 templates extending/overriding InvenioRDM defaults
  - `assets/` - Custom frontend assets (JS, LESS/CSS)

- **`invenio.cfg`** - Main application configuration (Flask, Invenio, security, theming)

- **`assets/`** - Frontend assets (copied to instance during build)
  - `js/` - JavaScript/React customizations
  - `less/` - LESS stylesheets (Semantic UI theme)
  - `templates/` - React component templates

- **`templates/`** - Jinja2 templates (copied to instance)

- **`static/`** - Static files served as-is (images, etc.)

- **`app_data/`** - Application data
  - `vocabularies.yaml` - Vocabulary configuration
  - `vocabularies/` - Custom controlled vocabularies
  - `pages/` - Static pages content

- **`translations/`** - i18n translation files

- **`docker/`** - Container configuration
  - `nginx/` - NGINX reverse proxy config
  - `uwsgi/` - uWSGI application server config

- **`.invenio`** - Invenio-CLI configuration (version controlled)
- **`.invenio.private`** - Private config (NOT version controlled)

### Configuration System

InvenioRDM uses a layered configuration approach:

1. **Base Invenio defaults** - From installed packages
2. **`invenio.cfg`** - Instance-level overrides (main config file)
3. **Environment variables** - Runtime overrides

Key configuration areas in `invenio.cfg`:
- Flask settings (SECRET_KEY, TRUSTED_HOSTS)
- Database (SQLALCHEMY_DATABASE_URI)
- Search (SEARCH_INDEX_PREFIX)
- Security headers (APP_DEFAULT_SECURE_HEADERS)
- Theming (THEME_SITENAME, THEME_LOGO, INSTANCE_THEME_FILE)
- Authentication (ACCOUNTS_*, SECURITY_*, OAUTHCLIENT_*)
- Deposit form defaults (APP_RDM_DEPOSIT_FORM_DEFAULTS)
- DOI registration (DATACITE_*)
- OAI-PMH (OAISERVER_*)

**Important:** Never commit SECRET_KEY or database credentials. Use environment variables or `.invenio.private` for sensitive values.

### Extension Points

InvenioRDM is highly extensible through Python entry points defined in `site/setup.cfg`:

```python
[options.entry_points]
invenio_base.blueprints =
    v13_ai_views = v13_ai.views:create_blueprint
invenio_assets.webpack =
    v13_ai_theme = v13_ai.webpack:theme
```

Common customization patterns:
- **Views/Routes:** Add Flask blueprints in `v13_ai/views.py`
- **Templates:** Override by placing templates in matching paths under `templates/`
- **Assets:** Add webpack entries in `v13_ai/webpack.py`, source files in `v13_ai/assets/`
- **Theming:** Customize LESS variables in `assets/less/site/globals/`
- **Vocabularies:** Define in `app_data/vocabularies.yaml` and populate from YAML/CSV files

### Build Process

The Dockerfile shows the build flow:
1. Copy Python package and install dependencies via pipenv
2. Copy configuration, templates, app_data, translations
3. Copy static assets to instance path
4. Run `invenio collect` to gather static files
5. Run `invenio webpack buildall` to build frontend bundles

For local development, assets can be built incrementally with `invenio-cli assets build/watch`.

### Service Architecture

InvenioRDM runs on a microservices-style architecture with:
- **PostgreSQL** - Primary database (port 5432)
- **OpenSearch 2** - Search and indexing (ports 9200, 9600)
- **Redis** - Caching and session storage (port 6379)
- **RabbitMQ** - Message queue for async tasks (ports 5672, 15672)
- **Celery** - Background task processing
- **uWSGI** - WSGI application server
- **NGINX** - Reverse proxy and static file serving

Development tools:
- **OpenSearch Dashboards** - Search index viewer (port 5601)
- **pgAdmin** - Database management UI

All services are defined in `docker-compose.yml` and `docker-services.yml`.

## Common Workflows

### Adding a Custom Page/View

1. Add route in `site/v13_ai/views.py` to the blueprint
2. Create template in `site/v13_ai/templates/semantic-ui/v13_ai/`
3. Rebuild: `invenio-cli containers build` or restart dev server

### Customizing Styles

1. Edit LESS files in `assets/less/site/globals/site.variables` or `site.overrides`
2. Rebuild assets: `invenio-cli assets build` or `invenio-cli containers build`

### Adding Custom JavaScript

1. Add entry in `site/v13_ai/webpack.py` theme config
2. Create JS files in `site/v13_ai/assets/semantic-ui/js/v13_ai/`
3. Rebuild assets

### Working with Vocabularies

1. Define vocabulary in `app_data/vocabularies.yaml`
2. Add data files (YAML/CSV) in `app_data/vocabularies/`
3. Load with: `invenio vocabularies import --vocabulary <name>`

### Configuration Changes

After modifying `invenio.cfg`, restart the application:
- **Containers:** `invenio-cli containers stop && invenio-cli containers start`
- **Local dev:** Restart `invenio-cli run` commands

## Important Notes

- The application uses **self-signed SSL certificates** in development - browsers will show security warnings
- Database connection string format: `postgresql+psycopg2://user:password@host/database`
- The `SECRET_KEY` in `invenio.cfg` must be changed before production deployment
- Search index prefix is `v13-ai-` to avoid conflicts with other instances
- Email confirmation is required before login by default (SECURITY_LOGIN_WITHOUT_CONFIRMATION = False)
