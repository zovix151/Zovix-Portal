import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from plan_catalog import GLOBAL_PLANS


_LOGO_PATH = (
    (120, 143),
    (392, 143),
    (392, 204),
    (204, 339),
    (392, 339),
    (392, 404),
    (120, 404),
    (120, 343),
    (308, 208),
    (120, 208),
)
_GRADIENT_STOPS = (
    (0.0, (25, 213, 207)),
    (0.55, (71, 121, 242)),
    (1.0, (128, 84, 237)),
)


def should_apply_free_watermark(subscription_active, subscription_pack):
    pack_name = str(subscription_pack or "").strip().casefold()
    paid_plan_names = (
        str(plan["name"]).casefold()
        for plan in GLOBAL_PLANS["subscriptions"].values()
        if plan.get("price", 0) > 0
    )
    return not (
        subscription_active
        and any(plan_name in pack_name for plan_name in paid_plan_names)
    )


def _interpolate_gradient(progress):
    for (start, start_color), (end, end_color) in zip(
        _GRADIENT_STOPS, _GRADIENT_STOPS[1:]
    ):
        if progress <= end:
            ratio = (progress - start) / (end - start)
            return tuple(
                round(first + (second - first) * ratio)
                for first, second in zip(start_color, end_color)
            )
    return _GRADIENT_STOPS[-1][1]


def _create_logo_mark(size):
    mark = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(mark)
    draw.rounded_rectangle(
        (0, 0, size - 1, size - 1),
        radius=round(size * 0.26),
        fill=(16, 40, 75, 190),
    )

    scale = size / 512
    logo_mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(logo_mask)
    mask_draw.polygon(
        [(round(x * scale), round(y * scale)) for x, y in _LOGO_PATH],
        fill=235,
    )
    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    for x in range(size):
        color = _interpolate_gradient(x / max(1, size - 1))
        gradient_draw.line((x, 0, x, size - 1), fill=(*color, 235))
    gradient.putalpha(logo_mask)
    mark.alpha_composite(gradient)

    dot_center = (round(387 * scale), round(124 * scale))
    dot_radius = round(26 * scale)
    draw.ellipse(
        (
            dot_center[0] - dot_radius,
            dot_center[1] - dot_radius,
            dot_center[0] + dot_radius,
            dot_center[1] + dot_radius,
        ),
        fill=(255, 255, 255, 235),
    )
    return mark


def _svg_dimensions(root):
    view_box = root.attrib.get("viewBox", "")
    values = re.split(r"[\s,]+", view_box.strip()) if view_box.strip() else []
    if len(values) == 4:
        min_x, min_y, width, height = (float(value) for value in values)
        if width > 0 and height > 0:
            return min_x, min_y, width, height

    dimensions = []
    for attribute in ("width", "height"):
        match = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)", root.attrib.get(attribute, ""))
        dimensions.append(float(match.group(1)) if match else 1000.0)
    return 0.0, 0.0, dimensions[0], dimensions[1]


def _watermark_svg(source_path, output_path):
    tree = ET.parse(source_path)
    root = tree.getroot()
    if root.tag.split("}")[-1] != "svg":
        raise ValueError("Blueprint output is not an SVG document.")

    namespace = root.tag[1:].split("}", 1)[0] if root.tag.startswith("{") else ""
    if namespace:
        ET.register_namespace("", namespace)
    tag = lambda name: f"{{{namespace}}}{name}" if namespace else name

    min_x, min_y, width, height = _svg_dimensions(root)
    logo_size = min(112.0, max(48.0, min(width, height) * 0.095))
    margin = max(12.0, min(width, height) * 0.02)
    scale = logo_size / 512
    existing_ids = {element.attrib.get("id") for element in root.iter()}
    gradient_id = "zovix-watermark-gradient"
    suffix = 2
    while gradient_id in existing_ids:
        gradient_id = f"zovix-watermark-gradient-{suffix}"
        suffix += 1

    defs = ET.SubElement(root, tag("defs"))
    gradient = ET.SubElement(
        defs,
        tag("linearGradient"),
        {
            "id": gradient_id,
            "x1": "52",
            "y1": "46",
            "x2": "462",
            "y2": "466",
            "gradientUnits": "userSpaceOnUse",
        },
    )
    for offset, color in (("0", "#19d5cf"), (".55", "#4779f2"), ("1", "#8054ed")):
        ET.SubElement(
            gradient,
            tag("stop"),
            {"offset": offset, "stop-color": color},
        )

    group = ET.SubElement(
        root,
        tag("g"),
        {
            "transform": (
                f"translate({min_x + width - logo_size - margin:.2f} "
                f"{min_y + height - logo_size - margin:.2f}) scale({scale:.5f})"
            ),
            "opacity": "0.78",
            "aria-label": "ZOVIX watermark",
        },
    )
    ET.SubElement(
        group,
        tag("rect"),
        {"x": "20", "y": "20", "width": "472", "height": "472", "rx": "132", "fill": "#10284b"},
    )
    ET.SubElement(
        group,
        tag("path"),
        {
            "d": "M120 143h272v61L204 339h188v65H120v-61l188-135H120z",
            "fill": f"url(#{gradient_id})",
        },
    )
    ET.SubElement(
        group,
        tag("circle"),
        {"cx": "387", "cy": "124", "r": "26", "fill": "#fff"},
    )
    tree.write(output_path, encoding="unicode", xml_declaration=False)


def apply_zovix_watermark(image_path):
    source_path = Path(image_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Generated image does not exist: {source_path}")
    if source_path.stem.endswith("_watermarked"):
        return str(source_path)

    output_path = source_path.with_name(
        f"{source_path.stem}_watermarked{source_path.suffix or '.png'}"
    )
    if source_path.suffix.lower() == ".svg":
        _watermark_svg(source_path, output_path)
        return str(output_path)

    with Image.open(source_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
        width, height = image.size
        logo_size = min(112, max(48, int(min(width, height) * 0.095)))
        margin = max(12, int(min(width, height) * 0.02))
        image.alpha_composite(
            _create_logo_mark(logo_size),
            (width - logo_size - margin, height - logo_size - margin),
        )
        image_format = source.format or "PNG"
        if image_format in {"JPEG", "JPG"}:
            image = image.convert("RGB")
        image.save(output_path, format=image_format)

    return str(output_path)
