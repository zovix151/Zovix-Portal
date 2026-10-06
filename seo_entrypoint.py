from pathlib import Path

from starlette.responses import FileResponse
from starlette.routing import Route
from streamlit.web.server.starlette import App


STATIC_DIR = Path(__file__).parent / "static"


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


app = App(
    "replit_face_app.py",
    routes=[
        Route("/", serve_home),
        Route("/zovix-logo.svg", serve_brand_logo),
        Route("/robots.txt", serve_robots),
        Route("/sitemap.xml", serve_sitemap),
        Route("/about", serve_about),
        Route("/engines", serve_engines),
    ],
)