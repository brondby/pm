#!/usr/bin/env bash

# Stop and remove the Docker container if it exists.
docker rm -f pm-backend >/dev/null 2>&1 || true
