import re
import xml.etree.ElementTree as ET


_SVG_NAMESPACE = "http://www.w3.org/2000/svg"
_ALLOWED_ELEMENTS = {
    "svg",
    "g",
    "defs",
    "linearGradient",
    "radialGradient",
    "stop",
    "rect",
    "path",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "text",
    "tspan",
    "title",
    "desc",
    "clipPath",
    "marker",
}
_ALLOWED_ATTRIBUTES = {
    "id",
    "width",
    "height",
    "viewBox",
    "preserveAspectRatio",
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "d",
    "points",
    "fill",
    "fill-rule",
    "fill-opacity",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-dasharray",
    "stroke-dashoffset",
    "stroke-opacity",
    "opacity",
    "transform",
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "text-anchor",
    "dominant-baseline",
    "letter-spacing",
    "textLength",
    "lengthAdjust",
    "dx",
    "dy",
    "rotate",
    "offset",
    "stop-color",
    "stop-opacity",
    "gradientUnits",
    "gradientTransform",
    "spreadMethod",
    "clipPathUnits",
    "markerUnits",
    "markerWidth",
    "markerHeight",
    "refX",
    "refY",
    "orient",
    "marker-start",
    "marker-mid",
    "marker-end",
    "clip-path",
    "mask",
    "style",
}
_ALLOWED_STYLE_PROPERTIES = {
    "fill",
    "fill-rule",
    "fill-opacity",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-dasharray",
    "stroke-dashoffset",
    "stroke-opacity",
    "opacity",
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "text-anchor",
    "dominant-baseline",
    "letter-spacing",
}
ET.register_namespace("", _SVG_NAMESPACE)


def _local_name(tag):
    return tag.rsplit("}", 1)[-1]


def _safe_svg_value(value):
    if re.search(r"url\((?!\s*['\"]?#[-\w:.]+['\"]?\s*\))", value, flags=re.IGNORECASE):
        return False
    return not re.search(r"(?:javascript|data|https?|file):", value, flags=re.IGNORECASE)


def _sanitize_style(value):
    declarations = []
    for declaration in value.split(";"):
        property_name, separator, property_value = declaration.partition(":")
        property_name = property_name.strip().lower()
        property_value = property_value.strip()
        if (
            separator
            and property_name in _ALLOWED_STYLE_PROPERTIES
            and _safe_svg_value(property_value)
        ):
            declarations.append(f"{property_name}:{property_value}")
    return ";".join(declarations)


def _view_box(root):
    value = root.attrib.get("viewBox", "")
    parts = re.split(r"[\s,]+", value.strip()) if value.strip() else []
    if len(parts) == 4:
        try:
            min_x, min_y, width, height = (float(part) for part in parts)
        except ValueError:
            min_x = min_y = width = height = 0
        if width > 0 and height > 0:
            return f"{min_x:g} {min_y:g} {width:g} {height:g}"

    dimensions = []
    for name in ("width", "height"):
        match = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)", root.attrib.get(name, ""))
        dimensions.append(float(match.group(1)) if match else 1400.0)
    return f"0 0 {dimensions[0]:g} {dimensions[1]:g}"


def sanitize_blueprint_svg(svg_code):
    if not isinstance(svg_code, str) or not svg_code.strip():
        raise ValueError("Blueprint generator returned empty SVG output.")
    if len(svg_code) > 1_500_000:
        raise ValueError("Blueprint SVG output is too large to render safely.")

    try:
        root = ET.fromstring(svg_code)
    except ET.ParseError as exc:
        raise ValueError("Blueprint generator returned invalid SVG markup.") from exc
    if _local_name(root.tag) != "svg":
        raise ValueError("Blueprint generator did not return an SVG document.")

    def sanitize_element(element):
        for attribute in list(element.attrib):
            name = _local_name(attribute)
            value = element.attrib[attribute]
            if name not in _ALLOWED_ATTRIBUTES:
                del element.attrib[attribute]
            elif name == "style":
                sanitized_style = _sanitize_style(value)
                if sanitized_style:
                    element.attrib[attribute] = sanitized_style
                else:
                    del element.attrib[attribute]
            elif not _safe_svg_value(value):
                del element.attrib[attribute]

        for child in list(element):
            if _local_name(child.tag) not in _ALLOWED_ELEMENTS:
                element.remove(child)
            else:
                sanitize_element(child)

    sanitize_element(root)
    has_drawing = any(
        _local_name(element.tag)
        in {"rect", "path", "circle", "ellipse", "line", "polyline", "polygon", "text"}
        for element in root.iter()
    )
    if not has_drawing:
        raise ValueError("Blueprint SVG did not contain any drawable content.")

    if not root.tag.startswith("{"):
        root.set("xmlns", _SVG_NAMESPACE)
    root.set("viewBox", _view_box(root))
    root.set("width", "100%")
    root.set("height", "600")
    root.set("preserveAspectRatio", "xMidYMid meet")
    return ET.tostring(root, encoding="unicode")
