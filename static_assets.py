import base64
from io import BytesIO
import re
from functools import lru_cache
from pathlib import Path


MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}


@lru_cache(maxsize=64)
def static_asset_data_uri(filename: str) -> str:
    if Path(filename).name != filename:
        raise ValueError(f"Expected a static asset filename, got {filename!r}")

    asset_path = Path(__file__).resolve().parent / "static" / filename
    media_type = MEDIA_TYPES.get(asset_path.suffix.lower())
    if media_type is None:
        raise ValueError(f"Could not determine the media type for {filename!r}")

    asset_bytes = asset_path.read_bytes()
    if media_type != "image/svg+xml":
        from PIL import Image

        with Image.open(BytesIO(asset_bytes)) as image:
            image.thumbnail((1600, 1200))
            has_alpha = "A" in image.getbands() or "transparency" in image.info
            image = image.convert("RGBA" if has_alpha else "RGB")
            optimized = BytesIO()
            image.save(optimized, format="WEBP", quality=82, method=4)
            asset_bytes = optimized.getvalue()
        media_type = "image/webp"

    encoded = base64.b64encode(asset_bytes).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def inline_static_asset_urls(markup: str) -> str:
    return re.sub(
        r"/app/static/([A-Za-z0-9_.-]+)",
        lambda match: static_asset_data_uri(match.group(1)),
        markup,
    )
