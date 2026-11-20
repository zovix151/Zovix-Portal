import os
from pathlib import Path

from starlette.responses import FileResponse, RedirectResponse
from starlette.routing import Route
from streamlit.web.server.starlette import App


ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "static"


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


class SeoAndHttpsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
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

        await self.app(scope, receive, send)


async def serve_robots(_request):
    return FileResponse(
        STATIC_DIR / "robots.txt",
        media_type="text/plain",
        headers={"Cache-Control": "no-cache, max-age=0, must-revalidate"},
    )


async def serve_sitemap(_request):
    return FileResponse(STATIC_DIR / "sitemap.xml", media_type="application/xml")


async def serve_home(_request):
    return FileResponse(
        STATIC_DIR / "index.html",
        media_type="text/html",
        headers={"X-Robots-Tag": "index, follow", "Cache-Control": "public, max-age=300"},
    )


async def serve_brand_logo(_request):
    return FileResponse(STATIC_DIR / "zovix-logo.svg", media_type="image/svg+xml")


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
        Route("/zovix-logo.svg", serve_brand_logo),
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

    return SeoAndHttpsMiddleware(streamlit_app)


app = create_app(os.environ.get("ZOVIX_APP_MODE", "studio"))