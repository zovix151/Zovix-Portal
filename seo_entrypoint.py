import os
from pathlib import Path

from starlette.responses import FileResponse
from starlette.routing import Route
from streamlit.web.server.starlette import App


ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "static"


async def serve_robots(_request):
    return FileResponse(STATIC_DIR / "robots.txt", media_type="text/plain")


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
        return App(ROOT_DIR / "app.py", routes=seo_routes)
    if mode != "replit":
        raise ValueError(f"Unknown ZOVIX_APP_MODE: {mode!r}; expected 'replit' or 'studio'")

    return App(
        ROOT_DIR / "replit_face_app.py",
        routes=seo_routes + [
            Route("/", serve_home),
        ],
    )


app = create_app(os.environ.get("ZOVIX_APP_MODE", "studio"))