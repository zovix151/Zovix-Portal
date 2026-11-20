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


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


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

        no_redirect_opener = urllib.request.build_opener(NoRedirectHandler)
        secure_robots_request = urllib.request.Request(
            base_url + "/robots.txt",
            headers={"Host": "zovix.pro", "X-Forwarded-Proto": "https"},
        )
        with urllib.request.urlopen(secure_robots_request) as robots:
            assert robots.headers.get("Cache-Control") == "no-cache, max-age=0, must-revalidate"
            assert robots.read() == (seo_entrypoint.STATIC_DIR / "robots.txt").read_bytes()

        inspection_request = urllib.request.Request(
            base_url + "/robots.txt",
            headers={
                "Host": "zovix.pro",
                "User-Agent": "Google-InspectionTool",
                "X-Forwarded-Proto": "http",
            },
        )
        with no_redirect_opener.open(inspection_request) as inspection_robots:
            assert inspection_robots.status == 200
            assert inspection_robots.headers.get("Location") is None
            assert inspection_robots.headers.get_content_type() == "text/plain"
            assert inspection_robots.headers.get_content_charset() == "utf-8"
            assert inspection_robots.headers.get("Cache-Control") == (
                "no-cache, max-age=0, must-revalidate"
            )
            assert inspection_robots.read() == (
                seo_entrypoint.STATIC_DIR / "robots.txt"
            ).read_bytes()

        bot_request = urllib.request.Request(
            base_url + "/",
            headers={
                "Host": "zovix.pro",
                "User-Agent": "Googlebot",
                "X-Forwarded-Proto": "https",
            },
        )
        with urllib.request.urlopen(bot_request) as bot_root:
            bot_body = bot_root.read()
        assert bot_body == (seo_entrypoint.STATIC_DIR / "index.html").read_bytes()
        for metadata in (
            b"<title>Zovix \xe2\x80\x94 Cinematic AI Studio</title>",
            b'<meta name="description" content="Create cinematic AI videos, scenes, and visuals with Zovix. '
            b'Direct scenes, control camera motion, and generate high-impact AI media.">',
            b'<link rel="canonical" href="https://zovix.pro/" />',
            b'<meta property="og:title" content="Zovix \xe2\x80\x94 Cinematic AI Studio">',
            b'<meta property="og:description" content="Create cinematic AI videos, scenes, and visuals with Zovix. '
            b'Direct scenes, control camera motion, and generate high-impact AI media.">',
            b'<meta property="og:url" content="https://zovix.pro/">',
            b'<meta property="og:type" content="website">',
        ):
            assert metadata in bot_body

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

        apex_http_request = urllib.request.Request(
            base_url + "/?page=studio",
            headers={"Host": "zovix.pro", "X-Forwarded-Proto": "http"},
        )
        with pytest.raises(urllib.error.HTTPError) as redirect_error:
            no_redirect_opener.open(apex_http_request)
        assert redirect_error.value.code == 301
        assert redirect_error.value.headers["Location"] == "https://zovix.pro/?page=studio"

        www_http_request = urllib.request.Request(
            base_url + "/about?inspection=1",
            headers={"Host": "www.zovix.pro", "X-Forwarded-Proto": "http"},
        )
        with pytest.raises(urllib.error.HTTPError) as www_redirect_error:
            no_redirect_opener.open(www_http_request)
        assert www_redirect_error.value.code == 301
        assert (
            www_redirect_error.value.headers["Location"]
            == "https://zovix.pro/about?inspection=1"
        )

        https_request = urllib.request.Request(
            base_url + "/robots.txt",
            headers={"Host": "zovix.pro", "X-Forwarded-Proto": "https"},
        )
        with no_redirect_opener.open(https_request) as https_robots:
            assert https_robots.status == 200
            assert https_robots.read() == (seo_entrypoint.STATIC_DIR / "robots.txt").read_bytes()

        forwarded_ssl_request = urllib.request.Request(
            base_url + "/",
            headers={"Host": "zovix.pro", "X-Forwarded-Ssl": "on"},
        )
        with no_redirect_opener.open(forwarded_ssl_request) as secure_root:
            assert secure_root.status == 200

        www_https_request = urllib.request.Request(
            base_url + "/?page=studio",
            headers={"Host": "www.zovix.pro", "X-Forwarded-Proto": "https"},
        )
        with pytest.raises(urllib.error.HTTPError) as www_https_error:
            no_redirect_opener.open(www_https_request)
        assert www_https_error.value.code == 301
        assert (
            www_https_error.value.headers["Location"]
            == "https://zovix.pro/?page=studio"
        )
    finally:
        process.terminate()
        process.wait(timeout=10)
        process.stderr.close()


def test_invalid_app_mode_fails_explicitly():
    with pytest.raises(ValueError, match="Unknown ZOVIX_APP_MODE"):
        seo_entrypoint.create_app("invalid")
