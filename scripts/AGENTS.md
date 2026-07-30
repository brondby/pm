Start/stop scripts for the Docker container, one pair per platform:

- `start.sh` / `stop.sh` (Linux)
- `start.command` / `stop.command` (macOS)
- `start.bat` / `stop.bat` (Windows)

Each `start.*` script builds the image (`docker build -t pm-backend .`) and runs it detached on port 8000
(`docker run -d --name pm-backend -p 8000:8000 pm-backend`). Each `stop.*` removes that container
(`docker rm -f pm-backend`). `docker compose build && docker compose up` is an equivalent alternative (see root
`README.md`).