# JSTC FastAPI Project

A modular FastAPI project with organized structure for scalability and maintainability.

## Features

- **Modular Architecture**: Organized into separate modules for models, routers, and configuration
- **Pydantic Models**: Comprehensive request/response validation with proper separation
- **Configuration Management**: Environment-based configuration using Pydantic Settings
- **CORS Support**: Configurable cross-origin resource sharing
- **API Documentation**: Automatic OpenAPI documentation with detailed examples
- **Type Safety**: Full type annotations throughout the codebase
- **Database Ready**: Pre-configured SQLAlchemy integration for easy database adoption

## Project Structure

```
api/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── item.py          # Item-related Pydantic models
│   │   └── common.py        # Common response models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── items.py         # Item endpoints
│   │   └── health.py        # Health check endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # Application configuration
│   └── database.py          # Database configuration (future use)
├── main.py                  # FastAPI application entry point
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore patterns
└── README.md               # Project documentation
```

## Setup

1. **Create a virtual environment**:

   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment**:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment** (optional):

   ```bash
   cp .env.example .env
   # Edit .env file with your settings
   ```

## Running the Application

Start the development server:

```bash
uvicorn main:app --reload
```

Or run directly:

```bash
python main.py
```

The API will be available at:

- **API**: <http://localhost:8000>
- **Interactive API docs (Swagger UI)**: <http://localhost:8000/docs>
- **Alternative API docs (ReDoc)**: <http://localhost:8000/redoc>

## API Endpoints

### General

- `GET /` - Welcome message with API information
- `GET /health` - Health check with status and version
- `GET /health/ping` - Simple ping endpoint

### Items

- `GET /items` - Get all items (with pagination)
- `GET /items/{item_id}` - Get item by ID
- `POST /items` - Create new item
- `PUT /items/{item_id}` - Update item (partial updates supported)
- `DELETE /items/{item_id}` - Delete item

## Model Structure

### Request Models

- `ItemCreate`: For creating new items
- `ItemUpdate`: For updating existing items (all fields optional)

### Response Models

- `Item`: Complete item with ID and timestamps
- `ItemListResponse`: Paginated list of items with metadata
- `SuccessResponse`: Standard success response
- `ErrorResponse`: Standard error response
- `HealthResponse`: Health check response

## Configuration

The application uses environment-based configuration. Available settings:

```python
# API Configuration
API_TITLE="JSTC API"
API_DESCRIPTION="A FastAPI application with modular structure"
API_VERSION="1.0.0"
API_HOST="0.0.0.0"
API_PORT=8000
DEBUG=True

# CORS Configuration
ALLOWED_ORIGINS=["*"]
ALLOWED_METHODS=["*"]
ALLOWED_HEADERS=["*"]

# Database (for future use)
DATABASE_URL="sqlite:///./sql_app.db"
```

## Example Usage

### Create an item

```bash
curl -X POST "http://localhost:8000/items" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Laptop",
       "description": "Gaming laptop with high-end specs",
       "price": 999.99,
       "tax": 99.99
     }'
```

### Get all items

```bash
curl "http://localhost:8000/items?skip=0&limit=10"
```

### Update an item

```bash
curl -X PUT "http://localhost:8000/items/1" \
     -H "Content-Type: application/json" \
     -d '{"price": 899.99}'
```

## Development

### Adding New Models

1. Create model files in `app/models/`
2. Define Pydantic models with proper validation
3. Separate create/update/response models as needed

### Adding New Endpoints

1. Create router files in `app/routers/`
2. Define endpoints with proper documentation
3. Include router in `main.py`

### Database Integration

The project is pre-configured for database integration:

1. Uncomment SQLAlchemy imports
2. Create database models
3. Update endpoints to use database sessions
4. Run migrations as needed

## Next Steps

Consider adding:

- Database models and migrations
- Authentication and authorization (JWT)
- Logging and monitoring
- API versioning
- Rate limiting
- Docker containerization
- Unit and integration tests
- CI/CD pipeline
