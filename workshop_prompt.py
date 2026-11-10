"""Prompt guidance for Creative Workshop image generation."""


WORKSHOP_ENHANCEMENT_SYSTEM_PROMPT = (
    "Rewrite the user's image idea as a clear image-generation prompt. Preserve all "
    "explicit details, relationships, colors, materials, objects, text, negations, "
    "and the requested visual style, including intentional damage or surrealism. "
    "Do not replace, omit, contradict, or invent specified elements. Improve the "
    "clarity of spatial layout, coherent perspective, object placement, lighting, "
    "and texture only when compatible with the user's intent. Respect the negative "
    "constraints. Return only the finished prompt, without explanation or quotes."
)

_ENVIRONMENT_GUIDANCE = (
    "Render the requested environment clearly with coherent spatial layout, "
    "consistent perspective, connected geometry, stable object proportions, and "
    "lighting and shadows appropriate to the scene. Preserve the requested style, "
    "all specified details, and any intentional damage, irregularity, or surrealism; "
    "do not add unrelated objects or alter the requested setting."
)


def build_workshop_prompt(original_prompt: str, enhanced_prompt: str | None = None) -> str:
    if not isinstance(original_prompt, str) or not original_prompt.strip():
        raise ValueError("Creative Workshop prompt must not be empty.")
    original = original_prompt.strip()
    enhanced = enhanced_prompt.strip() if enhanced_prompt else ""
    sections = [f"Original image request:\n{original}"]
    if enhanced and enhanced != original:
        sections.append(
            "Additional visual direction (preserve the original request if anything conflicts):\n"
            f"{enhanced}"
        )
    sections.append(_ENVIRONMENT_GUIDANCE)
    return "\n\n".join(sections)
