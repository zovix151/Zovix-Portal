#!/usr/bin/env python3
"""
==========================================================================
ZOVIX ComfyUI Image Generation Engine (RunPod Serverless)
==========================================================================
Replaces the legacy Stability AI / Pollinations image pipeline with the
ComfyUI workflow running behind a RunPod serverless endpoint.

Flow:
  1. Load zovix_workflow.json fresh from disk (dynamic, no caching).
  2. Inject prompt/negative-prompt/resolution/seed/steps into the right nodes.
  3. POST {"input": {"images": [...], "workflow": {...}}} to
     https://api.runpod.ai/v2/<ENDPOINT_ID>/runsync
  4. If the job doesn't finish inline, fall back to /run + /status polling.
  5. Decode the returned base64 image and save it to the workshop output folder.
==========================================================================
"""
import os
import json
import time
import uuid
import base64
import random
import logging

import requests

logger = logging.getLogger("zovix.comfyui")

# ---------------------------------------------------------------------------
# RunPod serverless configuration
# ---------------------------------------------------------------------------
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.getenv("COMFYUI_RUNPOD_ENDPOINT_ID", "ipb2c2vnew0qbz")
RUNPOD_BASE_URL = os.getenv("RUNPOD_BASE_URL", "https://api.runpod.ai/v2")

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
WORKFLOW_PATH = os.getenv("COMFYUI_WORKFLOW_PATH", os.path.join(_APP_DIR, "zovix_workflow.json"))
WORKSHOP_OUTPUT_DIR = os.getenv("WORKSHOP_OUTPUT_DIR", _APP_DIR)

# Node IDs from zovix_workflow.json (Flux1-dev checkpoint graph)
NODE_POSITIVE_PROMPT = "6"
NODE_NEGATIVE_PROMPT = "33"
NODE_LATENT_IMAGE = "27"
NODE_SAMPLER = "31"
NODE_SAVE_IMAGE = "9"

ASPECT_RATIO_DIMENSIONS = {
    "16:9": (912, 512),
    "9:16": (512, 912),
    "1:1": (512, 512),
    "21:9": (1024, 432),
    "4:5": (512, 640),
    "3:2": (768, 512),
}

QUALITY_STEPS = {"Standard": 10, "HD": 16, "Pro": 24}


def load_workflow():
    """Read zovix_workflow.json fresh from disk on every call."""
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def inject_prompt_settings(workflow, prompt, negative_prompt="", aspect_ratio="16:9", quality="Standard", seed=None):
    """Inject user prompt/settings into the correct nodes of the workflow payload."""
    width, height = ASPECT_RATIO_DIMENSIONS.get(aspect_ratio, (512, 512))
    steps = QUALITY_STEPS.get(quality, 10)
    seed = random.randint(0, 2 ** 31 - 1) if seed is None else seed

    if NODE_POSITIVE_PROMPT in workflow:
        workflow[NODE_POSITIVE_PROMPT]["inputs"]["text"] = prompt

    if NODE_NEGATIVE_PROMPT in workflow:
        workflow[NODE_NEGATIVE_PROMPT]["inputs"]["text"] = (negative_prompt or "").strip()

    if NODE_LATENT_IMAGE in workflow:
        workflow[NODE_LATENT_IMAGE]["inputs"]["width"] = width
        workflow[NODE_LATENT_IMAGE]["inputs"]["height"] = height

    if NODE_SAMPLER in workflow:
        workflow[NODE_SAMPLER]["inputs"]["seed"] = seed
        workflow[NODE_SAMPLER]["inputs"]["steps"] = steps

    return workflow


def _headers(api_key):
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _poll_job(endpoint_id, job_id, api_key, timeout, poll_interval=2):
    status_url = f"{RUNPOD_BASE_URL}/{endpoint_id}/status/{job_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(status_url, headers=_headers(api_key), timeout=30)
        resp.raise_for_status()
        result = resp.json()
        status = result.get("status", "IN_QUEUE")
        if status == "COMPLETED":
            return result
        if status == "FAILED":
            raise RuntimeError(f"RunPod job failed: {result.get('error', 'Unknown error')}")
        time.sleep(poll_interval)
    raise TimeoutError(f"RunPod job {job_id} did not complete within {timeout}s")


def run_comfyui_job(workflow, api_key, endpoint_id, images=None, timeout=180):
    """POST the workflow to RunPod's /runsync, falling back to /run + polling if needed."""
    payload = {"input": {"images": images or [], "workflow": workflow}}

    runsync_url = f"{RUNPOD_BASE_URL}/{endpoint_id}/runsync"
    resp = requests.post(runsync_url, headers=_headers(api_key), json=payload, timeout=min(timeout, 90))
    resp.raise_for_status()
    result = resp.json()

    if result.get("status") == "COMPLETED":
        return result

    if result.get("status") == "FAILED":
        raise RuntimeError(f"RunPod job failed: {result.get('error', 'Unknown error')}")

    job_id = result.get("id")
    if not job_id:
        raise RuntimeError(f"RunPod returned no job id: {result}")

    return _poll_job(endpoint_id, job_id, api_key, timeout)


def _extract_base64_images(output):
    """Normalize the various output shapes RunPod ComfyUI workers may return into a base64 string list."""
    if output is None:
        return []
    if isinstance(output, str):
        return [output]
    if isinstance(output, list):
        found = []
        for item in output:
            if isinstance(item, str):
                found.append(item)
            elif isinstance(item, dict):
                found.append(item.get("data") or item.get("image") or item.get("base64"))
        return [b64 for b64 in found if b64]
    if isinstance(output, dict):
        images = output.get("images")
        if images:
            return _extract_base64_images(images)
        for key in ("image", "data", "base64"):
            if output.get(key):
                return [output[key]]
    return []


def generate_workshop_image(prompt, aspect_ratio="16:9", negative_prompt="", quality="Standard", seed=None,
                             api_key=None, endpoint_id=None, timeout=180):
    """
    Generate an image through the ComfyUI-on-RunPod serverless API and save it
    to the local workshop output folder. Drop-in replacement for the legacy
    Stability AI / Pollinations generate_pro_image() pipeline.

    Returns the local file path on success, or None on failure.
    """
    api_key = (api_key or RUNPOD_API_KEY or "").strip()
    endpoint_id = (endpoint_id or RUNPOD_ENDPOINT_ID or "").strip()

    if not api_key:
        logger.error("RUNPOD_API_KEY not configured; cannot call ComfyUI RunPod endpoint.")
        return None
    if not endpoint_id:
        logger.error("ComfyUI RunPod endpoint id not configured.")
        return None

    try:
        workflow = inject_prompt_settings(load_workflow(), prompt, negative_prompt, aspect_ratio, quality, seed)

        result = run_comfyui_job(workflow, api_key, endpoint_id, timeout=timeout)

        images_b64 = _extract_base64_images(result.get("output"))
        if not images_b64:
            logger.error(f"RunPod ComfyUI job returned no images: {result}")
            return None

        raw_b64 = images_b64[0]
        if "," in raw_b64[:60]:  # strip a data:image/...;base64, prefix if present
            raw_b64 = raw_b64.split(",", 1)[1]
        image_bytes = base64.b64decode(raw_b64)

        os.makedirs(WORKSHOP_OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(WORKSHOP_OUTPUT_DIR, f"workshop_output_{uuid.uuid4().hex[:6]}.png")
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        return output_path

    except Exception as e:
        logger.error(f"ComfyUI RunPod workshop image generation failed: {e}")
        return None
