import xml.etree.ElementTree as ET

import pytest

from blueprint_svg import sanitize_blueprint_svg


def test_sanitizer_keeps_blueprint_shapes_and_removes_active_content():
    source = """
    <svg xmlns="http://www.w3.org/2000/svg" width="1000" height="700"
         viewBox="0 0 1000 700" onload="alert(1)">
      <script>alert(1)</script>
      <foreignObject><p>not SVG</p></foreignObject>
      <defs>
        <linearGradient id="wall">
          <stop offset="0" stop-color="#fff"/>
        </linearGradient>
      </defs>
      <rect x="10" y="10" width="100" height="100"
            fill="url(#wall)" onclick="alert(1)"
            style="stroke:#fff;filter:url(https://example.test/filter)"/>
      <path d="M0 0 L10 10" stroke="#0ff"/>
      <image href="https://example.test/asset.png"/>
    </svg>
    """

    sanitized = sanitize_blueprint_svg(source)
    root = ET.fromstring(sanitized)
    names = [element.tag.rsplit("}", 1)[-1] for element in root.iter()]

    assert "rect" in names
    assert "path" in names
    assert "script" not in names
    assert "foreignObject" not in names
    assert "image" not in names
    assert "onload" not in root.attrib
    assert "onclick" not in next(element for element in root.iter() if element.tag.endswith("rect")).attrib
    assert root.attrib["width"] == "100%"
    assert root.attrib["height"] == "600"


@pytest.mark.parametrize("source", ["", "not svg", "<svg><script>no drawing</script></svg>"])
def test_sanitizer_rejects_empty_or_nonvisual_svg(source):
    with pytest.raises(ValueError):
        sanitize_blueprint_svg(source)
