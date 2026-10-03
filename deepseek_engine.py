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


def _build_sales_script_prompt(product_name, price, category, language, tone, extra_instructions, personal_experience=""):
    return f"""Return ONLY valid JSON. Create exactly three sales-script variations for this product.
Product: {product_name}
Price: {price or 'not provided'}
Language: {language}
Internal style guidance only (never say this in the script): {tone}
Extra instructions: {extra_instructions or 'none'}
Creator's real product experience: {personal_experience or 'none provided'}

The JSON must have this exact shape:
{{"scripts":[{{"script":"...","tone":"urgency","cta":"..."}},{{"script":"...","tone":"social_proof","cta":"..."}},{{"script":"...","tone":"emotional","cta":"..."}}]}}

Write each script as spoken dialogue from one friendly, believable human presenter talking to a friend. Use informal, relaxed, everyday language; avoid formal or corporate wording. For Hindi or Hinglish, make it sound like natural spoken Hindustani/Hinglish, like a friend explaining something to a friend, not a narrator reading an ad. Use short varied sentences and natural transitions, and do not translate English marketing phrases literally. Add only one or two light, language-appropriate fillers per script, such as "dekho", "umm", or "actually" for Hindi/Hinglish. At most one small natural restart or hesitation; do not force repeated stutters or make the speaker sound unintelligible. Keep the requested tone only as a subtle flavor, never at the cost of the casual human voice.
The category/tone is internal writing guidance only. Never announce, explain, or name the product category in the spoken script or CTA. Do not say what category the product belongs to or use category labels in either language. Talk naturally about the product itself instead.
If a real product experience is supplied above, include one brief first-person anecdote using only those exact facts; do not embellish its duration, occasion, results, or feelings. If none is supplied, do not claim that the presenter bought, owns, used, or personally recommends the product, and do not invent a personal/family story. Instead, use a relatable everyday scenario framed honestly (for example, "socho" / "maan lo"), not as something that actually happened.
Give the three scripts distinct angles:
1. urgency: a gentle invitation to take the next step, with no pressure or invented deadline/scarcity.
2. social_proof: earn trust through clear, practical, transparent wording; never imply popularity, reviews, or customer experience that was not provided.
3. emotional: connect the product to a believable everyday need without melodrama or unsupported claims.
Mention only product facts supplied above or in the extra instructions. Do not invent features, specifications, performance, materials, origin, certifications, reviews, discounts, guarantees, deadlines, scarcity, health benefits, or statistics. If details are limited, be honest and focus on the product name, category, price, and a reasonable use case without pretending to know more.
Avoid robotic openings such as "Introducing our", "Look no further", or "Revolutionize your"; avoid slogans, hard-sell language, repeated exclamation marks, headings, bullet points, emojis, and stage directions. Each script must be concise, no more than 120 words, and end with a clear, conversational spoken CTA. The cta field must match that invitation. Use the requested language throughout."""


def generate_sales_script(product_name, price="", category="Other", language="English", extra_instructions="", personal_experience=""):
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
    prompt = _build_sales_script_prompt(
        product_name, price, category, language, tone, extra_instructions, personal_experience
    )

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
