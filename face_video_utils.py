"""Pure helpers for face-video voice defaults and aspect-ratio sizing."""


_DEFAULT_VOICE_IDS = {
    "male": "pNInz6obpgDQ5IdwJg7p",
    "female": "21m00Tcm4TlvDq8ikWAM",
}

_ASPECT_RATIOS = {
    "9:16": (9, 16),
    "16:9": (16, 9),
    "1:1": (1, 1),
}


def default_elevenlabs_voice_id_for_gender(gender):
    normalized_gender = str(gender or "").strip().lower()
    if normalized_gender in {"female", "woman", "girl", "f", "feminine"}:
        return _DEFAULT_VOICE_IDS["female"]
    return _DEFAULT_VOICE_IDS["male"]


def face_video_dimensions(long_edge, aspect_ratio):
    try:
        long_edge = int(long_edge)
    except (TypeError, ValueError) as exc:
        raise ValueError("Face-video dimensions require a positive integer edge.") from exc
    if long_edge < 2:
        raise ValueError("Face-video dimensions require an edge of at least two pixels.")

    try:
        ratio_width, ratio_height = _ASPECT_RATIOS[aspect_ratio]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Unsupported face video aspect ratio: {aspect_ratio}") from exc

    if ratio_width < ratio_height:
        width = round(long_edge * ratio_width / ratio_height)
        height = long_edge
    elif ratio_width > ratio_height:
        width = long_edge
        height = round(long_edge * ratio_height / ratio_width)
    else:
        width = height = long_edge

    return max(2, width // 2 * 2), max(2, height // 2 * 2)
