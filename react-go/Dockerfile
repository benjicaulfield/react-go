# React-Go Dockerfile (Multi-stage build)

# Stage 1: Build React frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Build Go backend
FROM golang:1.21-alpine AS go-build
WORKDIR /app/go-backend
COPY go-backend/go.mod go-backend/go.sum ./
RUN go mod download
COPY go-backend/ .
RUN go build -o /app/bin/server ./main.go

# Stage 3: Final image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy built artifacts
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
COPY --from=go-build /app/bin/server ./bin/

# Copy Python services and configuration
COPY python-services/ ./python-services/
COPY go-backend/ ./go-backend/

# Install Python dependencies
RUN pip install -r python-services/requirements.txt

# Copy supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports
EXPOSE 3000 8080 5000

# Start all services with supervisor
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
