"# Docker Diagnostic Integration

This document explains how the Docker diagnostic functionality works in the index.html page.

## Overview

When you click the "Start Diagnostic Comparison" button on index.html, it:
1. Starts the Docker Compose environment with `docker-compose up --build -d`
2. Waits for containers to start
3. Retrieves the size of each running container
4. Displays the container sizes on the page

## Requirements

1. **Node.js Server**: The `docker-server.js` must be running on port 3001
2. **Docker**: Docker and Docker Compose must be installed
3. **Docker Compose File**: The `docker-compose.yml` file must be present

## Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Start the Node.js Server

```bash
npm start
```

### 3. Open the Diagnostic Page

Open `index.html` in your web browser. The page will communicate with the Node.js server running on port 3001.

## How It Works

### Frontend (index.html)
- Uses JavaScript `fetch` API to send POST request to `/start-comparison` endpoint
- Displays loading state while waiting for Docker operations
- Shows container sizes in a formatted list

### Backend (docker-server.js)
- Express.js server listening on port 3001
- Handles CORS for cross-origin requests
- Executes `docker-compose up --build -d` command
- Waits 5 seconds for containers to start
- Executes `docker ps --format "{{.Names}}\t{{.Size}}"` to get container sizes
- Returns JSON response with container information

## Container Size Information

The displayed container sizes include:
- **Virtual Size**: The amount of disk space used by the container
- **Container Name**: The name of each running container

## Troubleshooting

### Common Issues:

1. **CORS Errors**: Ensure the Node.js server is running and accessible
2. **Docker Not Found**: Make sure Docker is installed and running
3. **Permission Issues**: Run the Node.js server with appropriate permissions
4. **Port Conflicts**: Check if port 3001 is already in use

### Error Messages:

- "Failed to start Docker comparison. Make sure the Node.js server is running on port 3001."
  - Solution: Start the Node.js server with `npm start`

## Customization

You can modify the `docker-server.js` file to:
- Change the wait time before checking container sizes
- Add additional Docker commands
- Modify the container size format
- Add more diagnostic information

## Security Considerations

- The Node.js server enables CORS for all origins (for development)
- In production, you should restrict CORS to specific origins
- Consider adding authentication for the diagnostic endpoints
- Be cautious about exposing Docker control endpoints"
