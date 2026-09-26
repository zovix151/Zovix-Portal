"""Sales funnel content helpers for AI Sales videos."""

from __future__ import annotations

import re
from typing import Dict


def _clean_text(value: str) -> str:
    return " ".join(str(value or "").split())


def _normalise_price(value: str) -> str:
    text = _clean_text(value)
    return text if text else "Best Value"


def _hashtags(product_name: str, category: str = "") -> str:
    words = []
    for part in [product_name, category]:
        cleaned = _clean_text(part)
        if cleaned:
            words.append(cleaned)
    base = ["#AIProduct", "#SmartShopping", "#TechDeals"]
    if not words:
        return " ".join(base)
    transformed = []
    for word in words:
        token = re.sub(r"[^a-zA-Z0-9]+", "", word)
        if token:
            transformed.append("#" + token[:18])
    if len(transformed) >= 3:
        return " ".join(transformed[:3] + base[:2])
    return " ".join(transformed + base[:max(0, 3 - len(transformed))])


def build_sales_funnel(product_name: str, price: str = "", category: str = "General",
                      script: str = "", language: str = "English", tone: str = "Professional") -> Dict[str, str]:
    """Create caption, hashtags, product description, and email draft for a sales video."""
    clean_name = _clean_text(product_name) or "Premium Product"
    clean_price = _normalise_price(price)
    clean_category = _clean_text(category) or "General"
    clean_script = _clean_text(script) or "Experience premium quality and value built for everyday convenience."
    clean_tone = _clean_text(tone) or "Professional"

    caption = (
        f"{clean_name} is here to upgrade your everyday routine. "
        f"Made for {clean_category.lower()} lovers who want quality, convenience, and style. "
        f"Starting at {clean_price}. {clean_script[:180]}"
    )

    hashtags = _hashtags(clean_name, clean_category)

    description = (
        f"Introducing {clean_name}, a premium {clean_category.lower()} product designed to deliver everyday value and elevated performance. "
        f"Built with smart design and reliable quality, it helps customers enjoy a smoother, more enjoyable experience. "
        f"Available now at {clean_price}."
    )

    email = (
        f"Subject: {clean_name} is live now\n\n"
        f"Hi there,\n\n"
        f"We are excited to introduce {clean_name}, a standout {clean_category.lower()} product built for modern customers. "
        f"It combines premium quality, smart performance, and everyday value, making it a smart addition to any routine.\n\n"
        f"Now available at {clean_price}.\n\n"
        f"{clean_script}\n\n"
        f"Thank you for your attention."
    )

    whatsapp = (
        f"Hi! Check out {clean_name}, a premium {clean_category.lower()} product available at {clean_price}. "
        f"{clean_script[:220]} "
        "Reply here if you want the details or would like to order."
    )

    return {
        "caption": caption,
        "hashtags": hashtags,
        "description": description,
        "email": email,
        "whatsapp": whatsapp,
        "language": language,
        "tone": clean_tone,
    }
