DRAW_DEFAULT_NEGATIVE_PROMPT = (
    "blurry or out of focus image, low resolution, pixelation, compression artifacts, "
    "distorted anatomy, extra or missing limbs or fingers, malformed hands or faces, "
    "duplicated subjects, cropped-off main subject, cluttered composition, inconsistent "
    "lighting, incorrect perspective, overexposure, underexposure, unrequested text, "
    "gibberish lettering, unintended logos, watermarks, signatures, borders, frames"
)

WORKSHOP_DEFAULT_NEGATIVE_PROMPT = (
    "blurry or out of focus image, low resolution, pixelation, compression artifacts, "
    "malformed anatomy, distorted hands or faces, duplicated subjects, missing requested "
    "elements, extra unrelated objects, cropped-off main subject, cluttered composition, "
    "inconsistent lighting or shadows, incorrect perspective, overexposure, underexposure, "
    "unrequested text, gibberish lettering, unintended logos, watermarks, signatures, borders, frames"
)


def combine_negative_prompts(user_prompt, default_prompt):
    combined = []
    seen = set()
    for prompt in (default_prompt, user_prompt):
        for clause in str(prompt or "").split(","):
            cleaned = " ".join(clause.split())
            key = cleaned.casefold()
            if cleaned and key not in seen:
                combined.append(cleaned)
                seen.add(key)
    return ", ".join(combined)
