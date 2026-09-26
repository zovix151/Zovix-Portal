import os
import base64
import uuid
import runpod
# Apne LivePortrait pipeline ko yahan import karein
from liveportrait.pipeline.live_portrait_pipeline import LivePortraitPipeline

# Pipeline initialize kar rahe hain
pipeline = LivePortraitPipeline()

WORK_DIR = os.getenv("RUNPOD_WORK_DIR", "/tmp/zovix_face_jobs")
os.makedirs(WORK_DIR, exist_ok=True)


def _decode_base64_file(value, output_path):
    """Decode raw base64 or a data URI into a local input file."""
    if not value:
        raise ValueError("Missing input file payload")
    encoded = value.split(",", 1)[1] if value.startswith("data:") else value
    with open(output_path, "wb") as output_file:
        output_file.write(base64.b64decode(encoded, validate=True))
    return output_path


def _encode_video(output_path):
    if output_path and not os.path.isabs(output_path):
        output_path = os.path.abspath(output_path)
    if not output_path or not os.path.exists(output_path):
        raise FileNotFoundError("Video file not found after processing")
    with open(output_path, "rb") as video_file:
        return base64.b64encode(video_file.read()).decode("ascii")


def handler(job):
    job_input = job.get("input", {})
    job_id = job.get("id", uuid.uuid4().hex)
    image_path = os.path.join(WORK_DIR, f"{job_id}_face.png")
    audio_path = os.path.join(WORK_DIR, f"{job_id}_audio.wav")
    output_path = None

    try:
        image_value = job_input.get("image_base64") or job_input.get("source_image")
        audio_value = job_input.get("wav_base64") or job_input.get("driven_audio")
        if not image_value or not audio_value:
            raise ValueError("image_base64 and wav_base64 are required")

        _decode_base64_file(image_value, image_path)
        _decode_base64_file(audio_value, audio_path)
        output_path = pipeline.execute(image_path, audio_path)
        if not output_path:
            output_path = os.path.join(os.getcwd(), "output.mp4")
        if not os.path.exists(output_path):
            output_candidates = [
                os.path.join(WORK_DIR, "output.mp4"),
                os.path.join("/tmp", "output.mp4"),
            ]
            output_path = next((candidate for candidate in output_candidates if os.path.exists(candidate)), output_path)
        encoded_video = _encode_video(output_path)
        return {
            "status": "COMPLETED",
            "video_base64": encoded_video,
            "output": {"video_base64": encoded_video},
            "message": "LivePortrait processed successfully",
        }
    except Exception as e:
        print(f"Error during execution: {str(e)}")
        return {
            "status": "FAILED",
            "error": str(e),
            "message": str(e),
        }
    finally:
        for path in (image_path, audio_path, output_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

runpod.serverless.start({"handler": handler})