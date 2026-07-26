@echo off
rem Stop and remove the Docker container on Windows
docker rm -f pm-backend >nul 2>&1
