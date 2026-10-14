"""Layer 4 of the ZOVIX Ghost Engine: lighting and atmosphere post-processing."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

import logging
import os
import uuid
import cv2
import numpy as np


logger = logging.getLogger(__name__)

_LIGHTING_TYPES = (
    "Volumetric Golden Hour",
    "Dramatic Rim Light",
    "Cyberpunk Neon",
)
_ATMOSPHERE_TYPES = ("Dust Motes", "Rain", "Fog", "Embers", "None")
_OUTPUT_ROOT = Path(__file__).resolve().parent / "static" / "outputs"


def _create_lighting_state(lighting_type: str, width: int, height: int):
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]

    if lighting_type == "Volumetric Golden Hour":
        dx = x - 0.08
        dy = y - 0.04
        distance = np.sqrt(dx * dx + dy * dy)
        angle = np.arctan2(dy, dx)
        rays = np.zeros((height, width), dtype=np.float32)
        for ray_angle in np.linspace(0.18, 0.9, 6, dtype=np.float32):
            rays += np.exp(-np.square((angle - ray_angle) / 0.025))
        rays *= np.exp(-distance * 1.8)
        rays = np.clip(rays * 0.22, 0.0, 0.32)
        leak = np.exp(
            -(
                np.square((x - 0.08) / 0.28)
                + np.square((y - 0.18) / 0.48)
            )
        )
        overlay = np.zeros((height, width, 3), dtype=np.float32)
        overlay[:, :, 0] = (rays + leak * 0.12) * 110.0
        overlay[:, :, 1] = (rays + leak * 0.12) * 175.0
        overlay[:, :, 2] = (rays + leak * 0.12) * 255.0
        return {"overlay": overlay}

    if lighting_type == "Cyberpunk Neon":
        flare_axis = (x + y * 0.28 - 0.68) / 0.012
        flare_line = np.exp(-np.square(flare_axis))
        ghosts = np.zeros((height, width), dtype=np.float32)
        for gx, gy, radius in (
            (0.12, 0.68, 0.045),
            (0.42, 0.59, 0.025),
            (0.78, 0.48, 0.035),
            (0.92, 0.44, 0.018),
        ):
            ghosts += np.exp(
                -(
                    np.square((x - gx) / radius)
                    + np.square((y - gy) / radius)
                )
            )
        flare = np.clip(flare_line * 0.16 + ghosts * 0.3, 0.0, 0.5)
        overlay = np.zeros((height, width, 3), dtype=np.float32)
        overlay[:, :, 0] = flare * 255.0
        overlay[:, :, 2] = flare * 235.0
        return {"overlay": overlay}

    return {}


def _grade_frame(frame: np.ndarray, lighting_type: str) -> np.ndarray:
    if lighting_type == "Volumetric Golden Hour":
        gains = np.array((0.94, 1.03, 1.13), dtype=np.float32)
        contrast, brightness = 1.04, 2.0
    elif lighting_type == "Dramatic Rim Light":
        gains = np.array((1.10, 1.02, 0.94), dtype=np.float32)
        contrast, brightness = 1.13, -10.0
    else:
        gains = np.array((1.15, 0.96, 1.10), dtype=np.float32)
        contrast, brightness = 1.08, -5.0

    graded = (
        (frame.astype(np.float32) - 128.0) * contrast + 128.0 + brightness
    )
    graded *= gains[None, None, :]

    if lighting_type == "Cyberpunk Neon":
        luminance = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        shadows = np.clip((145.0 - luminance) / 145.0, 0.0, 1.0)
        highlights = np.clip((luminance - 120.0) / 135.0, 0.0, 1.0)
        graded[:, :, 0] += shadows * 12.0
        graded[:, :, 2] += highlights * 18.0

    return np.clip(graded, 0.0, 255.0).astype(np.uint8)


def _apply_lighting(
    frame: np.ndarray,
    lighting_type: str,
    lighting_state: dict,
    frame_index: int,
) -> np.ndarray:
    graded = _grade_frame(frame, lighting_type)
    result = graded.astype(np.float32)

    if lighting_type == "Dramatic Rim Light":
        luminance = cv2.cvtColor(graded, cv2.COLOR_BGR2GRAY)
        gradient_x = cv2.Sobel(luminance, cv2.CV_32F, 1, 0, ksize=3)
        gradient_y = cv2.Sobel(luminance, cv2.CV_32F, 0, 1, ksize=3)
        edge_strength = cv2.magnitude(gradient_x, gradient_y)
        edge_strength = np.clip(edge_strength / 360.0, 0.0, 1.0)
        edge_glow = cv2.GaussianBlur(edge_strength, (0, 0), sigmaX=3.0)
        rim_color = np.array((210.0, 225.0, 255.0), dtype=np.float32)
        result += edge_glow[:, :, None] * rim_color[None, None, :] * 0.7
    else:
        overlay = lighting_state["overlay"]
        pulse = 0.92 + 0.08 * np.sin(frame_index * 0.08)
        result += overlay * pulse

    if lighting_type == "Cyberpunk Neon":
        luminance = cv2.cvtColor(graded, cv2.COLOR_BGR2GRAY).astype(np.float32)
        bright_mask = np.clip((luminance - 160.0) / 90.0, 0.0, 1.0)
        bright_sources = graded.astype(np.float32) * bright_mask[:, :, None]
        bloom = cv2.GaussianBlur(bright_sources, (0, 0), sigmaX=12.0)
        result += bloom * 0.28

    return np.clip(result, 0.0, 255.0).astype(np.uint8)


def _create_atmosphere_state(fx_type: str, width: int, height: int):
    rng = np.random.default_rng(2025)
    particle_count = max(1, round(width * height / (1280 * 720) * 70))

    if fx_type in {"Dust Motes", "Embers"}:
        return {
            "x": rng.uniform(0.0, width, particle_count).astype(np.float32),
            "y": rng.uniform(0.0, height, particle_count).astype(np.float32),
            "vx": rng.uniform(-9.0, 9.0, particle_count).astype(np.float32),
            "vy": rng.uniform(8.0, 34.0, particle_count).astype(np.float32),
            "radius": rng.integers(1, 4, particle_count),
            "phase": rng.uniform(0.0, 6.28, particle_count).astype(np.float32),
        }
    if fx_type == "Rain":
        count = particle_count * 2
        return {
            "x": rng.uniform(0.0, width, count).astype(np.float32),
            "y": rng.uniform(0.0, height, count).astype(np.float32),
            "vx": rng.uniform(18.0, 42.0, count).astype(np.float32),
            "vy": rng.uniform(220.0, 390.0, count).astype(np.float32),
            "length": rng.integers(8, 20, count),
        }
    if fx_type == "Fog":
        noise_height = max(12, height // 16)
        noise_width = max(12, width // 16)
        noise = rng.random((noise_height, noise_width), dtype=np.float32)
        noise = cv2.GaussianBlur(noise, (0, 0), sigmaX=2.0)
        noise = (noise - noise.min()) / max(float(noise.max() - noise.min()), 1e-6)
        return {"noise": noise}
    return {}


def _apply_atmosphere(
    frame: np.ndarray,
    fx_type: str,
    state: dict,
    frame_index: int,
    fps: float,
) -> np.ndarray:
    if fx_type == "None":
        return frame

    height, width = frame.shape[:2]
    elapsed = frame_index / fps

    if fx_type == "Fog":
        noise = np.roll(state["noise"], int(frame_index * 0.12), axis=1)
        fog_mask = cv2.resize(noise, (width, height), interpolation=cv2.INTER_CUBIC)
        fog_mask = cv2.GaussianBlur(fog_mask, (0, 0), sigmaX=width / 80.0)
        vertical_weight = np.linspace(0.65, 1.0, height, dtype=np.float32)[:, None]
        alpha = np.clip(fog_mask * vertical_weight * 0.24, 0.0, 0.28)
        fog_color = np.array((205.0, 215.0, 220.0), dtype=np.float32)
        fogged = (
            frame.astype(np.float32) * (1.0 - alpha[:, :, None])
            + fog_color[None, None, :] * alpha[:, :, None]
        )
        return np.clip(fogged, 0.0, 255.0).astype(np.uint8)

    overlay = np.zeros_like(frame)
    x = (state["x"] + state["vx"] * elapsed) % width

    if fx_type == "Rain":
        y = (state["y"] + state["vy"] * elapsed) % height
        for index in range(len(x)):
            start = (int(x[index]), int(y[index]))
            end = (
                int(x[index] - state["vx"][index] * 0.045),
                int(y[index] - state["length"][index]),
            )
            cv2.line(overlay, start, end, (190, 210, 225), 1, cv2.LINE_AA)
        rain_glow = cv2.GaussianBlur(overlay, (0, 0), sigmaX=1.1)
        mixed = cv2.addWeighted(frame, 1.0, rain_glow, 0.45, 0.0)
        return cv2.addWeighted(mixed, 1.0, overlay, 0.35, 0.0)

    y = (state["y"] - state["vy"] * elapsed) % height
    if fx_type == "Dust Motes":
        for index in range(len(x)):
            sway = 5.0 * np.sin(state["phase"][index] + elapsed * 0.7)
            center = (int(x[index] + sway), int(y[index]))
            radius = int(state["radius"][index])
            cv2.circle(overlay, center, radius, (175, 220, 255), -1, cv2.LINE_AA)
        glow = cv2.GaussianBlur(overlay, (0, 0), sigmaX=3.0)
        mixed = cv2.addWeighted(frame, 1.0, glow, 0.55, 0.0)
        return cv2.addWeighted(mixed, 1.0, overlay, 0.35, 0.0)

    flicker = 0.78 + 0.22 * np.sin(state["phase"] + elapsed * 4.0)
    for index in range(len(x)):
        center = (int(x[index]), int(y[index]))
        radius = int(state["radius"][index])
        intensity = int(170 + 85 * flicker[index])
        cv2.circle(overlay, center, radius, (0, int(intensity * 0.48), intensity), -1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(overlay, (0, 0), sigmaX=4.0)
    mixed = cv2.addWeighted(frame, 1.0, glow, 0.72, 0.0)
    return cv2.addWeighted(mixed, 1.0, overlay, 0.58, 0.0)


def apply_atmosphere_and_lighting(
    video_path: str,
    lighting_type: str,
    fx_type: str,
) -> str:
    """Apply per-frame lighting and atmosphere effects; return the final MP4 path."""
    if not isinstance(video_path, str) or not video_path.strip():
        raise ValueError("video_path must be a non-empty path.")
    if lighting_type not in _LIGHTING_TYPES:
        raise ValueError(
            f"Unsupported lighting_type {lighting_type!r}. "
            f"Choose one of: {', '.join(_LIGHTING_TYPES)}."
        )
    if fx_type not in _ATMOSPHERE_TYPES:
        raise ValueError(
            f"Unsupported fx_type {fx_type!r}. "
            f"Choose one of: {', '.join(_ATMOSPHERE_TYPES)}."
        )
    if not Path(video_path).is_file():
        raise FileNotFoundError(f"Input video does not exist: {video_path}")

    _OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        logger.error("Could not open input video %s.", video_path)
        raise RuntimeError(f"Could not open input video: {video_path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if not np.isfinite(fps) or fps <= 0.0:
        capture.release()
        logger.error("Input video %s has invalid frame rate %r.", video_path, fps)
        raise ValueError("Input video has an invalid frame rate.")
    ok, first_frame = capture.read()
    if not ok or first_frame is None:
        capture.release()
        logger.error("Input video %s contains no readable frames.", video_path)
        raise ValueError("Input video contains no readable frames.")

    height, width = first_frame.shape[:2]
    try:
        lighting_state = _create_lighting_state(lighting_type, width, height)
        atmosphere_state = _create_atmosphere_state(fx_type, width, height)
    except cv2.error:
        capture.release()
        logger.exception("Could not initialize visual effects for %s.", video_path)
        raise

    output_id = uuid.uuid4().hex
    temporary_path = _OUTPUT_ROOT / f".fx-{output_id}.tmp.mp4"
    output_path = _OUTPUT_ROOT / f"fx_{output_id}.mp4"
    writer = cv2.VideoWriter(
        str(temporary_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        writer.release()
        capture.release()
        logger.error("Could not initialize MP4 encoder for %s.", video_path)
        raise RuntimeError(
            "Could not initialize the MP4 video encoder. Check the OpenCV/FFmpeg "
            "installation and MP4 codec support."
        )

    logger.info(
        "Applying %s lighting and %s atmosphere to input video.",
        lighting_type,
        fx_type,
    )
    frame_index = 0
    completed = False
    try:
        frame = first_frame
        while frame is not None:
            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            lit_frame = _apply_lighting(frame, lighting_type, lighting_state, frame_index)
            final_frame = _apply_atmosphere(
                lit_frame,
                fx_type,
                atmosphere_state,
                frame_index,
                fps,
            )
            writer.write(final_frame)
            frame_index += 1
            ok, frame = capture.read()
            if not ok:
                frame = None
        completed = frame_index > 0
    except cv2.error:
        logger.exception("OpenCV failed while processing %s.", video_path)
        raise
    finally:
        capture.release()
        writer.release()
        if not completed:
            temporary_path.unlink(missing_ok=True)

    if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError("Atmosphere and lighting render produced no MP4 output.")
    try:
        os.replace(temporary_path, output_path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        logger.exception("Could not publish final effects video to %s.", output_path)
        raise
    logger.info("Atmosphere and lighting video saved to %s (%s frames).", output_path, frame_index)
    return str(output_path)
