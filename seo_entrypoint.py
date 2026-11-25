import os
from pathlib import Path

from starlette.responses import FileResponse, RedirectResponse
from starlette.routing import Route
from streamlit.web.server.starlette import App


ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "static"
MANIFEST_LINK = b'<link rel="manifest" href="/manifest.json" />'


def _robots_response():
    return FileResponse(
        STATIC_DIR / "robots.txt",
        media_type="text/plain",
        headers={"Cache-Control": "no-cache, max-age=0, must-revalidate"},
    )


def _is_https_request(scope, headers):
    forwarded_proto = headers.get(b"x-forwarded-proto", b"")
    if forwarded_proto:
        proto = forwarded_proto.split(b",", 1)[0].strip().lower()
        if proto == b"https":
            return True
        if proto == b"http":
            return False

    forwarded_ssl = headers.get(b"x-forwarded-ssl", b"")
    if forwarded_ssl.split(b",", 1)[0].strip().lower() in {
        b"on",
        b"true",
        b"1",
    }:
        return True

    return scope.get("scheme", "http").lower() == "https"


async def _serve_studio_with_manifest(app, scope, receive, send):
    scope = dict(scope)
    scope["headers"] = [
        (name, value) for name, value in scope.get("headers", [])
        if name.lower() not in {b"if-none-match", b"if-modified-since"}
    ]
    scope["extensions"] = {
        name: value for name, value in scope.get("extensions", {}).items()
        if name != "http.response.pathsend"
    }
    response_start = None
    chunks = []

    async def add_manifest_link(message):
        nonlocal response_start
        if message["type"] == "http.response.start":
            response_start = message
            return
        if message["type"] != "http.response.body" or response_start is None:
            await send(message)
            return
        chunks.append(message.get("body", b""))
        if message.get("more_body", False):
            return
        headers = response_start["headers"]
        content_type = next(
            (value for name, value in headers if name.lower() == b"content-type"),
            b"",
        )
        body = b"".join(chunks)
        if response_start["status"] == 200 and content_type.startswith(b"text/html"):
            if any(name.lower() == b"content-encoding" for name, _ in headers):
                raise RuntimeError("Cannot add manifest link to encoded HTML")
            if scope["method"] == "GET":
                if b"<head>" not in body:
                    raise RuntimeError("Streamlit HTML has no head element")
                body = body.replace(b"<head>", b"<head>\n    " + MANIFEST_LINK, 1)
                content_length = len(body)
            else:
                original_length = next(
                    int(value) for name, value in headers
                    if name.lower() == b"content-length"
                )
                content_length = original_length + len(b"\n    " + MANIFEST_LINK)
            response_start["headers"] = [
                (name, value) for name, value in headers
                if name.lower() not in {b"content-length", b"etag", b"last-modified"}
            ] + [(b"content-length", str(content_length).encode("ascii"))]
        await send(response_start)
        await send(dict(message, body=body))

    await app(scope, receive, add_manifest_link)


class SeoAndHttpsMiddleware:
    def __init__(self, app, mode):
        self.app = app
        self.mode = mode

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope["path"] == "/robots.txt" and scope["method"] in {"GET", "HEAD"}:
            await _robots_response()(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        host = headers.get(b"host", b"").split(b":", 1)[0].lower().rstrip(b".")

        if host in {b"zovix.pro", b"www.zovix.pro"} and (
            not _is_https_request(scope, headers) or host == b"www.zovix.pro"
        ):
            path = scope.get("raw_path", scope["path"].encode("ascii"))
            query = scope.get("query_string", b"")
            location = b"https://zovix.pro" + path
            if query:
                location += b"?" + query
            response = RedirectResponse(location.decode("ascii"), status_code=301)
            await response(scope, receive, send)
            return

        user_agent = headers.get(b"user-agent", b"").lower()
        crawler_markers = (
            b"bot",
            b"crawler",
            b"spider",
            b"slurp",
            b"preview",
            b"google-inspectiontool",
        )
        if scope["path"] == "/" and any(marker in user_agent for marker in crawler_markers):
            response = FileResponse(
                STATIC_DIR / "index.html",
                media_type="text/html",
                headers={
                    "X-Robots-Tag": "index, follow",
                    "Cache-Control": "public, max-age=300",
                },
            )
            await response(scope, receive, send)
            return

        if self.mode == "studio" and scope["path"] == "/" and scope["method"] in {"GET", "HEAD"}:
            await _serve_studio_with_manifest(self.app, scope, receive, send)
        else:
            await self.app(scope, receive, send)


async def serve_robots(_request):
    return _robots_response()


async def serve_sitemap(_request):
    return FileResponse(STATIC_DIR / "sitemap.xml", media_type="application/xml")


async def serve_manifest(_request):
    return FileResponse(STATIC_DIR / "manifest.json", media_type="application/manifest+json")


async def serve_assetlinks(_request):
    return FileResponse(
        STATIC_DIR / ".well-known" / "assetlinks.json",
        media_type="application/json",
        headers={"Cache-Control": "no-cache, max-age=0, must-revalidate"},
    )


async def serve_home(_request):
    return FileResponse(
        STATIC_DIR / "index.html",
        media_type="text/html",
        headers={"X-Robots-Tag": "index, follow", "Cache-Control": "public, max-age=300"},
    )


async def serve_brand_logo(_request):
    return FileResponse(STATIC_DIR / "zovix-logo.svg", media_type="image/svg+xml")


async def serve_favicon_png(_request):
    return FileResponse(STATIC_DIR / "favicon.png", media_type="image/png")


async def serve_favicon_ico(_request):
    return FileResponse(STATIC_DIR / "favicon.ico", media_type="image/vnd.microsoft.icon")


async def serve_about(_request):
    return FileResponse(
        STATIC_DIR / "about.html",
        media_type="text/html",
        headers={"X-Robots-Tag": "index, follow", "Cache-Control": "public, max-age=300"},
    )


async def serve_engines(_request):
    return FileResponse(
        STATIC_DIR / "engines.html",
        media_type="text/html",
        headers={"X-Robots-Tag": "index, follow", "Cache-Control": "public, max-age=300"},
    )


async def serve_face_generation_policy(_request):
    return FileResponse(
        STATIC_DIR / "face-generation-policy.html",
        media_type="text/html",
        headers={"X-Robots-Tag": "index, follow", "Cache-Control": "public, max-age=300"},
    )


def create_app(mode):
    seo_routes = [
        Route("/robots.txt", serve_robots),
        Route("/sitemap.xml", serve_sitemap),
        Route("/manifest.json", serve_manifest),
        Route("/.well-known/assetlinks.json", serve_assetlinks),
        Route("/zovix-logo.svg", serve_brand_logo),
        Route("/favicon.png", serve_favicon_png),
        Route("/favicon.ico", serve_favicon_ico),
        Route("/about", serve_about),
        Route("/engines", serve_engines),
        Route("/face-generation-policy", serve_face_generation_policy),
    ]
    if mode == "studio":
        streamlit_app = App(ROOT_DIR / "app.py", routes=seo_routes)
    elif mode == "replit":
        streamlit_app = App(
            ROOT_DIR / "replit_face_app.py",
            routes=seo_routes + [
                Route("/", serve_home),
            ],
        )
    else:
        raise ValueError(f"Unknown ZOVIX_APP_MODE: {mode!r}; expected 'replit' or 'studio'")

    return SeoAndHttpsMiddleware(streamlit_app, mode)


app = create_app(os.environ.get("ZOVIX_APP_MODE", "studio"))