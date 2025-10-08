#!/bin/bash

# Define variables
TAG="latest"

# Build the Docker image
docker build -t $IMAGE_NAME:$TAG .

# Log in to Docker Hub
echo "Logging in to Docker Hub..."
docker login

# Push the Docker image to Docker Hub
docker push $IMAGE_NAME:$TAG

echo "Docker image $IMAGE_NAME:$TAG has been pushed to Docker Hub."
