from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import landing_page
import pytest


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


def test_android_download_requires_apk_or_url(monkeypatch, tmp_path):
    rendered = []
    monkeypatch.delenv("ZOVIX_ANDROID_APK_URL", raising=False)
    monkeypatch.setattr(landing_page, "__file__", str(tmp_path / "landing_page.py"))
    monkeypatch.setattr(landing_page.st, "markdown", lambda html, **kwargs: rendered.append(html))
    monkeypatch.setattr(landing_page, "static_asset_data_uri", lambda filename: "image")
    page = landing_page.WorldClassLandingPage.__new__(landing_page.WorldClassLandingPage)

    assert "zx-get-app" not in page._navbar_html()
    page._render_showcase()
    assert "zx-app-note" not in rendered[-1]
    apk = tmp_path / "static" / "downloads" / "zovix-android.apk"
    apk.parent.mkdir(parents=True)
    apk.write_bytes(b"test")
    assert "/app/static/downloads/zovix-android.apk" in page._navbar_html()


def test_android_download_url_and_hero_note(monkeypatch):
    rendered = []
    monkeypatch.setenv("ZOVIX_ANDROID_APK_URL", "https://example.com/app.apk?one=1&two=2")
    monkeypatch.setattr(landing_page.st, "markdown", lambda html, **kwargs: rendered.append(html))
    monkeypatch.setattr(landing_page, "static_asset_data_uri", lambda filename: "image")
    page = landing_page.WorldClassLandingPage.__new__(landing_page.WorldClassLandingPage)

    page._render_showcase()

    assert "href='https://example.com/app.apk?one=1&amp;two=2' download='Zovix-Android.apk'" in rendered[-1]
    assert "Android app available" in rendered[-1]


@pytest.mark.parametrize("url", ["javascript:alert(1)", "//example.com/app.apk", "https://example.com/a b.apk"])
def test_android_download_rejects_invalid_url(monkeypatch, url):
    monkeypatch.setenv("ZOVIX_ANDROID_APK_URL", url)
    with pytest.raises(ValueError, match="ZOVIX_ANDROID_APK_URL"):
        landing_page._android_apk_url()
