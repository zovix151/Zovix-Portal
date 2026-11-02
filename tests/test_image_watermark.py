import xml.etree.ElementTree as ET

from PIL import Image, ImageChops

from image_watermark import apply_zovix_watermark, should_apply_free_watermark


def test_free_plan_watermark_entitlement():
    assert should_apply_free_watermark(False, "")
    assert should_apply_free_watermark(True, "Free Plan")
    assert should_apply_free_watermark(True, "Unknown Plan")
    assert not should_apply_free_watermark(True, "Premium")
    assert not should_apply_free_watermark(True, "Standard Monthly")


def test_raster_watermark_creates_branded_copy(tmp_path):
    source_path = tmp_path / "drawing.png"
    Image.new("RGB", (640, 480), "white").save(source_path)

    watermarked_path = apply_zovix_watermark(source_path)

    assert watermarked_path.endswith("drawing_watermarked.png")
    with Image.open(source_path) as original, Image.open(watermarked_path) as watermarked:
        assert original.size == watermarked.size
        difference = ImageChops.difference(
            original.convert("RGBA"),
            watermarked.convert("RGBA"),
        )
        assert difference.convert("RGB").getbbox() is not None
        assert original.getpixel((630, 470)) == (255, 255, 255)


def test_svg_watermark_is_added_to_downloadable_blueprint(tmp_path):
    source_path = tmp_path / "blueprint.svg"
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 800">'
        '<rect width="1000" height="800" fill="white"/></svg>',
        encoding="utf-8",
    )

    watermarked_path = apply_zovix_watermark(source_path)
    with open(watermarked_path, encoding="utf-8") as output_file:
        assert output_file.read().lstrip().startswith("<svg")
    root = ET.parse(watermarked_path).getroot()

    assert any(element.attrib.get("aria-label") == "ZOVIX watermark" for element in root.iter())
