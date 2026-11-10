from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import landing_page


class VideoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.videos = []

    def handle_starttag(self, tag, attrs):
        if tag == "video":
            self.videos.append(dict(attrs))


def test_cinematic_demo_uses_local_autoplay_video(monkeypatch):
    rendered = []
    monkeypatch.setattr(landing_page.st, "markdown", lambda html, **kwargs: rendered.append(html))
    monkeypatch.setattr(landing_page, "static_asset_data_uri", lambda filename: "image")
    monkeypatch.setattr(landing_page.WorldClassLandingPage, "_navbar_html", lambda self: "")

    landing_page.WorldClassLandingPage.__new__(landing_page.WorldClassLandingPage)._render_showcase()

    parser = VideoParser()
    parser.feed(rendered[-1])
    video = next(video for video in parser.videos if video.get("class") == "zx-demo-video")
    assert {"autoplay", "muted", "loop", "playsinline", "controls"} <= video.keys()
    assert video["src"].startswith("/app/static/")
    filename = unquote(video["src"].removeprefix("/app/static/"))
    assert (Path(landing_page.__file__).resolve().parent / "static" / filename).is_file()
