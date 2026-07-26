#!/usr/bin/env bash

# Build the Docker image for the backend and run it in detached mode.
docker build -t pm-backend .
docker run -d --name pm-backend -p 8000:8000 pm-backend
