@echo off
rem Build and run the Docker container on Windows
docker build -t pm-backend .
docker run -d --name pm-backend -p 8000:8000 pm-backend
