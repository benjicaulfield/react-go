# Python Microservices

This directory contains Python microservices that work with the Go backend to provide scraping and recommendation functionality.

## Services

### 1. Scraper Service (`scraper-service.py`)
- **Port**: 8001
- **Purpose**: Handles web scraping operations for seller data
- **Endpoints**:
  - `POST /scrape` - Trigger scraping for a seller
  - `GET /health` - Health check

### 2. Recommendation Service (`recommendation-service.py`)
- **Port**: 8002
- **Purpose**: Provides ML predictions and thermodynamic record selection
- **Endpoints**:
  - `POST /predict` - Get ML predictions for listings
  - `POST /train` - Train the ML model with user feedback
  - `POST /thermodynamic` - Get thermodynamic record selection
  - `GET /health` - Health check

## Installation

1. **Create a virtual environment:**
   ```bash
   cd python-services
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Services

### Start both services in separate terminals:

**Terminal 1 - Scraper Service:**
```bash
cd python-services
source venv/bin/activate
python scraper-service.py
```

**Terminal 2 - Recommendation Service:**
```bash
cd python-services
source venv/bin/activate
python recommendation-service.py
```

## Integration with Go Backend

The Go backend is configured to call these services at:
- Scraper: `http://localhost:8001`
- Recommendation: `http://localhost:8002`

These URLs can be configured via environment variables:
- `SCRAPER_SERVICE_URL`
- `RECOMMENDER_SERVICE_URL`

## API Examples

### Scraper Service

**Trigger scraping:**
```bash
curl -X POST http://localhost:8001/scrape \
  -H "Content-Type: application/json" \
  -d '{"seller_name": "test_seller"}'
```

**Health check:**
```bash
curl http://localhost:8001/health
```

### Recommendation Service

**Get predictions:**
```bash
curl -X POST http://localhost:8002/predict \
  -H "Content-Type: application/json" \
  -d '{"listing_ids": [1, 2, 3]}'
```

**Train model:**
```bash
curl -X POST http://localhost:8002/train \
  -H "Content-Type: application/json" \
  -d '{"listing_ids": [1, 2, 3], "keeper_ids": [1, 3]}'
```

**Thermodynamic selection:**
```bash
curl -X POST http://localhost:8002/thermodynamic \
  -H "Content-Type: application/json" \
  -d '{"force_refresh": true}'
```

**Health check:**
```bash
curl http://localhost:8002/health
```

## Current Implementation

These are **stub implementations** that simulate the behavior of the real services. They:

- Return realistic mock data
- Include proper error handling
- Simulate processing delays
- Log operations for debugging

## Migrating to Real Implementation

To replace these stubs with real functionality:

1. **For Scraper Service:**
   - Import the existing Django scraper code
   - Replace the mock scraping logic with real scraper calls
   - Handle database operations (or delegate to Go backend)

2. **For Recommendation Service:**
   - Import the existing Django ML models
   - Load trained models and vectorizers
   - Replace mock predictions with real ML inference
   - Implement real thermodynamic algorithms

## Error Handling

Both services include comprehensive error handling:
- Input validation
- Exception catching
- Proper HTTP status codes
- Detailed error messages

## Logging

Services use Python's logging module to provide:
- Request/response logging
- Error tracking
- Performance monitoring
- Debug information

## Development

### Adding New Endpoints

1. Add the route handler function
2. Include proper error handling
3. Add logging statements
4. Update this README

### Testing

Test the services independently:

```bash
# Test scraper
python -c "
import requests
resp = requests.post('http://localhost:8001/scrape', 
                    json={'seller_name': 'test'})
print(resp.json())
"

# Test recommendation
python -c "
import requests
resp = requests.post('http://localhost:8002/predict', 
                    json={'listing_ids': [1, 2, 3]})
print(resp.json())
"
```

## Production Deployment

For production:

1. **Use a proper WSGI server** (e.g., Gunicorn):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8001 scraper-service:app
   gunicorn -w 4 -b 0.0.0.0:8002 recommendation-service:app
   ```

2. **Set up process management** (systemd, supervisor, etc.)

3. **Configure logging** for production

4. **Add monitoring and health checks**

5. **Use environment variables** for configuration

## Architecture Benefits

This microservice architecture provides:

- **Separation of concerns**: Go handles API/DB, Python handles ML/scraping
- **Language optimization**: Use Go for performance, Python for ML libraries
- **Independent scaling**: Scale services based on load
- **Technology flexibility**: Upgrade services independently
- **Fault isolation**: Service failures don't bring down the entire system
