# Dynaconf Configuration Patterns

Dynaconf supports multiple configuration file patterns. Here are the two main approaches:

## Approach 1: Single File with Environment Sections

**Structure:**
```
config.yaml  # Contains all environments in one file
```

**config.yaml:**
```yaml
default:
  api:
    title: "My API"
    port: 8000

development:
  api:
    debug: true
    
production:
  api:
    debug: false
```

**Pros:**
- Everything in one place
- Easy to see all environment differences
- Fewer files to manage

**Cons:**
- Can become large with many environments
- All team members see all environment configs

## Approach 2: Separate Files per Environment (Current Setup)

**Structure:**
```
config.yaml              # Base configuration
config.development.yaml  # Development overrides
config.staging.yaml      # Staging overrides
config.production.yaml   # Production overrides
config.local.yaml        # Local overrides (gitignored)
```

**config.yaml (base):**
```yaml
api:
  title: "My API"
  port: 8000
  debug: false
```

**config.development.yaml:**
```yaml
api:
  debug: true
  host: "127.0.0.1"
```

**Pros:**
- Clean separation of concerns
- Environment-specific files can have different permissions
- Easier to manage large configurations
- Can gitignore sensitive environment configs
- Team members only need relevant environment files

**Cons:**
- More files to manage
- Need to look across files to see full config

## Loading Order

With separate files, Dynaconf loads in this order:

1. `config.yaml` (base configuration)
2. `config.{environment}.yaml` (environment-specific)
3. `config.local.yaml` (local overrides, gitignored)
4. Environment variables with `JSTC_` prefix
5. `.env` file variables

Later sources override earlier ones.

## Switching Between Patterns

You can easily switch between patterns by updating the `settings_files` list in `config.py`:

```python
# Pattern 1: Single file
settings_files=["config.yaml"]

# Pattern 2: Separate files (current)
settings_files=[
    "config.yaml",
    "config.development.yaml", 
    "config.staging.yaml",
    "config.production.yaml",
    "config.local.yaml",
]
```

## Environment Selection

Set the environment using:

```bash
# Environment variable
export ENV_FOR_DYNACONF=production

# Or in .env file
ENV_FOR_DYNACONF=production

# Or programmatically
settings.setenv('production')
```

## Best Practices

1. **Use separate files for complex projects** with multiple environments
2. **Use single file for simple projects** with 2-3 environments
3. **Always use config.local.yaml** for developer-specific overrides
4. **Keep sensitive data in environment variables**, never in YAML files
5. **Use descriptive environment names** (development, staging, production, testing)

## Example Usage

```python
from app.core.config import settings

# Access configuration (same regardless of pattern)
print(settings.api.title)
print(settings.current_env)

# Check current environment
if settings.current_env == 'development':
    print("Running in development mode")
```

## File Permissions

With separate files, you can set different permissions:

```bash
# Base config - readable by all
chmod 644 config.yaml
chmod 644 config.development.yaml

# Production config - restricted access
chmod 600 config.production.yaml
```

This is especially useful in production deployments where you want to restrict access to sensitive configuration data.
