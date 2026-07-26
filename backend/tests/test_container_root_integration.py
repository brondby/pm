"""Container integration test for deployed root page.

This test intentionally validates deployed behavior, not in-process app behavior:
- builds the Docker image
- runs the container
- verifies `/` serves the exported Kanban frontend (not the Hello World scaffold)
"""

from __future__ import annotations

import os
import secrets
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest


RUN_CONTAINER_INTEGRATION = os.getenv("RUN_CONTAINER_INTEGRATION_TESTS") == "1"


@pytest.mark.skipif(
    not RUN_CONTAINER_INTEGRATION,
    reason="Set RUN_CONTAINER_INTEGRATION_TESTS=1 to run Docker integration tests.",
)
def test_container_root_serves_kanban_frontend_not_hello_world() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    image_tag = "pm-backend"
    container_name = f"pm-backend-it-{secrets.token_hex(4)}"

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        host_port = sock.getsockname()[1]

    subprocess.run(
        ["docker", "build", "-t", image_tag, str(repo_root)],
        check=True,
        cwd=repo_root,
    )

    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container_name,
            "-p",
            f"{host_port}:8000",
            image_tag,
        ],
        check=True,
        cwd=repo_root,
    )

    try:
        deadline = time.time() + 90
        last_error: Exception | None = None
        response: httpx.Response | None = None

        while time.time() < deadline:
            try:
                response = httpx.get(f"http://127.0.0.1:{host_port}/", timeout=2.0)
                if response.status_code == 200:
                    break
            except Exception as error:  # pragma: no cover - best-effort polling
                last_error = error
            time.sleep(1)

        if response is None or response.status_code != 200:
            if last_error is not None:
                raise AssertionError(f"Container root endpoint did not become ready: {last_error}")
            raise AssertionError("Container root endpoint did not return HTTP 200 in time")

        html = response.text
        html_lower = html.lower()

        assert response.headers["content-type"].startswith("text/html")
        assert "hello, world!" not in html_lower
        assert "<title>hello world</title>" not in html_lower
        assert "/_next/" in html_lower
        assert "kanban" in html_lower
    finally:
        subprocess.run(["docker", "rm", "-f", container_name], check=False, cwd=repo_root)
