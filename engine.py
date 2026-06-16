import os
import time
import uuid
import sqlite3
import random
import json
import subprocess
import shutil
import requests
import traceback
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Tuple

try:
    import razorpay
    has_razorpay = True
except ImportError:
    razorpay = None
    has_razorpay = False

try:
    from google import genai
    from google.genai import types
    has_genai = True
except Exception:
    genai = None
    types = None
    has_genai = False

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    from mutagen.mp3 import MP3
except ImportError:
    MP3 = None

load_dotenv()


def get_system_secret(key: str, default_val: Optional[str] = None) -> Optional[str]:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default_val)


RAZORPAY_KEY_ID = get_system_secret("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = get_system_secret("RAZORPAY_KEY_SECRET")
PIXABAY_API_KEY = get_system_secret("PIXABAY_API_KEY")
ELEVENLABS_API_KEY = get_system_secret("ELEVENLABS_API_KEY")
GEMINI_API_KEY = get_system_secret("GEMINI_API_KEY")

if has_razorpay and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    except Exception:
        razorpay_client = None
else:
    razorpay_client = None


class SceneDetail(BaseModel):
    scene_text: str = Field(description="The portion of script written specifically for this scene narration.")
    search_keyword: str = Field(description="Strictly ONE single premium English search word for search databases matching the visual context.")
    duration: int = Field(description="Estimated duration in seconds for this scene segment.")


class VideoScriptBreakdown(BaseModel):
    scenes: List[SceneDetail]
    music_mood: str = Field(description="The emotional mood/vibe for background music: 'uplifting', 'dramatic', 'calm', 'energetic', 'mysterious', or 'cinematic'.")


MOOD_TO_MUSIC_MAP: Dict[str, str] = {
    "uplifting": "assets/music/uplifting.mp3",
    "dramatic": "assets/music/dramatic.mp3",
    "calm": "assets/music/calm.mp3",
    "energetic": "assets/music/energetic.mp3",
    "mysterious": "assets/music/mysterious.mp3",
    "cinematic": "assets/music/cinematic.mp3",
}


@st.cache_resource
def verify_system_folders() -> str:
    os.makedirs("saved_renders", exist_ok=True)
    os.makedirs("temp_scenes", exist_ok=True)
    os.makedirs("assets", exist_ok=True)
    return "Ready"


def init_database() -> None:
    conn = sqlite3.connect("vidix_studio.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            credits INTEGER DEFAULT 100
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            file_name TEXT,
            timestamp TEXT,
            prompt TEXT,
            path TEXT
        )
        """
    )
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, password, credits) VALUES ('prabhat', 'vidix123', 100)"
    )
    conn.commit()
    conn.close()


def authenticate_user_db(username: str, password: str) -> bool:
    conn = sqlite3.connect("vidix_studio.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return bool(row and row[0] == password)


def register_user_db(username: str, password: str) -> bool:
    conn = sqlite3.connect("vidix_studio.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, credits) VALUES (?, ?, 100)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user_credits_db(username: str) -> int:
    conn = sqlite3.connect("vidix_studio.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT credits FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0


def update_user_credits_db(username: str, amount: int) -> None:
    conn = sqlite3.connect("vidix_studio.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET credits = credits + ? WHERE username = ?", (amount, username))
    conn.commit()
    conn.close()


def save_render_to_db(username: str, file_name: str, prompt: str, path: str) -> None:
    conn = sqlite3.connect("vidix_studio.db", check_same_thread=False)
    cursor = conn.cursor()
    timestamp = time.strftime("%b %d, %Y - %I:%M %p")
    cursor.execute(
        "INSERT INTO history (username, file_name, timestamp, prompt, path) VALUES (?, ?, ?, ?, ?)",
        (username, file_name, timestamp, prompt, path),
    )
    conn.commit()
    conn.close()


def load_renders_history_db(username: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect("vidix_studio.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT file_name, timestamp, prompt, path FROM history WHERE username = ? ORDER BY id DESC",
        (username,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "file_name": row[0],
            "timestamp": row[1],
            "prompt": row[2],
            "path": row[3],
        }
        for row in rows
    ]


def create_payment_order(amount_paise: int) -> Dict[str, Any]:
    if razorpay_client and RAZORPAY_KEY_ID:
        try:
            data = {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": f"receipt_{int(time.time())}",
            }
            return razorpay_client.order.create(data=data)
        except Exception:
            pass
    return {"id": f"order_mock_{uuid.uuid4().hex[:8]}", "amount": amount_paise}


def get_music_path(mood: str) -> str:
    base_path = os.path.join("assets", "music")
    target_path = os.path.join(base_path, f"{mood}.mp3")
    default_path = os.path.join(base_path, "default.mp3")
    return target_path if os.path.exists(target_path) else default_path


@st.cache_resource
def get_hwaccel_args() -> List[str]:
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-hwaccel", "auto", "-h"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return ["-hwaccel", "auto"] if result.returncode == 0 else []
    except Exception:
        return []


def get_audio_duration(audio_path: str) -> float:
    try:
        if MP3 is not None:
            audio = MP3(audio_path)
            return float(audio.info.length)
    except Exception:
        pass
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 5.0


def parse_tagged_script(script_text: str) -> List[Dict[str, Any]]:
    paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]
    scenes_mapped: List[Dict[str, Any]] = []
    for para in paragraphs:
        keyword = "mystery"
        clean_text = para
        if "[" in para and "]" in para:
            start_idx = para.find("[")
            end_idx = para.find("]")
            tag_content = para[start_idx + 1 : end_idx]
            clean_text = para[end_idx + 1 :].strip()
            keyword = tag_content.split(":")[-1].strip() if ":" in tag_content else tag_content.strip()
        else:
            para_lower = para.lower()
            if "haveli" in para_lower or "palace" in para_lower or "castle" in para_lower:
                keyword = "palace"
            elif "darkness" in para_lower or "dark" in para_lower or "shadow" in para_lower:
                keyword = "darkness"
            elif "secret" in para_lower or "mystery" in para_lower:
                keyword = "mystery"
            else:
                words = [w.strip(",.?!\"'" ) for w in para.split() if len(w) > 4]
                stopwords = {"there", "their", "about", "would", "could", "should", "under", "these"}
                valid_words = [w for w in words if w.lower() not in stopwords]
                if valid_words:
                    keyword = random.choice(valid_words)
        scenes_mapped.append({"scene_text": clean_text, "search_keyword": keyword, "duration": 5})
    return scenes_mapped


def run_async_in_thread(coro: Any) -> Any:
    result: List[Any] = []
    exception: List[Exception] = []

    def target() -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            res = loop.run_until_complete(coro)
            result.append(res)
        except Exception as e:
            exception.append(e)
        finally:
            loop.close()

    thread = threading.Thread(target=target)
    thread.start()
    thread.join()
    if exception:
        raise exception[0]
    return result[0] if result else None


@st.cache_data(show_spinner=False, max_entries=16)
def generate_ai_script_and_scenes(topic: str, duration_choice: str, selected_model: str, language_choice: str) -> Tuple[List[Dict[str, Any]], str]:
    if has_genai and GEMINI_API_KEY:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            num_scenes = 4 if "1 Minute" in duration_choice else 3
            lang_instruction = "fluent Hinglish (Hindi written in Latin script)" if "Hinglish" in language_choice else "clear modern English"
            prompt = (
                f"Write a premium engaging short video script about '{topic}' in {lang_instruction}. "
                f"Divide the video into exactly {num_scenes} sequential scenes. "
                f"Each scene must contain unique descriptive text and a single keyword search tag matching the visual mood. "
                f"Also, determine the overall emotional mood/vibe for background music for this video. "
                f"Choose ONE of: 'uplifting', 'dramatic', 'calm', 'energetic', 'mysterious', or 'cinematic'. "
                f"Return this as a 'music_mood' field in the JSON response."
            )
            response = client.models.generate_content(
                model=selected_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VideoScriptBreakdown,
                    temperature=0.7,
                ),
            )
            data = json.loads(response.text)
            scenes_mapped: List[Dict[str, Any]] = [
                {
                    "scene_text": item.get("scene_text", "").strip(),
                    "search_keyword": item.get("search_keyword", "mystery").strip(),
                    "duration": item.get("duration", 5),
                }
                for item in data.get("scenes", [])
            ]
            music_mood = data.get("music_mood", "cinematic").lower().strip()
            if scenes_mapped:
                return scenes_mapped, music_mood
        except Exception:
            pass

    if "English" in language_choice:
        fallback_text = (
            f"[Scene 1: space] Discover the incredible mysteries surrounding {topic} that science cannot explain.\n\n"
            f"[Scene 2: history] Hidden deep within forgotten records lies a dark secret.\n\n"
            f"[Scene 3: laboratory] Today, modern technology is finally revealing the truth."
        )
    else:
        fallback_text = (
            f"[Scene 1: universe] {topic} ke baare mein kuch aise hairan kar dene wale rahasya jo sabhi se chupaye gaye.\n\n"
            f"[Scene 2: mystery] Purani dastawezon mein dabi ek aisi sachai jise koi nahi janta.\n\n"
            f"[Scene 3: hologram] Aaj ke modern scientists is ghabrahat bhare sach ko bahar la rahe hain."
        )
    return parse_tagged_script(fallback_text), "cinematic"


@st.cache_data(show_spinner=False, max_entries=64)
def fetch_pixabay_hits(query: str) -> Optional[Dict[str, Any]]:
    if not PIXABAY_API_KEY or PIXABAY_API_KEY == "YOUR_PIXABAY_API_KEY":
        return None
    clean_query = query.replace('"', '').replace("'", "").strip()
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={clean_query}&per_page=10&video_type=film"
    try:
        res = requests.get(url, timeout=12)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None


def generate_elevenlabs_speech(text: str, output_filename: str, voice_id: str) -> bool:
    if not ELEVENLABS_API_KEY:
        return False
    safe_remove_file(output_filename)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY,
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    try:
        box = requests.post(url, json=data, headers=headers, timeout=30)
        if box.status_code == 200:
            with open(output_filename, "wb") as f:
                f.write(box.content)
            return True
    except Exception:
        pass
    return False


def run_fallback_tts(text: str, output_filename: str, language_choice: str, voice_profile: str) -> None:
    safe_remove_file(output_filename)
    is_male = "Drew" in voice_profile or "Male" in voice_profile
    if "English" in language_choice:
        voice_name = "en-US-GuyNeural" if is_male else "en-US-AriaNeural"
    else:
        voice_name = "hi-IN-MadhurNeural" if is_male else "hi-IN-SwaraNeural"
    if edge_tts is not None:
        run_async_in_thread(edge_tts.Communicate(text, voice_name).save(output_filename))


def fetch_pixabay_video_clip(query: str, output_filename: str) -> bool:
    safe_remove_file(output_filename)
    response = fetch_pixabay_hits(query)
    if response is None or "hits" not in response:
        return False
    try:
        hits = response["hits"]
        if not hits:
            return False
        selected_video = random.choice(hits)
        videos_dict = selected_video.get("videos", {})
        target_video = videos_dict.get("medium") or videos_dict.get("small") or videos_dict.get("large")
        if target_video and "url" in target_video:
            video_url = target_video["url"]
            with requests.get(video_url, stream=True, timeout=15) as r:
                with open(output_filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return os.path.exists(output_filename) and os.path.getsize(output_filename) > 100000
    except Exception:
        pass
    return False


def get_premium_local_backup(output_filename: str) -> bool:
    local_dir = "local_assets"
    if os.path.isdir(local_dir):
        files = [os.path.join(local_dir, f) for f in os.listdir(local_dir) if f.endswith(".mp4")]
        if files:
            chosen = random.choice(files)
            try:
                shutil.copy(chosen, output_filename)
                return True
            except Exception:
                pass
    return False


def create_emergency_solid_clip(output_filename: str, duration: float, res_width: int, res_height: int) -> bool:
    safe_remove_file(output_filename)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=#050508:s={res_width}x{res_height}:r=24",
        "-t",
        str(duration),
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        output_filename,
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False


def create_emergency_silent_audio(output_filename: str, duration: float) -> bool:
    safe_remove_file(output_filename)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=stereo",
        "-t",
        str(duration),
        "-c:a",
        "libmp3lame",
        output_filename,
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False


def safe_remove_file(file_path: str) -> None:
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass


def convert_mp4_to_webm(mp4_path: str, webm_path: str) -> bool:
    safe_remove_file(webm_path)
    cmd = [
        "ffmpeg",
        *get_hwaccel_args(),
        "-y",
        "-i",
        mp4_path,
        "-c:v",
        "libvpx-vp9",
        "-crf",
        "32",
        "-b:v",
        "0",
        "-c:a",
        "libopus",
        webm_path,
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        try:
            cmd = [
                "ffmpeg",
                *get_hwaccel_args(),
                "-y",
                "-i",
                mp4_path,
                "-c:v",
                "libvpx",
                "-crf",
                "10",
                "-b:v",
                "1M",
                "-c:a",
                "libvorbis",
                webm_path,
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except Exception:
            return False


def build_scene_stitched_video_isolated(
    scenes_data: List[Dict[str, Any]],
    video_output: str,
    size_choice: str,
    voice_profile: str,
    language_choice: str,
    bgm_path: Optional[str] = None,
    bgm_volume: float = 0.3,
    music_mood: Optional[str] = None,
) -> bool:
    safe_remove_file(video_output)
    res_width, res_height = 720, 1280
    if "16:9" in size_choice:
        res_width, res_height = 1280, 720
    elif "1:1" in size_choice:
        res_width, res_height = 1080, 1080

    workspace_dir = os.path.join("temp_scenes", f"workspace_{uuid.uuid4().hex}")
    os.makedirs(workspace_dir, exist_ok=True)
    compiled_scenes_paths: List[str] = []

    if music_mood:
        print(f"[build_scene_stitched_video_isolated] Building with music mood: '{music_mood}'")

    def process_scene_segment(idx: int, scene: Dict[str, Any]) -> Optional[str]:
        text = scene.get("scene_text", "")
        kw = scene.get("search_keyword", "mystery")

        audio_segment_path = os.path.join(workspace_dir, f"temp_voice_{idx}.mp3")
        selected_voice_id = "21m00Tcm4TlvDq8ikWAM" if "Drew" in voice_profile else "pNInz6obpgDQ5IdwJg7p"
        voice_built = False

        if ELEVENLABS_API_KEY:
            voice_built = generate_elevenlabs_speech(text, audio_segment_path, selected_voice_id)
        if not voice_built:
            run_fallback_tts(
                text=text,
                output_filename=audio_segment_path,
                language_choice=language_choice,
                voice_profile=voice_profile,
            )

        if not os.path.exists(audio_segment_path) or os.path.getsize(audio_segment_path) == 0:
            create_emergency_silent_audio(audio_segment_path, 5.0)

        dur = get_audio_duration(audio_segment_path)
        if dur <= 0:
            dur = 5.0

        raw_video_path = os.path.join(workspace_dir, f"temp_raw_vid_{idx}.mp4")
        success = fetch_pixabay_video_clip(kw, raw_video_path)
        if not success or not os.path.exists(raw_video_path) or os.path.getsize(raw_video_path) < 100000:
            success = get_premium_local_backup(raw_video_path)

        if not success or not os.path.exists(raw_video_path):
            filler_path = "assets/filler.mp4"
            if os.path.exists(filler_path) and os.path.getsize(filler_path) > 100000:
                try:
                    shutil.copy(filler_path, raw_video_path)
                    success = True
                except Exception:
                    success = False

        if not success or not os.path.exists(raw_video_path):
            create_emergency_solid_clip(raw_video_path, dur, res_width, res_height)

        segment_mux_path = os.path.join(workspace_dir, f"temp_seg_mux_{idx}.mp4")
        ff_cmd = [
            "ffmpeg",
            *get_hwaccel_args(),
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            raw_video_path,
            "-i",
            audio_segment_path,
            "-t",
            f"{dur:.2f}",
            "-vf",
            f"scale={res_width}:{res_height}:force_original_aspect_ratio=increase,crop={res_width}:{res_height},setsar=1,eq=saturation=1.15:contrast=1.05,fade=t=in:st=0:d=0.4,fade=t=out:st={dur-0.4:.2f}:d=0.4",
            "-af",
            f"afade=t=in:ss=0:d=0.4,afade=t=out:st={dur-0.4:.2f}:d=0.4",
            "-r",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            segment_mux_path,
        ]
        try:
            subprocess.run(ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(segment_mux_path) and os.path.getsize(segment_mux_path) > 0:
                return segment_mux_path
        except Exception:
            fallback_cmd = [
                "ffmpeg",
                *get_hwaccel_args(),
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                raw_video_path,
                "-i",
                audio_segment_path,
                "-t",
                f"{dur:.2f}",
                "-vf",
                f"scale={res_width}:{res_height}:force_original_aspect_ratio=increase,crop={res_width}:{res_height},setsar=1",
                "-r",
                "24",
                "-pix_fmt",
                "yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-c:a",
                "aac",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-shortest",
                segment_mux_path,
            ]
            try:
                subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                if os.path.exists(segment_mux_path) and os.path.getsize(segment_mux_path) > 0:
                    return segment_mux_path
            except Exception:
                pass
        return None

    try:
        max_workers = min(len(scenes_data), max(1, os.cpu_count() or 1))
        segment_results: Dict[int, Optional[str]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(process_scene_segment, idx, scene): idx
                for idx, scene in enumerate(scenes_data)
            }
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    scene_path = future.result()
                except Exception as exc:
                    print(f"[build_scene_stitched_video_isolated] Scene {idx} failed: {exc}")
                    scene_path = None
                segment_results[idx] = scene_path

        for idx in range(len(scenes_data)):
            scene_path = segment_results.get(idx)
            if scene_path:
                compiled_scenes_paths.append(scene_path)
            else:
                fill_clip = os.path.join(workspace_dir, f"temp_seg_mux_{idx}_fill.mp4")
                create_emergency_solid_clip(fill_clip, 5.0, res_width, res_height)
                compiled_scenes_paths.append(fill_clip)

        validated_scenes: List[str] = []
        for path in compiled_scenes_paths:
            if os.path.exists(path) and os.path.getsize(path) > 1000:
                validated_scenes.append(path)
            else:
                fill_clip = path.replace(".mp4", "_fill.mp4")
                create_emergency_solid_clip(fill_clip, 5.0, res_width, res_height)
                validated_scenes.append(fill_clip)

        if not validated_scenes:
            return False

        manifest_file = os.path.join(workspace_dir, "concat_manifest.txt")
        with open(manifest_file, "w") as f:
            for path in validated_scenes:
                clean_path = os.path.abspath(path).replace("\\", "/")
                f.write(f"file '{clean_path}'\n")

        temp_stitched_output = os.path.join(workspace_dir, "temp_voice_stitched.mp4")
        concat_cmd = [
            "ffmpeg",
            *get_hwaccel_args(),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            manifest_file,
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            temp_stitched_output,
        ]
        subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        if bgm_path and os.path.exists(bgm_path):
            mix_cmd = [
                "ffmpeg",
                *get_hwaccel_args(),
                "-y",
                "-i",
                temp_stitched_output,
                "-stream_loop",
                "-1",
                "-i",
                bgm_path,
                "-filter_complex",
                f"[0:a]volume=1.0[a0];[1:a]volume={bgm_volume}[a1];[a0][a1]amix=inputs=2:duration=first[aout]",
                "-map",
                "0:v:0",
                "-map",
                "[aout]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                video_output,
            ]
            try:
                subprocess.run(mix_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            except Exception:
                shutil.copy(temp_stitched_output, video_output)
        else:
            shutil.copy(temp_stitched_output, video_output)

        return os.path.exists(video_output) and os.path.getsize(video_output) > 1000
    except Exception:
        return False
    finally:
        try:
            shutil.rmtree(workspace_dir, ignore_errors=True)
        except Exception:
            pass
