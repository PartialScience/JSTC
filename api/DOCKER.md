# Docker Setup and Usage Guide

This guide explains how to run the JSTC API using Docker and Docker Compose.

## Quick Start

### Development Mode
```bash
# Start the application in development mode
docker-compose -f docker-compose.dev.yml up --build

# Access the API at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Production Mode
```bash
# Start the full application stack
docker-compose up --build

# Access the API at http://localhost:80 (via Nginx)
# Direct API access at http://localhost:8000
```

## Available Services

### Development Stack (docker-compose.dev.yml)
- **API**: FastAPI application with hot reload
- **Database**: PostgreSQL for data storage

### Production Stack (docker-compose.yml)
- **API**: FastAPI application (multi-worker)
- **Database**: PostgreSQL with persistent volumes
- **Redis**: For caching and sessions
- **Nginx**: Reverse proxy with rate limiting

## Docker Files

### Dockerfile
- Standard development/production Dockerfile
- Single-stage build
- Good for development and small deployments

### Dockerfile.prod
- Multi-stage production Dockerfile
- Smaller final image size
- Better security with non-root user
- Optimized for production

## Environment Configuration

The Docker setup uses Dynaconf environment variables:

```bash
# Set environment
ENV_FOR_DYNACONF=development  # or staging, production

# Override configuration
JSTC_API__HOST=0.0.0.0
JSTC_API__PORT=8000
JSTC_DATABASE__URL=postgresql://user:pass@host/db
```

## Common Commands

### Build and Run
```bash
# Development with hot reload
docker-compose -f docker-compose.dev.yml up --build

# Production stack
docker-compose up --build -d

# Build production image
docker build -f Dockerfile.prod -t jstc-api:prod .
```

### Managing Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (careful - deletes data!)
docker-compose down -v

# View logs
docker-compose logs api
docker-compose logs -f api  # Follow logs

# Execute commands in running container
docker-compose exec api bash
docker-compose exec db psql -U postgres -d jstc_db
```

### Database Management
```bash
# Access PostgreSQL
docker-compose exec db psql -U postgres -d jstc_db

# Backup database
docker-compose exec db pg_dump -U postgres jstc_db > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres jstc_db < backup.sql
```

## Configuration Files

### docker-compose.yml
Full production stack with:
- API server with multiple workers
- PostgreSQL database with persistent storage
- Redis for caching
- Nginx reverse proxy

### docker-compose.dev.yml
Development stack with:
- API server with hot reload
- PostgreSQL database
- Source code mounted for live editing

## Security Considerations

### Production Checklist
- [ ] Change default passwords in docker-compose.yml
- [ ] Set secure JSTC_SECRET_KEY
- [ ] Configure SSL certificates for Nginx
- [ ] Review and restrict network access
- [ ] Enable firewall rules
- [ ] Use secrets management for sensitive data

### Environment Variables
```bash
# Required in production
JSTC_SECRET_KEY=your-very-secure-secret-key
POSTGRES_PASSWORD=secure-database-password

# Optional overrides
JSTC_DATABASE__URL=postgresql://user:pass@host/db
JSTC_API__DEBUG=false
```

## Monitoring and Health Checks

### Health Check Endpoint
```bash
# Check API health
curl http://localhost:8000/health

# Through Nginx
curl http://localhost/health
```

### Container Health
```bash
# Check container status
docker-compose ps

# View health check status
docker inspect --format='{{.State.Health.Status}}' jstc-api
```

## Scaling

### Horizontal Scaling
```bash
# Scale API instances
docker-compose up --scale api=3

# Load balance with Nginx (already configured)
```

### Resource Limits
Add to docker-compose.yml:
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

## Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   # Check what's using port 8000
   netstat -tulpn | grep 8000
   
   # Use different ports in docker-compose.yml
   ports:
     - "8001:8000"
   ```

2. **Database connection issues**
   ```bash
   # Check database logs
   docker-compose logs db
   
   # Verify connection
   docker-compose exec api python -c "from app.database import engine; print(engine.url)"
   ```

3. **Permission issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

### Logs and Debugging
```bash
# View all logs
docker-compose logs

# Follow specific service logs
docker-compose logs -f api

# Debug container
docker-compose exec api bash
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Build and test
  run: |
    docker build -f Dockerfile.prod -t jstc-api:${{ github.sha }} .
    docker run --rm jstc-api:${{ github.sha }} python -m pytest
```

### Production Deployment
```bash
# Build production image
docker build -f Dockerfile.prod -t jstc-api:latest .

# Push to registry
docker tag jstc-api:latest your-registry/jstc-api:latest
docker push your-registry/jstc-api:latest
```
