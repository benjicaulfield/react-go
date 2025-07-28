"#!/bin/bash

echo \"Testing Docker configurations for Records App projects...\"
echo

# Test Django-HTMX Dockerfile
echo \"1. Testing Django-HTMX Dockerfile...\"
cd django-htmx
docker build -t django-htmx-test . --no-cache
if [ $? -eq 0 ]; then
    echo \"✓ Django-HTMX Dockerfile builds successfully\"
else
    echo \"✗ Django-HTMX Dockerfile build failed\"
fi
cd ..

echo

# Test React-Go Dockerfile
echo \"2. Testing React-Go Dockerfile...\"
cd react-go
docker build -t react-go-test . --no-cache
if [ $? -eq 0 ]; then
    echo \"✓ React-Go Dockerfile builds successfully\"
else
    echo \"✗ React-Go Dockerfile build failed\"
fi
cd ..

echo
echo \"3. Testing Docker Compose configuration...\"
docker-compose config
if [ $? -eq 0 ]; then
    echo \"✓ Docker Compose configuration is valid\"
else
    echo \"✗ Docker Compose configuration is invalid\"
fi

echo
echo \"Docker testing completed!\""
