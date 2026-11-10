import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

import pytest

import seo_entrypoint


@pytest.mark.parametrize("mode", [None, "replit", "studio"])
def test_sitemap_and_robots_are_served_at_root(mode):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    env = os.environ.copy()
    if mode is None:
        env.pop("ZOVIX_APP_MODE", None)
    else:
        env["ZOVIX_APP_MODE"] = mode
    process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "seo_entrypoint:app",
            "--host", "127.0.0.1", "--port", str(port),
        ],
        cwd=seo_entrypoint.ROOT_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 30
        while True:
            if process.poll() is not None:
                pytest.fail(f"Server exited: {process.stderr.read().decode(errors='replace')}")
            try:
                response = urllib.request.urlopen(base_url + "/sitemap.xml", timeout=1)
                break
            except urllib.error.URLError:
                if time.monotonic() >= deadline:
                    pytest.fail("Server did not become ready within 30 seconds")
                time.sleep(0.1)

        with response:
            assert response.status == 200
            assert response.headers.get_content_type() == "application/xml"
            body = response.read()
        assert body == (seo_entrypoint.STATIC_DIR / "sitemap.xml").read_bytes()
        assert ET.fromstring(body).tag.endswith("}urlset")

        request = urllib.request.Request(base_url + "/sitemap.xml", method="HEAD")
        with urllib.request.urlopen(request) as head:
            assert head.status == 200
            assert head.headers.get_content_type() == "application/xml"
            assert head.read() == b""

        with urllib.request.urlopen(base_url + "/robots.txt") as robots:
            assert robots.read() == (seo_entrypoint.STATIC_DIR / "robots.txt").read_bytes()

        for path, filename in [
            ("/about", "about.html"),
            ("/engines", "engines.html"),
            ("/face-generation-policy", "face-generation-policy.html"),
        ]:
            with urllib.request.urlopen(base_url + path) as info:
                assert info.read() == (seo_entrypoint.STATIC_DIR / filename).read_bytes()

        with urllib.request.urlopen(base_url + "/") as root:
            root_body = root.read()
        if mode == "replit":
            assert root_body == (seo_entrypoint.STATIC_DIR / "index.html").read_bytes()
        else:
            assert b"streamlit" in root_body.lower()
            with urllib.request.urlopen(base_url + "/?page=login") as login:
                assert login.read() == root_body
    finally:
        process.terminate()
        process.wait(timeout=10)
        process.stderr.close()


def test_invalid_app_mode_fails_explicitly():
    with pytest.raises(ValueError, match="Unknown ZOVIX_APP_MODE"):
        seo_entrypoint.create_app("invalid")
