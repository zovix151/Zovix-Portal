"""Replicate-backed sales copy generation."""

import json
import os
import re


_VARIATION_NAMES = ("urgency", "social_proof", "emotional")
_CATEGORY_TONES = {
    "Luxury": "calm, elegant, premium, and understated",
    "Fitness": "energetic, motivating, and action-focused",
    "Sports": "energetic, motivating, and action-focused",
    "Beauty": "warm, confident, and aspirational",
    "Food & Beverage": "appetizing, friendly, and sensory",
    "Fashion": "stylish, confident, and contemporary",
    "Electronics": "clear, modern, and benefit-focused",
}


def _replicate_token():
    token = os.getenv("REPLICATE_API_TOKEN", "") or os.getenv("REPLICATE_API_KEY", "")
    if not token:
        try:
            import streamlit as st
            token = st.secrets.get("REPLICATE_API_TOKEN", "") or st.secrets.get("REPLICATE_API_KEY", "")
        except Exception:
            token = ""
    return str(token).strip()


def _extract_text(output):
    if isinstance(output, str):
        return output
    if isinstance(output, (list, tuple)):
        return "".join(str(item) for item in output)
    if isinstance(output, dict):
        for key in ("output", "text", "response", "completion"):
            if output.get(key):
                return _extract_text(output[key])
    return str(output or "")


def _parse_json(text):
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text.strip(), flags=re.IGNORECASE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}|\[.*\]", cleaned, flags=re.DOTALL)
        if not match:
            raise ValueError("Replicate returned no JSON sales scripts.")
        return json.loads(match.group(0))


def _normalise_scripts(payload):
    if isinstance(payload, dict):
        candidates = payload.get("scripts") or payload.get("variations") or [payload]
    elif isinstance(payload, list):
        candidates = payload
    else:
        candidates = []

    scripts = []
    for index, item in enumerate(candidates):
        if not isinstance(item, dict):
            continue
        script = " ".join(str(item.get("script", "")).split())
        words = len(script.split())
        if 1 <= words <= 120:
            scripts.append({
                "script": script,
                "tone": str(item.get("tone") or _VARIATION_NAMES[min(index, 2)]),
                "cta": str(item.get("cta") or "Shop now."),
            })
        if len(scripts) == 3:
            break
    if len(scripts) != 3:
        raise ValueError("Replicate scripts must contain exactly 3 variations of no more than 120 words.")
    return scripts


def _is_model_not_found_error(error):
    message = str(error).lower()
    return "404" in message or "not found" in message or "does not exist" in message


def generate_sales_script(product_name, price="", category="Other", language="English", extra_instructions=""):
    """Generate three sales scripts through Replicate, each capped at 120 words.

    Returns a list of JSON-compatible objects with script, tone, and cta keys.
    """
    token = _replicate_token()
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN is not configured.")
    try:
        import replicate
    except ImportError as exc:
        raise RuntimeError("Install the Replicate package before generating sales scripts.") from exc

    model_ref = os.getenv("REPLICATE_SCRIPT_MODEL", "meta/meta-llama-3-70b-instruct").strip()
    fallback_model = os.getenv("REPLICATE_SCRIPT_FALLBACK_MODEL", "deepseek-ai/deepseek-v3").strip()
    model_candidates = []
    for candidate in (model_ref, fallback_model):
        if candidate and candidate not in model_candidates:
            model_candidates.append(candidate)
    tone = _CATEGORY_TONES.get(category, "clear, friendly, persuasive, and suitable for the product")
    prompt = f"""Return ONLY valid JSON. Create exactly three sales-script variations for this product.
Product: {product_name}
Price: {price or 'not provided'}
Category: {category}
Language: {language}
Required category tone: {tone}
Extra instructions: {extra_instructions or 'none'}

The JSON must have this exact shape:
{{"scripts":[{{"script":"...","tone":"urgency","cta":"..."}},{{"script":"...","tone":"social_proof","cta":"..."}},{{"script":"...","tone":"emotional","cta":"..."}}]}}
Create an A/B-testable set with these persuasion angles:
1. urgency: encourage immediate action without inventing a deadline or false scarcity.
2. social_proof: communicate trust and suitability without inventing reviews, customer counts, or statistics.
3. emotional: connect the product to a relatable customer need and outcome.
Use scarcity only when the product details explicitly provide real limited availability. Each script must be no more than 120 words, natural for voiceover, and include a clear CTA. Do not invent certifications, reviews, discounts, guarantees, deadlines, scarcity, or statistics. Use the requested language."""

    client = replicate.Client(api_token=token)
    last_error = None
    for index, candidate in enumerate(model_candidates):
        try:
            output = client.run(candidate, input={
                "prompt": prompt,
                "max_new_tokens": 900,
                "temperature": 0.75,
            })
            return _normalise_scripts(_parse_json(_extract_text(output)))
        except Exception as exc:
            last_error = exc
            is_last_candidate = index == len(model_candidates) - 1
            if is_last_candidate or not _is_model_not_found_error(exc):
                raise
    raise RuntimeError(f"All Replicate script models failed: {last_error}") from last_error
