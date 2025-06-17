# Go Backend for Discogs API

This is a Go/Gin backend that replaces the Django/Python backend while maintaining the same API endpoints for the React/TypeScript frontend.

## Features

- **Gin Framework**: Fast HTTP web framework
- **GORM**: Object-relational mapping for PostgreSQL
- **Same API Endpoints**: Compatible with existing React frontend
- **Microservice Architecture**: Calls to Python scraper and recommendation services
- **CORS Support**: Configured for frontend development
- **Integration Tests**: Comprehensive test suite

## Prerequisites

- Go 1.21 or later
- PostgreSQL database (same as Django backend)
- Python microservices (scraper and recommendation services)

## Installation

1. **Clone and navigate to the Go backend directory:**
   ```bash
   cd go-backend
   ```

2. **Install dependencies:**
   ```bash
   go mod tidy
   ```

3. **Set up environment variables:**
   The application reads from the `.env` file in the parent directory. Ensure these variables are set:
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=app
   DB_PASSWORD=dairyman
   DB_NAME=records
   DB_SSLMODE=disable
   
   # Optional: Microservice URLs
   SCRAPER_SERVICE_URL=http://localhost:8001
   RECOMMENDER_SERVICE_URL=http://localhost:8002
   
   # Optional: External API keys
   EXCHANGE_RATE_API_KEY=your_key_here
   DISCOGS_CONSUMER_KEY=your_key_here
   DISCOGS_CONSUMER_SECRET=your_secret_here
   ```

## Running the Application

1. **Start the server:**
   ```bash
   go run main.go
   ```

2. **The server will start on port 8000 by default**
   - API will be available at `http://localhost:8000`
   - Same endpoints as the Django backend

## API Endpoints

The Go backend implements the same endpoints as the Django backend:

### Dashboard
- `GET /dashboard/` - Get dashboard statistics
- `GET /api/dashboard/listings/` - Get dashboard listings
- `POST /api/refresh-record-of-the-day/` - Refresh record of the day

### Search
- `GET /search/results/` - Search listings with filters
- `GET /autocomplete/genre/` - Genre autocomplete
- `GET /autocomplete/condition/` - Condition autocomplete
- `GET /autocomplete/styles/` - Styles autocomplete

### Seller Operations
- `POST /by-seller/search/` - Search listings by seller
- `POST /data/:seller` - Trigger scraper for seller
- `GET /records/seller/:seller/` - Get records by seller

### Recommendations
- `GET /recommendation-predictions/` - Get ML predictions
- `POST /submit-scoring-selections/` - Submit user selections
- `GET /model-performance-stats/` - Get model performance

### Other
- `GET /export-listings` - Export listings to CSV
- `POST /add-to-wantlist/` - Add record to wantlist
- `POST /vote-record-of-the-day/:id/` - Vote on record of the day

## Database

The Go backend uses the same PostgreSQL database as the Django backend. It connects to existing tables using GORM with custom table names that match Django's naming convention:

- `discogs_record`
- `discogs_seller` 
- `discogs_listing`
- `discogs_recommendationmodel`
- `discogs_recommendationmetrics`
- `discogs_recordoftheday`
- `discogs_recordofthedayfeedback`

## Microservices Integration

The Go backend is designed to work with Python microservices for:

1. **Scraper Service** (`http://localhost:8001`):
   - `POST /scrape` - Trigger scraping for a seller

2. **Recommendation Service** (`http://localhost:8002`):
   - `POST /predict` - Get ML predictions for listings
   - `POST /train` - Train the ML model
   - `POST /thermodynamic` - Get thermodynamic record selection

## Testing

Run the integration tests to verify everything works:

```bash
go test -v
```

The tests include:
- Database connectivity
- Dashboard API functionality
- Search functionality
- Seller operations
- Data integrity checks

## Development

### Project Structure
```
go-backend/
├── main.go                 # Application entry point
├── go.mod                  # Go module definition
├── integration_test.go     # Integration tests
├── internal/
│   ├── config/            # Configuration management
│   ├── database/          # Database connection and setup
│   ├── handlers/          # HTTP request handlers
│   ├── middleware/        # HTTP middleware
│   ├── models/           # GORM models
│   └── services/         # External service clients
└── README.md             # This file
```

### Adding New Endpoints

1. Add the handler function in `internal/handlers/handlers.go`
2. Register the route in `main.go`
3. Add tests in `integration_test.go`

### Database Migrations

The application uses GORM's AutoMigrate feature, but since we're using an existing Django database, migrations are handled by Django. The Go application just connects to existing tables.

## Switching from Django to Go

To switch the frontend from the Django backend to the Go backend:

1. **Stop the Django server** (usually running on port 8000)
2. **Start the Go server** on port 8000:
   ```bash
   cd go-backend
   go run main.go
   ```
3. **No frontend changes needed** - all endpoints are compatible

## Production Deployment

For production deployment:

1. **Build the binary:**
   ```bash
   go build -o discogs-api main.go
   ```

2. **Run the binary:**
   ```bash
   ./discogs-api
   ```

3. **Set environment variables** for production database and services

4. **Use a process manager** like systemd or supervisor

## Performance

The Go backend offers several performance improvements over Django:

- **Faster startup time**: Go compiles to native binary
- **Lower memory usage**: More efficient memory management
- **Better concurrency**: Go's goroutines handle concurrent requests efficiently
- **Faster JSON processing**: Native JSON support

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running
- Check database credentials in `.env`
- Ensure database exists and is accessible

### Microservice Connection Issues
- Verify Python services are running on expected ports
- Check service URLs in configuration
- Services will gracefully degrade if unavailable

### CORS Issues
- Frontend CORS is configured for localhost:5173 (Vite)
- Add additional origins in `main.go` if needed

## Contributing

1. Follow Go conventions and formatting (`go fmt`)
2. Add tests for new functionality
3. Update this README for significant changes
4. Ensure all tests pass before submitting changes
