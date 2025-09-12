#!/bin/bash

# Build the Docker image
echo "Building Docker image..."
docker build -t kopi-chat .

# Stop and remove existing container if running
echo "Stopping existing container..."
docker stop kopi-chat-container 2>/dev/null || true
docker rm kopi-chat-container 2>/dev/null || true

# Run the container
echo "Starting container..."
docker run -d --name kopi-chat-container -p 8000:8000 kopi-chat

echo "Container started! Access the app at http://localhost:8000"
echo "To view logs: docker logs -f kopi-chat-container"