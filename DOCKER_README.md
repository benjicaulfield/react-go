"# Docker Setup for Records App Projects

This repository contains Docker configurations for both the Django-HTMX and React-Go implementations of the Records App.

## Prerequisites

- Docker and Docker Compose installed on your system
- Git (to clone the repository)

## Project Structure

```
records/
├── django-htmx/          # Django-HTMX implementation
├── react-go/             # React-Go implementation
├── index.html            # Diagnostic comparison page
├── docker-compose.yml    # Docker Compose configuration
└── DOCKER_README.md      # This file
```

## Quick Start

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd records
   ```

2. **Build and start all services:**
   ```bash
   docker-compose up --build
   ```

3. **Access the applications:**
   - Django-HTMX: http://localhost:8000
   - React-Go Frontend: http://localhost:3000
   - React-Go Backend: http://localhost:8080
   - React-Go Python Services: http://localhost:5000
   - Diagnostic Page: Open `index.html` in your browser

## Individual Project Dockerfiles

### Django-HTMX

The Django-HTMX Dockerfile:
- Uses Python 3.11-slim base image
- Installs system dependencies (gcc, python3-dev, libpq-dev)
- Uses uv for dependency management
- Runs Django migrations and starts the development server
- Exposes port 8000

**Build and run:**
```bash
cd django-htmx
docker build -t django-htmx .
docker run -p 8000:8000 django-htmx
```

### React-Go

The React-Go Dockerfile uses a multi-stage build:
1. **Frontend Build:** Builds the React application using Node.js
2. **Go Backend Build:** Compiles the Go backend
3. **Final Image:** Combines everything and uses supervisor to run all services

**Services managed by supervisor:**
- Go backend server
- Python recommendation service
- Python scraper service
- React frontend (served via npx serve)

**Build and run:**
```bash
cd react-go
docker build -t react-go .
docker run -p 3000:3000 -p 8080:8080 -p 5000:5000 react-go
```

## Docker Compose

The `docker-compose.yml` file allows you to run both projects simultaneously:

```bash
# Start both projects
docker-compose up

# Start in detached mode
docker-compose up -d

# Stop all services
docker-compose down

# Rebuild images
docker-compose up --build
```

## Environment Variables

### Django-HTMX
- `DEBUG=1` - Enable Django debug mode
- `SECRET_KEY=your-secret-key-here` - Django secret key

### React-Go
- `NODE_ENV=production` - Set Node.js environment
- `GO_ENV=production` - Set Go environment

## Troubleshooting

1. **Port conflicts:** If ports are already in use, modify the port mappings in docker-compose.yml
2. **Build failures:** Ensure you have sufficient disk space and internet connection
3. **Database issues:** The Django project uses SQLite by default, but can be configured for PostgreSQL
4. **Permission issues:** Run Docker commands with appropriate permissions (sudo if needed)

## Customization

- **Add more services:** Modify docker-compose.yml to add additional services
- **Change ports:** Update port mappings in both Dockerfiles and docker-compose.yml
- **Production deployment:** Consider using Docker Swarm or Kubernetes for production

## Contributing

1. Test the Docker configurations on your local machine
2. Report any issues or improvements
3. Follow the existing patterns when adding new services"
