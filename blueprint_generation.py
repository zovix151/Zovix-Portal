import json

import requests


_DEFAULT_NEGATIVE_PROMPT = (
    "extra rooms or components not requested, changed counts or dimensions, "
    "duplicated labels, unreadable text, unrelated objects, logos, watermarks, signatures"
)


def _enhance_blueprint_prompt_gpt4o(
    prompt,
    blueprint_type,
    style,
    render_mode,
    quality,
    template_context,
    api_key,
):
    if not str(api_key or "").strip():
        raise RuntimeError("OPENAI_API_KEY is not configured for GPT-4o blueprint planning.")

    user_message = (
        f"Blueprint type: {blueprint_type}\n"
        f"Style: {style}\n"
        f"View: {render_mode}\n"
        f"Quality: {quality}\n"
        f"User's exact brief (highest priority):\n{str(prompt or '').strip()}\n\n"
        f"Optional template reference (secondary only):\n{str(template_context or '').strip() or 'None'}"
    )
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a blueprint prompt engineer preparing image-generation instructions for "
                        "Replicate Flux. Read the complete user brief and preserve every explicitly requested "
                        "room, component, count, dimension, layout relationship, and label. Never add, remove, "
                        "or substitute requested items. Adapt the description to the selected blueprint type, "
                        "style, view, and quality. Ask for clear technical linework, a coherent layout, legible "
                        "short labels, and useful dimension annotations. Do not turn a technical plan into a "
                        "photograph, moodboard, or unrelated scene. Return only a JSON object with string fields "
                        '"prompt" and "negative_prompt".'
                    ),
                },
                {"role": "user", "content": user_message},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 1200,
        },
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"GPT-4o blueprint planning returned HTTP {response.status_code}: "
            f"{response.text[:400]}"
        )

    result = response.json()
    choices = result.get("choices") or []
    content = str((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
    if not content:
        raise RuntimeError("GPT-4o returned no blueprint prompt.")
    try:
        blueprint_plan = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GPT-4o returned invalid blueprint prompt JSON.") from exc

    enhanced_prompt = str(blueprint_plan.get("prompt") or "").strip()
    model_negative_prompt = str(blueprint_plan.get("negative_prompt") or "").strip()
    if not enhanced_prompt:
        raise RuntimeError("GPT-4o returned an empty blueprint prompt.")

    exact_user_brief = str(prompt or "").strip()
    final_prompt = (
        f"{enhanced_prompt}\n\n"
        f"Non-negotiable original user brief: {exact_user_brief}\n"
        f"Blueprint type: {blueprint_type}. Style: {style}. View: {render_mode}."
    )
    template_text = str(template_context or "").strip()
    if template_text:
        final_prompt += f"\nSecondary template reference: {template_text}"

    negative_prompt = ", ".join(
        item
        for item in (model_negative_prompt, _DEFAULT_NEGATIVE_PROMPT)
        if item
    )
    aspect_ratio = "16:9" if str(render_mode).casefold().startswith("3d") else "4:3"
    return final_prompt, negative_prompt, aspect_ratio


def generate_blueprint_image_with_gpt4o(
    prompt,
    blueprint_type,
    style,
    render_mode,
    quality,
    template_context,
    api_key,
    replicate_generator,
):
    exact_prompt = str(prompt or "").strip()
    if not exact_prompt:
        raise ValueError("Enter a blueprint description before generating.")
    quality_name = str(quality or "Standard").strip()
    if quality_name not in {"Standard", "HD"}:
        raise ValueError("Blueprint quality must be Standard or HD.")

    final_prompt, negative_prompt, aspect_ratio = _enhance_blueprint_prompt_gpt4o(
        exact_prompt,
        blueprint_type,
        style,
        render_mode,
        quality_name,
        template_context,
        api_key,
    )
    image_path = replicate_generator(
        final_prompt,
        aspect_ratio,
        negative_prompt,
        quality_name,
    )
    if not image_path:
        raise RuntimeError("Replicate did not return a blueprint image.")
    return image_path
