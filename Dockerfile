# ------------------------------------------------------------
# Multi‑stage build: first stage builds the Next.js frontend
# ------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

# Set working directory for the frontend
WORKDIR /frontend

# Copy only package files first to leverage layer caching
COPY frontend/package.json frontend/package-lock.json* ./

# Install frontend dependencies (npm ci for reproducible install)
RUN npm ci

# Copy the rest of the frontend source code
COPY frontend/ ./

# Build the Next.js app. With `output: "export"` in next.config.ts the build
# automatically generates a static `out/` directory, so no separate `next export`
# command is required.
RUN npm run build

# ------------------------------------------------------------
# Second stage: lightweight Python image serving the static files
# ------------------------------------------------------------
FROM python:3.12-slim

# Install uv (the Python package manager) – recommended in project constraints
RUN pip install --no-cache-dir uv

# Ensure that user‑installed scripts (e.g., pytest) are in PATH
ENV PATH="/root/.local/bin:$PATH"

# Set working directory for the backend
WORKDIR /app

# Copy backend source code and requirements
COPY backend/ ./backend/

# Install backend dependencies using uv in the system environment (no virtualenv)
RUN uv pip install --system -r backend/requirements.txt

# Copy the exported static frontend into the backend static directory
# The "out" folder from the builder stage contains index.html and assets.
COPY --from=frontend-builder /frontend/out/ ./backend/static/

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI app with uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
