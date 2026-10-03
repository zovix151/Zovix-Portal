from pathlib import Path

from starlette.responses import FileResponse
from starlette.routing import Route
from streamlit.web.server.starlette import App


STATIC_DIR = Path(__file__).parent / "static"


async def serve_robots(_request):
    return FileResponse(STATIC_DIR / "robots.txt", media_type="text/plain")


async def serve_sitemap(_request):
    return FileResponse(STATIC_DIR / "sitemap.xml", media_type="application/xml")


app = App(
    "replit_face_app.py",
    routes=[
        Route("/robots.txt", serve_robots),
        Route("/sitemap.xml", serve_sitemap),
    ],
)