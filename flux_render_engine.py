"""Layer 2 of the ZOVIX Ghost Engine: Flux keyframe and relative depth map."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

import io
import logging
import os
import time
import uuid
import requests
import streamlit as st
from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError
from streamlit.errors import StreamlitSecretNotFoundError


logger = logging.getLogger(__name__)

_FLUX_MODEL = "black-forest-labs/flux-1.1-pro"
_FLUX_FALLBACK_MODEL = "black-forest-labs/flux-schnell"
_DEPTH_MODEL = "chenxwh/depth-anything-v2"
_TARGET_SIZE = (7680, 4320)
_I2V_KEYFRAME_SIZE = (1536, 864)
_PREDICTION_TIMEOUT_SECONDS = 600
_POLL_INTERVAL_SECONDS = 0.5
_RATE_LIMIT_RETRIES = 3
_RATE_LIMIT_RETRY_DELAY_SECONDS = 4
_OUTPUT_ROOT = Path(__file__).resolve().parent / "static" / "outputs"


class _ReplicateHTTPError(RuntimeError):
    """Replicate returned a non-success HTTP status."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


class _ReplicateRateLimitError(_ReplicateHTTPError):
    """Replicate rejected a request with HTTP 429 after bounded retries."""

    def __init__(self, model_ref: str):
        super().__init__(
            429,
            f"Replicate rate-limited model {model_ref} after "
            f"{_RATE_LIMIT_RETRIES + 1} attempts.",
        )


class _ReplicateSubmissionError(_ReplicateHTTPError):
    """A model's initial prediction submission was rejected."""


def _get_replicate_token() -> str:
    for name in ("REPLICATE_API_TOKEN", "REPLICATE_API_KEY"):
        token = os.getenv(name, "").strip()
        if token:
            return token
        try:
            token = st.secrets.get(name, "")
        except (KeyError, StreamlitSecretNotFoundError):
            token = ""
        if token:
            return str(token).strip()
    return ""


def _parse_prediction_response(response: requests.Response, model_ref: str) -> dict:
    if response.status_code == 429:
        raise _ReplicateRateLimitError(model_ref)
    if response.status_code not in {200, 201, 202}:
        logger.error(
            "Replicate model %s returned HTTP %s.", model_ref, response.status_code
        )
        raise _ReplicateHTTPError(
            response.status_code,
            f"Replicate model {model_ref} returned HTTP {response.status_code}: "
            f"{response.text[:500]}",
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Replicate model {model_ref} returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Replicate model {model_ref} returned an invalid response.")
    return payload


def _request_with_rate_limit_retry(
    method: str,
    url: str,
    *,
    model_ref: str,
    **kwargs,
) -> requests.Response:
    """Retry rate-limited Replicate requests without retrying accepted jobs."""
    request = requests.post if method == "POST" else requests.get
    for attempt in range(_RATE_LIMIT_RETRIES + 1):
        try:
            response = request(url, **kwargs)
        except requests.RequestException as exc:
            logger.exception("Replicate %s request failed for %s.", method, model_ref)
            raise RuntimeError(
                f"Replicate {method} request failed for model {model_ref}."
            ) from exc

        if response.status_code != 429:
            return response
        if attempt == _RATE_LIMIT_RETRIES:
            raise _ReplicateRateLimitError(
                model_ref
            )
        logger.warning(
            "Replicate rate-limited model %s (attempt %d/%d); retrying in %d seconds.",
            model_ref,
            attempt + 1,
            _RATE_LIMIT_RETRIES + 1,
            _RATE_LIMIT_RETRY_DELAY_SECONDS,
        )
        time.sleep(_RATE_LIMIT_RETRY_DELAY_SECONDS)

    raise AssertionError("Rate-limit retry loop exited unexpectedly.")


def _run_replicate_model(model_ref: str, model_input: dict, token: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    endpoint = f"https://api.replicate.com/v1/models/{model_ref}/predictions"
    logger.info("Submitting Replicate prediction for %s.", model_ref)
    try:
        response = _request_with_rate_limit_retry(
            "POST",
            endpoint,
            model_ref=model_ref,
            headers=headers,
            json={"input": model_input},
            timeout=60,
        )
        prediction = _parse_prediction_response(response, model_ref)
    except _ReplicateHTTPError as exc:
        raise _ReplicateSubmissionError(exc.status_code, str(exc)) from exc
    deadline = time.monotonic() + _PREDICTION_TIMEOUT_SECONDS

    while True:
        status = str(prediction.get("status", "")).lower()
        if status == "succeeded":
            return prediction.get("output")
        if status in {"failed", "canceled", "cancelled"}:
            message = prediction.get("error") or "No error details were provided."
            logger.error("Replicate model %s %s: %s", model_ref, status, message)
            raise RuntimeError(f"Replicate model {model_ref} {status}: {message}")
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Replicate model {model_ref} did not finish within "
                f"{_PREDICTION_TIMEOUT_SECONDS} seconds."
            )

        get_url = (prediction.get("urls") or {}).get("get")
        if not isinstance(get_url, str) or not get_url.startswith("https://"):
            raise RuntimeError(
                f"Replicate model {model_ref} returned no valid prediction status URL."
            )
        time.sleep(_POLL_INTERVAL_SECONDS)
        status_response = _request_with_rate_limit_retry(
            "GET",
            get_url,
            model_ref=model_ref,
            headers=headers,
            timeout=30,
        )
        prediction = _parse_prediction_response(status_response, model_ref)


def _find_output_url(output, preferred_keys=()):
    if isinstance(output, str) and output.startswith(("https://", "http://")):
        return output
    if isinstance(output, dict):
        for key in preferred_keys:
            found = _find_output_url(output.get(key), preferred_keys)
            if found:
                return found
        for value in output.values():
            found = _find_output_url(value, preferred_keys)
            if found:
                return found
    if isinstance(output, (list, tuple)):
        for item in output:
            found = _find_output_url(item, preferred_keys)
            if found:
                return found
    return None


def _download_image(image_url: str, description: str) -> Image.Image:
    response = None
    for attempt in range(4):
        try:
            response = requests.get(image_url, timeout=120)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < 3:
                    retry_after = response.headers.get("Retry-After", "")
                    try:
                        delay = max(1, min(30, int(float(retry_after))))
                    except (TypeError, ValueError):
                        delay = min(20, _RATE_LIMIT_RETRY_DELAY_SECONDS * (2 ** attempt))
                    time.sleep(delay)
                    continue
            response.raise_for_status()
            break
        except requests.RequestException as exc:
            if attempt == 3:
                logger.exception("Could not download the %s.", description)
                raise RuntimeError(f"Could not download the {description} after retries.") from exc
            time.sleep(min(20, _RATE_LIMIT_RETRY_DELAY_SECONDS * (2 ** attempt)))
    if response is None:
        raise RuntimeError(f"Could not download the {description}.")

    try:
        with Image.open(io.BytesIO(response.content)) as image:
            image.load()
            return image.copy()
    except (UnidentifiedImageError, OSError) as exc:
        raise RuntimeError(f"Replicate returned an invalid {description} image.") from exc


def _resize_to_8k(image: Image.Image, mode: str) -> Image.Image:
    converted = image.convert(mode)
    return ImageOps.fit(
        converted,
        _TARGET_SIZE,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def _estimate_local_depth(image: Image.Image) -> Image.Image:
    """Build a deterministic grayscale depth approximation without a model."""
    grayscale = ImageOps.grayscale(image)
    normalized = ImageOps.autocontrast(grayscale, cutoff=1)
    vertical_prior = Image.linear_gradient("L").resize(
        normalized.size,
        resample=Image.Resampling.BILINEAR,
    )
    depth = Image.blend(normalized, vertical_prior, 0.15)
    return depth.filter(ImageFilter.GaussianBlur(radius=0.6))


def generate_flux_keyframe(config_dict: dict) -> str:
    """Generate a 16:9 keyframe sized for the direct image-to-video input."""
    if not isinstance(config_dict, dict):
        raise TypeError("config_dict must be a dictionary.")
    flux_prompt = config_dict.get("flux_prompt")
    if not isinstance(flux_prompt, str) or not flux_prompt.strip():
        raise ValueError("config_dict must contain a non-empty flux_prompt string.")
    token = _get_replicate_token()
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN or REPLICATE_API_KEY must be configured.")

    flux_input = {"prompt": flux_prompt.strip(), "aspect_ratio": "16:9", "output_format": "png"}
    try:
        flux_output = _run_replicate_model(_FLUX_MODEL, flux_input, token)
    except _ReplicateSubmissionError as exc:
        if exc.status_code not in {402, 429}:
            raise
        logger.warning("Flux Pro unavailable; trying fallback image model %s.", _FLUX_FALLBACK_MODEL)
        flux_output = _run_replicate_model(_FLUX_FALLBACK_MODEL, flux_input, token)
    keyframe_url = _find_output_url(flux_output, ("image", "images", "output", "url"))
    if not keyframe_url:
        raise RuntimeError("Flux image model completed without returning a keyframe URL.")

    source_image = _download_image(keyframe_url, "Flux keyframe").convert("RGB")
    keyframe = ImageOps.fit(
        source_image,
        _I2V_KEYFRAME_SIZE,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    _OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    output_path = _OUTPUT_ROOT / f"keyframe_{uuid.uuid4().hex[:10]}.png"
    temporary_path = output_path.with_name(f".{output_path.name}.tmp.png")
    try:
        keyframe.save(temporary_path, format="PNG", compress_level=4)
        temporary_path.replace(output_path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise
    logger.info(
        "Flux I2V keyframe saved at %dx%d to %s.",
        *_I2V_KEYFRAME_SIZE,
        output_path,
    )
    return str(output_path)


def generate_flux_keyframe_and_depth(config_dict: dict) -> tuple[str, str]:
    """Render a Flux keyframe and aligned 8K relative-depth PNG.

    Flux supplies the image at its supported native size. Replicate depth
    estimation is preferred; if it fails, a local grayscale approximation is
    resized alongside the keyframe to 7680x4320.
    """
    if not isinstance(config_dict, dict):
        raise TypeError("config_dict must be a dictionary.")
    flux_prompt = config_dict.get("flux_prompt")
    if not isinstance(flux_prompt, str) or not flux_prompt.strip():
        raise ValueError("config_dict must contain a non-empty flux_prompt string.")

    token = _get_replicate_token()
    if not token:
        raise RuntimeError(
            "REPLICATE_API_TOKEN or REPLICATE_API_KEY must be configured in the "
            "environment or Streamlit secrets."
        )

    logger.info("Starting ZOVIX Ghost Engine Layer 2 render.")
    flux_input = {
        "prompt": flux_prompt.strip(),
        "aspect_ratio": "16:9",
        "output_format": "png",
    }
    try:
        flux_output = _run_replicate_model(_FLUX_MODEL, flux_input, token)
    except _ReplicateSubmissionError as exc:
        if exc.status_code not in {402, 429}:
            raise
        reason = "rate-limited after retries" if exc.status_code == 429 else "rejected for insufficient funds"
        logger.warning(
            "Flux Pro request was %s; trying lower-cost fallback model %s.",
            reason,
            _FLUX_FALLBACK_MODEL,
        )
        flux_output = _run_replicate_model(_FLUX_FALLBACK_MODEL, flux_input, token)
    keyframe_url = _find_output_url(flux_output, ("image", "images", "output", "url"))
    if not keyframe_url:
        raise RuntimeError("Flux image model completed without returning a keyframe image URL.")

    keyframe_source = _download_image(keyframe_url, "Flux keyframe")
    keyframe = _resize_to_8k(keyframe_source, "RGB")
    try:
        depth_output = _run_replicate_model(
            _DEPTH_MODEL,
            {
                "image": keyframe_url,
                "model_size": "Small",
            },
            token,
        )
        depth_url = _find_output_url(
            depth_output,
            ("grey_depth", "depth", "depth_map", "output", "url"),
        )
        if not depth_url:
            raise RuntimeError("Depth model completed without returning a depth map URL.")
        depth_map = _resize_to_8k(_download_image(depth_url, "depth map"), "L")
    except Exception as exc:
        logger.warning(
            "Replicate depth estimation failed (%s); using local grayscale depth fallback.",
            exc,
        )
        depth_map = _resize_to_8k(_estimate_local_depth(keyframe_source), "L")

    if keyframe.size != depth_map.size:
        raise RuntimeError(
            f"Layer 2 keyframe/depth dimensions do not match: "
            f"{keyframe.size} != {depth_map.size}."
        )

    _OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    output_id = uuid.uuid4().hex
    temporary_dir = _OUTPUT_ROOT / f".{output_id}.tmp"
    output_dir = _OUTPUT_ROOT / output_id
    temporary_dir.mkdir()
    try:
        keyframe_path = temporary_dir / "keyframe.png"
        depth_path = temporary_dir / "depth.png"
        keyframe.save(keyframe_path, format="PNG", compress_level=4)
        depth_map.save(depth_path, format="PNG", compress_level=4)
        temporary_dir.rename(output_dir)
    except OSError:
        for path in temporary_dir.glob("*"):
            path.unlink(missing_ok=True)
        temporary_dir.rmdir()
        raise

    final_paths = (str(output_dir / "keyframe.png"), str(output_dir / "depth.png"))
    logger.info("Layer 2 render completed; files saved under %s.", output_dir)
    return final_paths
