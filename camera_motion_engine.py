"""Layer 3 of the ZOVIX Ghost Engine: depth-guided camera motion."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

import base64
import json
import logging
import math
import os
import re
import shutil
import subprocess
import time
import uuid

import cv2
import numpy as np
import requests

from spatial_director_engine import (
    _ACTION_PROMPT_ENHANCEMENTS,
    _CAMERA_MOTIONS,
    _CHARACTER_ACTIONS,
)

logger = logging.getLogger(__name__)

_OUTPUT_SIZE = (1280, 720)
_FPS = 24
_DURATION_SECONDS = 5
_MOTION_TYPES = _CAMERA_MOTIONS
_CAMERA_MOTION_PROMPTS = {
    "Static (No Motion)": "Lock the camera completely; no pan, tilt, zoom, roll, or shake.",
    "Dolly Zoom": "Smooth forward dolly-in with subtle counter-zoom, keeping the subject centered.",
    "Dolly In": "Physically move the camera smoothly forward toward the subject.",
    "Dolly Out": "Physically move the camera smoothly backward away from the subject.",
    "Zoom In": "Gradually zoom the lens in while keeping framing centered on the subject.",
    "Pan Left": "Smooth horizontal pan to the left; keep the horizon level.",
    "Pan Right": "Smooth horizontal pan to the right; keep the horizon level.",
    "Tilt Up": "Smoothly tilt the camera upward to reveal the upper scene.",
    "Tilt Down": "Smoothly tilt the camera downward to reveal the foreground.",
    "Orbit Left (360)": (
        "Complete one smooth 360-degree orbit counter-clockwise around the subject; "
        "preserve subject identity, consistent distance, and a stable horizon."
    ),
    "Orbit Right (360)": (
        "Complete one smooth 360-degree orbit clockwise around the subject; "
        "preserve subject identity, consistent distance, and a stable horizon."
    ),
    "Crane Up": "Rise vertically on a smooth crane move, revealing more of the scene.",
    "Crane Down": "Descend vertically on a smooth crane move toward the subject.",
    "Tracking (Subject Follow)": (
        "Track laterally with the moving subject, keeping them consistently framed and in focus."
    ),
    "Tracking (Forward)": (
        "Move the camera forward through the scene toward the subject with smooth parallax."
    ),
    "Handheld Shake (Low)": "Add subtle, controlled handheld camera movement, not distracting jitter.",
    "Handheld Shake (High)": "Add energetic handheld camera shake while keeping the subject readable.",
    "Drone Flyover (Aerial)": (
        "Perform a smooth elevated aerial drone flyover, moving forward and gently gaining height."
    ),
    "Drone Circle": "Make a smooth elevated drone circle around the subject with a wide view.",
    "Dolly Zoom (Hitchcock)": (
        "Perform a Hitchcock dolly zoom: move the camera backward while zooming in, "
        "keeping the subject size nearly constant as the background perspective shifts."
    ),
    "Roll Clockwise": "Slowly roll the camera clockwise around the optical axis.",
    "Roll Counter-Clockwise": "Slowly roll the camera counter-clockwise around the optical axis.",
    "Rack Focus (Push)": "Push the camera forward while shifting focus from foreground to subject.",
    "Rack Focus (Pull)": "Pull the camera back while shifting focus from subject to background.",
    "Point of View (POV)": "Use a natural first-person POV camera moving through the scene.",
    "Bullet Time (Super Slow)": (
        "Create a dramatic super-slow-motion bullet-time move with a smooth sweeping camera arc."
    ),
}
_ACTION_MOTION_PROMPTS = _ACTION_PROMPT_ENHANCEMENTS
_WAN_I2V_MODEL = "wan-video/wan-2.2-i2v-fast"
_DEFAULT_I2V_MODEL = _WAN_I2V_MODEL
_I2V_MODEL = os.getenv("ZOVIX_GHOST_I2V_MODEL", _DEFAULT_I2V_MODEL).strip()
_I2V_VERSION = os.getenv(
    "ZOVIX_GHOST_I2V_VERSION",
    "",
).strip()
_I2V_MAX_DURATION_SECONDS = 5.0
_I2V_POLL_INTERVAL_SECONDS = 0.5
_I2V_TIMEOUT_SECONDS = 180
_ROUTER_I2V_TIMEOUT_SECONDS = 300
_WAN_I2V_DURATION_SECONDS = 5.0
_PORTRAIT_DRIVING_DURATION_SECONDS = _WAN_I2V_DURATION_SECONDS
_DYNAMIC_ACTION_DURATION_SECONDS = _WAN_I2V_DURATION_SECONDS
_I2V_MAX_SUBMISSION_RETRIES = 1
_I2V_RETRY_DELAY_SECONDS = 1
_I2V_MAX_REQUEST_RETRIES = 3
_DEPTH_SMOOTHING_SIGMA_COLOR = 0.08
_EDGE_FEATHER_PIXELS = 10
_OUTPUT_ROOT = Path(__file__).resolve().parent / "static" / "outputs"


def _fit_frame_to_size(frame: np.ndarray, output_size: tuple[int, int]) -> np.ndarray:
    """Center-crop to a target aspect ratio, then resize without stretching."""
    target_width, target_height = output_size
    height, width = frame.shape[:2]
    if height < 1 or width < 1:
        raise ValueError("Video frame has invalid dimensions.")
    target_ratio = target_width / target_height
    source_ratio = width / height
    if source_ratio > target_ratio:
        crop_width = max(1, round(height * target_ratio))
        left = (width - crop_width) // 2
        frame = frame[:, left:left + crop_width]
    elif source_ratio < target_ratio:
        crop_height = max(1, round(width / target_ratio))
        top = (height - crop_height) // 2
        frame = frame[top:top + crop_height, :]
    return cv2.resize(frame, output_size, interpolation=cv2.INTER_AREA)


def _fit_frame_to_output(frame: np.ndarray) -> np.ndarray:
    """Center-crop to the 16:9 master canvas, then resize without stretching."""
    return _fit_frame_to_size(frame, _OUTPUT_SIZE)


def _normalize_i2v_video(
    source: Path,
    output: Path,
    frame_count: int,
    duration_seconds: float,
    source_fps: float,
) -> None:
    """Encode at browser FPS while preserving source timing; reject truncated motion."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to normalize image-to-video output.")
    actual_duration = frame_count / source_fps
    if actual_duration < duration_seconds - (1.0 / source_fps):
        raise RuntimeError(
            f"Image-to-video generated only {actual_duration:.2f}s of motion; "
            f"{duration_seconds:.2f}s is required. Refusing to pad with frozen frames."
        )
    filters = (
        f"fps={_FPS},trim=duration={duration_seconds:.6f},"
        f"scale={_OUTPUT_SIZE[0]}:{_OUTPUT_SIZE[1]}:flags=lanczos,"
        "setsar=1,format=yuv420p"
    )
    result = subprocess.run(
        [
            ffmpeg, "-y", "-i", str(source), "-vf", filters,
            "-an", "-c:v", "libx264", "-profile:v", "main", "-level:v", "4.1",
            "-preset", "veryfast", "-crf", "17", "-r", str(_FPS), "-fps_mode", "cfr",
            "-movflags", "+faststart", str(output),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode or not output.is_file() or output.stat().st_size < 1000:
        raise RuntimeError(f"Could not normalize I2V output: {(result.stderr or '')[-1200:]}")


def _load_inputs(keyframe_path: str, depth_path: str):
    if not isinstance(keyframe_path, str) or not keyframe_path.strip():
        raise ValueError("keyframe_path must be a non-empty path.")
    if not isinstance(depth_path, str) or not depth_path.strip():
        raise ValueError("depth_path must be a non-empty path.")

    keyframe = cv2.imread(keyframe_path, cv2.IMREAD_COLOR)
    if keyframe is None:
        raise ValueError(f"Could not read keyframe image: {keyframe_path}")
    depth = cv2.imread(depth_path, cv2.IMREAD_UNCHANGED)
    if depth is None:
        raise ValueError(f"Could not read depth map image: {depth_path}")
    if depth.ndim == 3:
        depth = cv2.cvtColor(depth, cv2.COLOR_BGR2GRAY)

    image_height, image_width = keyframe.shape[:2]
    depth_height, depth_width = depth.shape[:2]
    image_ratio = image_width / image_height
    depth_ratio = depth_width / depth_height
    if abs(image_ratio - depth_ratio) > 0.02:
        raise ValueError("Keyframe and depth map must have matching aspect ratios.")

    width, height = _OUTPUT_SIZE
    keyframe = cv2.resize(keyframe, (width, height), interpolation=cv2.INTER_AREA)
    depth = cv2.resize(depth, (width, height), interpolation=cv2.INTER_AREA)
    depth = depth.astype(np.float32)
    low, high = np.percentile(depth, (2, 98))
    if not np.isfinite(low) or not np.isfinite(high) or high - low < 1e-6:
        raise ValueError("Depth map has no usable depth variation.")

    near_weight = np.clip((depth - low) / (high - low), 0.0, 1.0)
    near_weight = cv2.bilateralFilter(
        near_weight,
        d=7,
        sigmaColor=_DEPTH_SMOOTHING_SIGMA_COLOR,
        sigmaSpace=3.0,
    )
    return keyframe, near_weight


def _prepare_point_cloud(keyframe: np.ndarray, near_weight: np.ndarray):
    width, height = _OUTPUT_SIZE
    margin_x = round(width * 0.08)
    margin_y = round(height * 0.08)
    padded_frame = cv2.copyMakeBorder(
        keyframe,
        margin_y,
        margin_y,
        margin_x,
        margin_x,
        cv2.BORDER_REFLECT_101,
    )
    padded_depth = cv2.copyMakeBorder(
        near_weight,
        margin_y,
        margin_y,
        margin_x,
        margin_x,
        cv2.BORDER_REFLECT_101,
    )
    source_height, source_width = padded_depth.shape
    center_x = (width - 1) / 2.0
    center_y = (height - 1) / 2.0
    focal_length = width * 0.9
    pixel_x = (
        np.arange(source_width, dtype=np.float32) - margin_x - center_x
    )
    pixel_y = (
        np.arange(source_height, dtype=np.float32) - margin_y - center_y
    )
    depth_z = 1.2 + (1.0 - padded_depth) * 2.8
    world_x = pixel_x[None, :] * depth_z / focal_length
    world_y = pixel_y[:, None] * depth_z / focal_length
    points = (
        world_x.reshape(-1),
        world_y.reshape(-1),
        depth_z.reshape(-1),
        padded_frame.reshape(-1, 3),
    )
    anchor_depth = float(np.median(depth_z[margin_y:-margin_y, margin_x:-margin_x]))
    return points, focal_length, anchor_depth


def _camera_pose(motion_type: str, progress: float, focal_length: float, anchor_depth: float):
    camera_x = 0.0
    camera_y = 0.0
    camera_z = 0.0
    yaw = 0.0
    focal = focal_length

    if motion_type in {"Dolly Zoom", "Dolly Zoom (Hitchcock)"}:
        camera_z = 0.12 * progress
        focal = focal_length * max((anchor_depth - camera_z) / anchor_depth, 0.8)
    elif motion_type == "Dolly In":
        camera_z = 0.18 * progress
    elif motion_type in {"Dolly Out", "Zoom Out"}:
        camera_z = -0.16 * progress
    elif motion_type == "Pan Left":
        camera_x = -0.075 * progress
        yaw = math.radians(-2.5 * progress)
    elif motion_type == "Pan Right":
        camera_x = 0.075 * progress
        yaw = math.radians(2.5 * progress)
    elif motion_type == "Tilt Up":
        camera_y = -0.075 * progress
    elif motion_type == "Tilt Down":
        camera_y = 0.075 * progress
    elif motion_type in {"Orbit Left (360)", "Orbit Right (360)", "Drone Circle"}:
        direction = -1.0 if motion_type == "Orbit Left (360)" else 1.0
        yaw = math.radians(35.0 * progress * direction)
        camera_x = 0.08 * math.sin(progress * math.pi * 2.0) * direction
    elif motion_type in {"Crane Up", "Drone Flyover (Aerial)"}:
        camera_y = -0.13 * progress
        camera_z = 0.08 * progress
    elif motion_type == "Crane Down":
        camera_y = 0.13 * progress
        camera_z = -0.04 * progress
    elif motion_type in {"Tracking (Subject Follow)", "Tracking"}:
        camera_x = 0.06 * math.sin(progress * math.pi) - 0.025 * progress
        yaw = math.radians(-1.5 * progress)
    elif motion_type in {"Tracking (Forward)", "Point of View (POV)"}:
        camera_z = 0.15 * progress
    elif motion_type == "Roll Clockwise":
        yaw = math.radians(5.0 * progress)
    elif motion_type == "Roll Counter-Clockwise":
        yaw = math.radians(-5.0 * progress)
    elif motion_type in {"Rack Focus (Push)", "Rack Focus (Pull)"}:
        direction = 1.0 if motion_type.endswith("(Push)") else -1.0
        camera_z = 0.035 * progress * direction
        focal = focal_length * (1.0 + 0.025 * progress * direction)
    elif motion_type == "Bullet Time (Super Slow)":
        yaw = math.radians(22.0 * progress)
        camera_x = 0.05 * math.sin(progress * math.pi)
    elif motion_type in {"Handheld Shake (Low)", "Handheld Shake (High)"}:
        amplitude = 0.006 if motion_type.endswith("(Low)") else 0.018
        camera_x = amplitude * math.sin(progress * math.pi * 12.0)
        camera_y = amplitude * math.cos(progress * math.pi * 10.0)
    elif motion_type == "Zoom In":
        focal = focal_length * (1.0 + 0.18 * progress)
    elif motion_type == "Static (No Motion)":
        pass

    return camera_x, camera_y, camera_z, yaw, focal


def _fill_reprojection_holes(frame: np.ndarray, holes: np.ndarray) -> np.ndarray:
    """Inpaint disocclusions using reflected edge context and feather seams."""
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Reprojected frame must be a three-channel color image.")
    if holes.shape != frame.shape[:2]:
        raise ValueError("Reprojection hole mask must match the frame dimensions.")

    hole_mask = np.where(holes > 0, 255, 0).astype(np.uint8)
    if not cv2.countNonZero(hole_mask):
        return frame
    if cv2.countNonZero(cv2.bitwise_not(hole_mask)) == 0:
        raise RuntimeError("Camera reprojection left no visible source pixels.")

    padding = _EDGE_FEATHER_PIXELS
    padded_frame = cv2.copyMakeBorder(
        frame, padding, padding, padding, padding, cv2.BORDER_REFLECT_101
    )
    padded_mask = cv2.copyMakeBorder(
        hole_mask,
        padding,
        padding,
        padding,
        padding,
        cv2.BORDER_CONSTANT,
        value=0,
    )
    filled = cv2.inpaint(padded_frame, padded_mask, 5, cv2.INPAINT_TELEA)
    filled = filled[padding:-padding, padding:-padding]

    seam_mask = cv2.dilate(
        hole_mask,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
    )
    edge_width = _EDGE_FEATHER_PIXELS
    seam_mask[:edge_width, :] = 255
    seam_mask[-edge_width:, :] = 255
    seam_mask[:, :edge_width] = 255
    seam_mask[:, -edge_width:] = 255
    feather = cv2.GaussianBlur(seam_mask, (0, 0), sigmaX=2.0).astype(np.float32) / 255.0
    softened = cv2.GaussianBlur(filled, (0, 0), sigmaX=1.1).astype(np.float32)
    result = (
        filled.astype(np.float32) * (1.0 - feather[:, :, None])
        + softened * feather[:, :, None]
    )
    return np.clip(result, 0, 255).astype(np.uint8)


def _reproject_frame(points, pose, output_size: tuple[int, int]) -> np.ndarray:
    width, height = output_size
    world_x, world_y, world_z, colors = points
    camera_x, camera_y, camera_z, yaw, focal = pose
    cosine = math.cos(yaw)
    sine = math.sin(yaw)

    rotated_x = cosine * world_x - sine * world_z
    rotated_z = sine * world_x + cosine * world_z
    view_x = rotated_x - camera_x
    view_y = world_y - camera_y
    view_z = rotated_z - camera_z

    center_x = (width - 1) / 2.0
    center_y = (height - 1) / 2.0
    valid_depth = view_z > 1e-4
    projected_x = np.zeros_like(view_z)
    projected_y = np.zeros_like(view_z)
    projected_x[valid_depth] = (
        focal * view_x[valid_depth] / view_z[valid_depth] + center_x
    )
    projected_y[valid_depth] = (
        focal * view_y[valid_depth] / view_z[valid_depth] + center_y
    )
    pixel_x = np.rint(projected_x).astype(np.int32)
    pixel_y = np.rint(projected_y).astype(np.int32)
    visible_bounds = (
        valid_depth
        & (pixel_x >= 0)
        & (pixel_x < width)
        & (pixel_y >= 0)
        & (pixel_y < height)
    )

    destination_indices = pixel_y[visible_bounds] * width + pixel_x[visible_bounds]
    destination_depths = view_z[visible_bounds]
    z_buffer = np.full(width * height, np.inf, dtype=np.float32)
    np.minimum.at(z_buffer, destination_indices, destination_depths)
    nearest_points = destination_depths <= z_buffer[destination_indices] + 1e-5

    frame = np.zeros((height * width, 3), dtype=np.uint8)
    frame[destination_indices[nearest_points]] = colors[visible_bounds][nearest_points]
    frame = frame.reshape(height, width, 3)
    holes = np.isinf(z_buffer).reshape(height, width).astype(np.uint8) * 255
    if cv2.countNonZero(holes):
        frame = _fill_reprojection_holes(frame, holes)
    return frame


def _get_replicate_token() -> str:
    for name in ("REPLICATE_API_TOKEN", "REPLICATE_API_KEY"):
        token = os.getenv(name, "").strip()
        if token:
            return token
    return ""


def _find_video_url(output) -> str | None:
    if isinstance(output, str) and output.startswith(("https://", "http://")):
        return output
    if isinstance(output, dict):
        for key in ("video", "output", "url"):
            url = _find_video_url(output.get(key))
            if url:
                return url
        for value in output.values():
            url = _find_video_url(value)
            if url:
                return url
    if isinstance(output, (list, tuple)):
        for item in output:
            url = _find_video_url(item)
            if url:
                return url
    return None


def _select_hybrid_route(character_action: str) -> tuple[str, float]:
    """Select a bounded motion route from the requested character action."""
    if character_action in {"None (Camera Motion Only)", "None (Camera Only)"}:
        return "camera", _DURATION_SECONDS
    if character_action in {
        "Hand Gestures & Expressive Dialogue",
        "Subtle Facial Expressions (Nod/Smirk)",
        "Shouting / Intense Speech",
        "Hand Gestures / Talking",
        "Facial Expressions",
    }:
        return "portrait", _PORTRAIT_DRIVING_DURATION_SECONDS
    return "dynamic", _DYNAMIC_ACTION_DURATION_SECONDS


def _post_i2v_prediction(endpoint: str, headers: dict, payload: dict) -> dict:
    for attempt in range(_I2V_MAX_SUBMISSION_RETRIES + 1):
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            if attempt == _I2V_MAX_SUBMISSION_RETRIES:
                raise RuntimeError("Image-to-video submission request failed after retries.") from exc
            time.sleep(min(20, _I2V_RETRY_DELAY_SECONDS * (2 ** attempt)))
            continue

        if response.status_code in {200, 201, 202}:
            try:
                result = response.json()
            except ValueError as exc:
                raise RuntimeError("Image-to-video returned invalid JSON.") from exc
            if not isinstance(result, dict):
                raise RuntimeError("Image-to-video returned an invalid prediction.")
            return result

        if response.status_code != 429 and response.status_code < 500:
            logger.error(
                "Replicate I2V submission rejected (HTTP %s): %s",
                response.status_code,
                response.text[:8000],
            )
            raise RuntimeError(
                f"Image-to-video request returned HTTP {response.status_code}: "
                f"{response.text[:4000]}"
            )
        if attempt == _I2V_MAX_SUBMISSION_RETRIES:
            logger.error(
                "Replicate I2V submission failed (HTTP %s): %s",
                response.status_code,
                response.text[:8000],
            )
            raise RuntimeError(
                f"Image-to-video request failed after {attempt + 1} attempts "
                f"(HTTP {response.status_code}): {response.text[:4000]}"
            )
        logger.warning(
            "Image-to-video request returned HTTP %s; retrying in %d seconds (%d/%d).",
            response.status_code,
            _I2V_RETRY_DELAY_SECONDS,
            attempt + 1,
            _I2V_MAX_SUBMISSION_RETRIES,
        )
        retry_after = response.headers.get("Retry-After", "")
        try:
            delay = max(1, min(30, int(float(retry_after))))
        except (TypeError, ValueError):
            delay = min(20, _I2V_RETRY_DELAY_SECONDS * (2 ** attempt))
        time.sleep(delay)
    raise AssertionError("Image-to-video retry loop exited unexpectedly.")


def _poll_video_prediction(prediction: dict, headers: dict, timeout_seconds: int, label: str) -> str:
    deadline = time.monotonic() + timeout_seconds
    poll_count = 0
    while True:
        status = str(prediction.get("status", "")).lower()
        if status == "succeeded":
            video_url = _find_video_url(prediction.get("output"))
            if video_url:
                logger.info(
                    "%s completed after %d status checks in %.2fs.",
                    label,
                    poll_count,
                    timeout_seconds - max(0.0, deadline - time.monotonic()),
                )
                return video_url
            raise RuntimeError(f"{label} completed without returning a video URL.")
        if status in {"failed", "canceled", "cancelled"}:
            failure_details = {
                "status": status,
                "error": prediction.get("error"),
                "logs": prediction.get("logs"),
                "id": prediction.get("id"),
            }
            logger.error(
                "Replicate I2V prediction ended with %s: %s",
                status,
                json.dumps(failure_details, ensure_ascii=False, default=str)[:12000],
            )
            raise RuntimeError(
                f"{label} {status}: {prediction.get('error') or 'no error details provided'}; "
                f"Replicate logs: {str(prediction.get('logs') or '')[-3000:]}"
            )
        if time.monotonic() >= deadline:
            raise TimeoutError(f"{label} did not finish within {timeout_seconds} seconds.")
        status_url = (prediction.get("urls") or {}).get("get")
        if not isinstance(status_url, str) or not status_url.startswith("https://"):
            raise RuntimeError(f"{label} returned no valid polling URL.")
        time.sleep(_I2V_POLL_INTERVAL_SECONDS)
        poll_count += 1
        last_error = None
        for retry in range(_I2V_MAX_REQUEST_RETRIES + 1):
            try:
                response = requests.get(status_url, headers=headers, timeout=5)
                if response.status_code == 429 or response.status_code >= 500:
                    if retry < _I2V_MAX_REQUEST_RETRIES:
                        retry_after = response.headers.get("Retry-After", "")
                        try:
                            delay = max(1, min(30, int(float(retry_after))))
                        except (TypeError, ValueError):
                            delay = min(20, _I2V_RETRY_DELAY_SECONDS * (2 ** retry))
                        time.sleep(delay)
                        continue
                if response.status_code >= 400:
                    logger.error(
                        "Replicate I2V status poll failed (HTTP %s): %s",
                        response.status_code,
                        response.text[:8000],
                    )
                response.raise_for_status()
                prediction = response.json()
                break
            except requests.HTTPError as exc:
                response = exc.response
                if response is not None and response.status_code != 429 and response.status_code < 500:
                    logger.exception(
                        "Non-retryable Replicate I2V poll response (HTTP %s): %s",
                        response.status_code,
                        response.text[:8000],
                    )
                    raise RuntimeError(
                        f"Replicate I2V poll returned HTTP {response.status_code}: "
                        f"{response.text[:4000]}"
                    ) from exc
                last_error = exc
                if retry == _I2V_MAX_REQUEST_RETRIES:
                    raise RuntimeError(f"Could not poll {label} after retries.") from exc
                time.sleep(min(20, _I2V_RETRY_DELAY_SECONDS * (2 ** retry)))
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if retry == _I2V_MAX_REQUEST_RETRIES:
                    raise RuntimeError(f"Could not poll {label} after retries.") from exc
                time.sleep(min(20, _I2V_RETRY_DELAY_SECONDS * (2 ** retry)))
        else:
            raise RuntimeError(f"Could not poll {label}.") from last_error
        if not isinstance(prediction, dict):
            raise RuntimeError(f"{label} returned an invalid prediction response.")


def _run_replicate_video_model(
    model_ref: str,
    model_input: dict,
    label: str,
    timeout_seconds: int = 120,
    version: str = "",
) -> tuple[str, str]:
    """Run a Replicate video model and return its normalized local MP4 and source URL."""
    token = _get_replicate_token()
    if not token:
        raise RuntimeError("Replicate API key is not configured for the video model.")
    if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", model_ref):
        raise ValueError("Replicate model must use owner/model format.")

    payload = {"input": model_input}
    if version:
        payload["version"] = f"{model_ref}:{version}"
        endpoint = "https://api.replicate.com/v1/predictions"
    else:
        endpoint = f"https://api.replicate.com/v1/models/{model_ref}/predictions"
    headers = {
        "Authorization": f"******",
        "Content-Type": "application/json",
    }
    prediction = _post_i2v_prediction(endpoint, headers, payload)
    video_url = _poll_video_prediction(
        prediction,
        headers,
        max(1, int(timeout_seconds)),
        label,
    )
    return _download_remote_video(video_url, label), video_url


def _download_remote_video(video_url: str, label: str) -> str:
    """Download a model result and normalize it to the Ghost Engine 16:9 canvas."""
    _OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    temp_path = _OUTPUT_ROOT / f".{label}-{uuid.uuid4().hex}.download.mp4"
    output_path = _OUTPUT_ROOT / f"{label}_{uuid.uuid4().hex}.mp4"
    try:
        response = requests.get(video_url, timeout=10, stream=True)
        response.raise_for_status()
        with temp_path.open("wb") as video_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    video_file.write(chunk)
        capture = cv2.VideoCapture(str(temp_path))
        if not capture.isOpened():
            raise RuntimeError(f"{label} returned an unreadable video.")
        source_fps = capture.get(cv2.CAP_PROP_FPS)
        output_fps = source_fps if math.isfinite(source_fps) and source_fps >= 8 else _FPS
        writer = cv2.VideoWriter(
            str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), float(output_fps), _OUTPUT_SIZE
        )
        if not writer.isOpened():
            capture.release()
            raise RuntimeError(f"Could not initialize the {label} MP4 encoder.")
        written = 0
        try:
            while True:
                success, frame = capture.read()
                if not success:
                    break
                writer.write(_fit_frame_to_output(frame))
                written += 1
        finally:
            capture.release()
            writer.release()
        if written < 2 or not output_path.is_file() or output_path.stat().st_size < 1000:
            raise RuntimeError(f"{label} contained too few usable frames.")
        return str(output_path)
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    finally:
        temp_path.unlink(missing_ok=True)


def _compact_image_data_uri(image_path: str, target_size=(1536, 864)) -> str:
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read reference image: {image_path}")
    image = _fit_frame_to_size(image, target_size)
    for quality in (82, 76, 70, 64, 58):
        encoded, image_bytes = cv2.imencode(
            ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality]
        )
        if encoded and len(image_bytes) <= 240 * 1024:
            return "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
    raise RuntimeError("Could not compress the reference image below Replicate's inline-file limit.")


def _build_i2v_input(
    model_ref: str,
    image_data: str,
    prompt: str,
    frame_count: int,
    wan_resolution: str | None = None,
) -> dict:
    """Build payloads from fields supported by the selected public model."""
    normalized_model = model_ref.lower()
    if "wan-2.2-i2v-fast" in normalized_model:
        resolution = os.getenv(
            "ZOVIX_GHOST_WAN_RESOLUTION",
            wan_resolution or "480p",
        ).strip()
        if resolution not in {"480p", "720p"}:
            raise ValueError("ZOVIX_GHOST_WAN_RESOLUTION must be either '480p' or '720p'.")
        return {
            "prompt": prompt,
            "image": image_data,
            "resolution": resolution,
        }
    if "cogvideox" in normalized_model:
        return {
            "image": image_data,
            "prompt": prompt,
            "num_frames": min(49, max(9, frame_count)),
            "guidance_scale": 6,
            "num_inference_steps": 28,
        }
    if "ltx-video" in normalized_model:
        return {
            "image": image_data,
            "prompt": prompt,
            "width": 768,
            "height": 448,
            "num_frames": frame_count,
            "fps": 24,
            "guidance_scale": 3.2,
            "negative_prompt": (
                "still image, static pose, minimal motion, frozen subject, "
                "worst quality, inconsistent motion, flicker, jitter, blurry, "
                "warped anatomy, deformed hands, duplicate limbs, identity change, "
                "background morphing, abrupt cuts"
            ),
            "num_inference_steps": 28,
        }
    raise ValueError(
        f"Unsupported I2V model {model_ref!r}. Use wan-video/wan-2.2-i2v-fast, "
        "lightricks/ltx-video-0.9.7, or an "
        "image-to-video CogVideoX model (for example thudm/cogvideox-i2v)."
    )


def _run_i2v_prediction(
    keyframe_path: str,
    motion_prompt: str,
    camera_motion: str,
    duration_seconds: float,
    scene_prompt: str = "",
    model_ref: str | None = None,
    model_version: str | None = None,
    timeout_seconds: int = _I2V_TIMEOUT_SECONDS,
    wan_resolution: str | None = None,
) -> tuple[str, str]:
    token = _get_replicate_token()
    if not token:
        raise RuntimeError("Replicate API key is not configured for character motion.")
    selected_model = (model_ref or _I2V_MODEL).strip()
    selected_version = (
        model_version if model_version is not None
        else (_I2V_VERSION if selected_model == _I2V_MODEL else "")
    ).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", selected_model):
        raise RuntimeError("ZOVIX_GHOST_I2V_MODEL must be an owner/model reference.")

    image_data = _compact_image_data_uri(keyframe_path, target_size=(768, 448))
    duration = min(_I2V_MAX_DURATION_SECONDS, max(2.0, duration_seconds))
    frame_count = max(9, round(duration * 24))
    frame_count = ((frame_count - 1 + 4) // 8) * 8 + 1
    prompt = ", ".join(
        part.strip(" ,.")
        for part in (
            scene_prompt,
            motion_prompt,
            "cinematic high-dynamic character action with continuous full-body movement",
            "preserve the exact character identity, face, clothing, lighting, and scene composition from the input image",
            _CAMERA_MOTION_PROMPTS[camera_motion],
            "one continuous shot with visible temporal change from the first frame to the last, no cuts, no frozen pose, no Ken Burns or digital zoom substitute",
            "natural acceleration, grounded weight shifts, believable follow-through, restrained cinematic motion blur, stable coherent background",
        )
        if part and part.strip()
    )
    payload = {
        "input": _build_i2v_input(
            selected_model,
            image_data,
            prompt,
            frame_count,
            wan_resolution=wan_resolution,
        )
    }
    if selected_version:
        endpoint = "https://api.replicate.com/v1/predictions"
        payload["version"] = f"{selected_model}:{selected_version}"
    else:
        endpoint = f"https://api.replicate.com/v1/models/{selected_model}/predictions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    deadline = time.monotonic() + timeout_seconds
    prediction = _post_i2v_prediction(endpoint, headers, payload)
    video_url = _poll_video_prediction(
        prediction,
        headers,
        max(1, int(deadline - time.monotonic())),
        f"Replicate I2V ({selected_model})",
    )

    _OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    download_path = _OUTPUT_ROOT / f".i2v-{uuid.uuid4().hex}.mp4"
    output_path = _OUTPUT_ROOT / f"motion_i2v_{uuid.uuid4().hex}.mp4"
    try:
        try:
            response = requests.get(video_url, timeout=10, stream=True)
            response.raise_for_status()
            with download_path.open("wb") as video_file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        video_file.write(chunk)
        except requests.RequestException as exc:
            raise RuntimeError("Could not download the character-motion video.") from exc

        capture = cv2.VideoCapture(str(download_path))
        if not capture.isOpened():
            raise RuntimeError("Image-to-video returned an unreadable video.")
        source_fps = float(capture.get(cv2.CAP_PROP_FPS))
        source_frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        capture.release()
        if not math.isfinite(source_fps) or source_fps <= 0 or source_frame_count < 2:
            raise RuntimeError("Image-to-video returned invalid frame metadata.")
        written = min(source_frame_count, round(duration * source_fps))
        _normalize_i2v_video(
            download_path, output_path, written, duration, source_fps
        )
        return str(output_path), video_url
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(f"Could not process the returned I2V video: {exc}") from exc
    finally:
        download_path.unlink(missing_ok=True)


def _render_2d_camera_motion(keyframe_path: str, motion_type: str, duration: float) -> str:
    """Create a smooth local Ken Burns fallback without requiring a depth map."""
    image = cv2.imread(keyframe_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read local-motion keyframe: {keyframe_path}")
    source = _fit_frame_to_output(image)
    width, height = _OUTPUT_SIZE
    _OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    output_path = _OUTPUT_ROOT / f"motion_local_{uuid.uuid4().hex}.mp4"
    writer = cv2.VideoWriter(
        str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), float(_FPS), _OUTPUT_SIZE
    )
    if not writer.isOpened():
        writer.release()
        raise RuntimeError("Could not initialize the local camera-motion encoder.")
    frame_count = max(2, round(_FPS * duration))
    try:
        for index in range(frame_count):
            linear = index / max(frame_count - 1, 1)
            progress = linear * linear * (3.0 - 2.0 * linear)
            zoom = 1.0
            shift_x = 0.0
            shift_y = 0.0
            angle = 0.0
            if motion_type in {"Dolly In", "Zoom In", "Rack Focus (Push)"}:
                zoom = 1.0 + 0.08 * progress
            elif motion_type in {"Dolly Out", "Rack Focus (Pull)"}:
                zoom = 1.0 - 0.06 * progress
            elif motion_type == "Dolly Zoom (Hitchcock)":
                zoom = 1.0 + 0.085 * progress
            elif motion_type == "Pan Left":
                shift_x = -0.045 * width * progress
            elif motion_type == "Pan Right":
                shift_x = 0.045 * width * progress
            elif motion_type == "Tilt Up":
                shift_y = -0.045 * height * progress
            elif motion_type == "Tilt Down":
                shift_y = 0.045 * height * progress
            elif motion_type in {"Crane Up", "Drone Flyover (Aerial)"}:
                shift_y = -0.055 * height * progress
                zoom = 1.0 - 0.025 * progress
            elif motion_type == "Crane Down":
                shift_y = 0.055 * height * progress
            elif motion_type in {"Orbit Left (360)", "Orbit Right (360)", "Drone Circle"}:
                direction = -1.0 if motion_type == "Orbit Left (360)" else 1.0
                shift_x = direction * 0.035 * width * math.sin(progress * math.pi * 2.0)
                zoom = 1.0 + 0.025 * progress
            elif motion_type == "Tracking (Subject Follow)":
                shift_x = 0.025 * width * math.sin(progress * math.pi * 2.0)
            elif motion_type in {"Tracking (Forward)", "Point of View (POV)"}:
                zoom = 1.0 + 0.07 * progress
            elif motion_type == "Roll Clockwise":
                angle = -5.0 * progress
            elif motion_type == "Roll Counter-Clockwise":
                angle = 5.0 * progress
            elif motion_type == "Handheld Shake (Low)":
                shift_x = 0.004 * width * math.sin(linear * math.pi * 12.0)
                shift_y = 0.004 * height * math.cos(linear * math.pi * 10.0)
            elif motion_type == "Handheld Shake (High)":
                shift_x = 0.012 * width * math.sin(linear * math.pi * 16.0)
                shift_y = 0.012 * height * math.cos(linear * math.pi * 14.0)
            elif motion_type == "Bullet Time (Super Slow)":
                shift_x = 0.025 * width * math.sin(progress * math.pi)
                angle = 3.0 * math.sin(progress * math.pi)
            if motion_type == "Static (No Motion)":
                zoom, shift_x, shift_y, angle = 1.0, 0.0, 0.0, 0.0
            matrix = np.array(
                [
                    [
                        zoom * math.cos(math.radians(angle)),
                        -zoom * math.sin(math.radians(angle)),
                        (1.0 - zoom) * width / 2.0 + shift_x,
                    ],
                    [
                        zoom * math.sin(math.radians(angle)),
                        zoom * math.cos(math.radians(angle)),
                        (1.0 - zoom) * height / 2.0 + shift_y,
                    ],
                ],
                dtype=np.float32,
            )
            frame = cv2.warpAffine(
                source, matrix, _OUTPUT_SIZE, flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REFLECT_101,
            )
            writer.write(frame)
    except Exception:
        writer.release()
        output_path.unlink(missing_ok=True)
        raise
    writer.release()
    if not output_path.is_file() or output_path.stat().st_size < 1000:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("Local camera-motion fallback produced no usable video.")
    logger.warning("Using local 2D camera-motion fallback from the Flux keyframe.")
    return str(output_path)


def apply_camera_motion(
    keyframe_path: str,
    depth_path: str | None,
    motion_type: str,
    duration_seconds: float = _DURATION_SECONDS,
    character_action: str = "None (Camera Only)",
    return_remote_url: bool = False,
    scene_prompt: str = "",
    quality: str | None = None,
) -> str | tuple[str, str]:
    """Create an image-to-video action clip or fall back to depth-guided camera motion."""
    if motion_type not in _MOTION_TYPES:
        raise ValueError(
            f"Unsupported motion_type {motion_type!r}. "
            f"Choose one of: {', '.join(_MOTION_TYPES)}."
        )
    if character_action not in _CHARACTER_ACTIONS:
        raise ValueError(
            f"Unsupported character_action {character_action!r}. "
            f"Choose one of: {', '.join(_CHARACTER_ACTIONS)}."
        )
    try:
        duration_seconds = float(duration_seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError("duration_seconds must be a positive number.") from exc
    if not math.isfinite(duration_seconds) or duration_seconds <= 0 or duration_seconds > 180:
        raise ValueError("duration_seconds must be greater than 0 and no more than 180.")

    route, routed_duration = _select_hybrid_route(character_action)
    if route != "camera":
        fast_model = os.getenv("ZOVIX_GHOST_FAST_I2V_MODEL", _WAN_I2V_MODEL).strip()
        if "wan-2.2-i2v-fast" in fast_model.lower():
            duration_seconds = _WAN_I2V_DURATION_SECONDS
        else:
            duration_seconds = routed_duration
        fast_version = os.getenv(
            "ZOVIX_GHOST_FAST_I2V_VERSION",
            _I2V_VERSION if fast_model == _I2V_MODEL else "",
        ).strip()
        try:
            router_timeout = int(os.getenv(
                "ZOVIX_GHOST_ROUTER_TIMEOUT_SECONDS",
                str(_ROUTER_I2V_TIMEOUT_SECONDS),
            ))
        except ValueError:
            logger.warning("Invalid router timeout; using %s seconds.", _ROUTER_I2V_TIMEOUT_SECONDS)
            router_timeout = _ROUTER_I2V_TIMEOUT_SECONDS
        router_timeout = min(600, max(15, router_timeout))
        try:
            driving_video = _run_i2v_prediction(
                keyframe_path,
                _ACTION_MOTION_PROMPTS[character_action],
                motion_type,
                duration_seconds,
                scene_prompt,
                model_ref=fast_model,
                model_version=fast_version,
                timeout_seconds=router_timeout,
                wan_resolution="720p" if quality == "HD" else "480p",
            )
            final_video = driving_video[0]
            if route == "portrait" and driving_video[1]:
                try:
                    from layer5_liveportrait import animate_face_from_motion

                    portrait_model = os.getenv(
                        "ZOVIX_GHOST_LIVEPORTRAIT_MODEL",
                        "charlesmccarthy/liveportrait",
                    ).strip()
                    portrait_version = os.getenv(
                        "ZOVIX_GHOST_LIVEPORTRAIT_VERSION",
                        "4d56e26a1ce02936e7c047b6ce9dc1a60fb7d97cc5a6a1f116a6a73af474cebf",
                    ).strip()
                    animated_path, animated = animate_face_from_motion(
                        keyframe_path,
                        driving_video[1],
                        final_video,
                        model_ref=portrait_model,
                        model_version=portrait_version,
                        timeout_seconds=router_timeout,
                    )
                    if animated:
                        final_video = animated_path
                except Exception:
                    logger.exception(
                        "LivePortrait route failed; retaining fast I2V portrait driving clip."
                    )
            logger.info(
                "Hybrid router selected %s route for action=%s using model=%s.",
                route,
                character_action,
                fast_model,
            )
            return (final_video, driving_video[1]) if return_remote_url else final_video
        except Exception as exc:
            logger.exception(
                "Hybrid route failed for action=%s using model=%s.",
                character_action,
                fast_model,
            )
            raise RuntimeError(
                f"Replicate character-motion generation failed for {character_action!r} "
                f"using {fast_model}. No pan/zoom-only fallback was substituted. "
                f"Provider error: {exc}"
            ) from exc

    if not depth_path:
        return _render_2d_camera_motion(keyframe_path, motion_type, duration_seconds)

    keyframe, near_weight = _load_inputs(keyframe_path, depth_path)
    points, focal_length, anchor_depth = _prepare_point_cloud(keyframe, near_weight)
    _OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    output_id = uuid.uuid4().hex
    temporary_path = _OUTPUT_ROOT / f".motion-{output_id}.tmp.mp4"
    output_path = _OUTPUT_ROOT / f"motion_{output_id}.mp4"
    frame_count = max(1, round(_FPS * duration_seconds))
    width, height = _OUTPUT_SIZE
    writer = cv2.VideoWriter(
        str(temporary_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        float(_FPS),
        (width, height),
    )
    if not writer.isOpened():
        writer.release()
        raise RuntimeError(
            "Could not initialize the MP4 video encoder. Check the OpenCV/FFmpeg "
            "installation and MP4 codec support."
        )

    logger.info("Rendering %s camera motion from depth map.", motion_type)
    completed = False
    try:
        for frame_index in range(frame_count):
            linear_progress = frame_index / max(frame_count - 1, 1)
            progress = linear_progress * linear_progress * (3.0 - 2.0 * linear_progress)
            pose = _camera_pose(
                motion_type, progress, focal_length, anchor_depth
            )
            frame = _reproject_frame(
                points,
                pose,
                _OUTPUT_SIZE,
            )
            writer.write(frame)
        completed = True
    finally:
        writer.release()
        if not completed:
            temporary_path.unlink(missing_ok=True)

    if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError("Camera motion render finished without producing an MP4.")
    os.replace(temporary_path, output_path)
    logger.info("Camera motion clip saved to %s.", output_path)
    return str(output_path)
