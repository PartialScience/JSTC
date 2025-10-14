# Configuration Guide

This document explains how the YAML-based configuration system works in the JSTC API.

## Overview

The configuration system uses a layered approach:

1. **Base Configuration** (`config.yaml`) - Default settings for all environments
2. **Environment-Specific Overrides** (`config.{env}.yaml`) - Settings that override base config
3. **Environment Variables** (`.env`) - Sensitive data and runtime overrides

## Configuration Files

### config.yaml (Base Configuration)

Contains default settings for the application:

```yaml
api:
  title: "JSTC API"
  description: "A FastAPI application with modular structure"
  version: "1.0.0"
  host: "0.0.0.0"
  port: 8000
  debug: true

cors:
  allow_origins: ["*"]
  allow_methods: ["*"]
  allow_headers: ["*"]
  allow_credentials: true

database:
  url: "sqlite:///./sql_app.db"
  echo: false
  pool_size: 5
  max_overflow: 10

pagination:
  default_page_size: 100
  max_page_size: 1000

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: null

security:
  algorithm: "HS256"
  access_token_expire_minutes: 30

features:
  enable_rate_limiting: false
  enable_request_logging: true
  enable_metrics: false
```

### Environment-Specific Configuration Files

- `config.dev.yaml` - Development overrides
- `config.staging.yaml` - Staging environment settings
- `config.prod.yaml` - Production environment settings

These files only need to include settings that differ from the base configuration.

### Environment Variables (.env)

Used only for sensitive data and runtime configuration:

```bash
# Environment determines which config file to use
ENVIRONMENT=development

# Sensitive data (never in YAML files)
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@host/db

# External service credentials
REDIS_URL=redis://localhost:6379/0
```

## Configuration Loading Process

1. Load base configuration from `config.yaml`
2. Determine environment from `ENVIRONMENT` env var (default: "development")
3. Load and merge environment-specific config from `config.{environment}.yaml`
4. Override sensitive settings with environment variables
5. Create typed Pydantic models from merged configuration

## Usage in Code

```python
from app.core.config import get_settings

settings = get_settings()

# Access nested configuration
print(settings.api.title)
print(settings.database.url)
print(settings.cors.allow_origins)
```

## Configuration Sections

### api
- `title`: API title for documentation
- `description`: API description
- `version`: API version
- `host`: Host to bind to
- `port`: Port to listen on
- `debug`: Enable debug mode
- `docs_url`: OpenAPI docs URL
- `redoc_url`: ReDoc documentation URL

### cors
- `allow_origins`: List of allowed origins
- `allow_methods`: List of allowed HTTP methods
- `allow_headers`: List of allowed headers
- `allow_credentials`: Whether to allow credentials

### database
- `url`: Database connection URL
- `echo`: Whether to log SQL statements
- `pool_size`: Connection pool size
- `max_overflow`: Maximum pool overflow

### pagination
- `default_page_size`: Default number of items per page
- `max_page_size`: Maximum allowed page size

### logging
- `level`: Log level (DEBUG, INFO, WARNING, ERROR)
- `format`: Log message format
- `file`: Log file path (null for console only)

### security
- `algorithm`: JWT algorithm
- `access_token_expire_minutes`: Token expiration time

### features
- `enable_rate_limiting`: Enable rate limiting
- `enable_request_logging`: Log all requests
- `enable_metrics`: Enable metrics collection

## Environment-Specific Examples

### Development (config.dev.yaml)
```yaml
api:
  debug: true
  host: "127.0.0.1"

database:
  url: "sqlite:///./dev_app.db"
  echo: true

logging:
  level: "DEBUG"
```

### Production (config.prod.yaml)
```yaml
api:
  debug: false
  host: "0.0.0.0"

cors:
  allow_origins:
    - "https://your-frontend.com"

database:
  pool_size: 20
  max_overflow: 30

logging:
  level: "WARNING"
  file: "/var/log/jstc-api/app.log"

security:
  access_token_expire_minutes: 15

features:
  enable_rate_limiting: true
```

## Best Practices

1. **Never put sensitive data in YAML files** - Use environment variables
2. **Keep environment configs minimal** - Only override what's different
3. **Use version control for YAML configs** - They're safe to commit
4. **Use descriptive names** - Make configuration self-documenting
5. **Validate configuration** - Use Pydantic models for type safety
6. **Document changes** - Update this guide when adding new settings

## Adding New Configuration

1. Add the setting to the appropriate Pydantic model in `config.py`
2. Add the default value to `config.yaml`
3. Add environment-specific overrides as needed
4. Update this documentation
5. Use the setting in your code via `get_settings()`

## Environment Variables Priority

Environment variables take precedence over YAML configuration for:
- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- Other sensitive credentials

This ensures sensitive data is never stored in configuration files.
