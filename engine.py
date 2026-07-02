import os
import time
import uuid
import random
import json
import subprocess
import shutil
import requests
import traceback
import asyncio
import threading
import concurrent.futures
import urllib.parse
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field
import edge_tts
from mutagen.mp3 import MP3
from PIL import Image, ImageDraw
import streamlit as st

# --- SAFELY RESOLVE STREAMLIT THREADING CONTEXT ---
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_context
except ImportError:
    try:
        from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx, add_script_run_context
    except ImportError:
        get_script_run_ctx = lambda: None
        add_script_run_context = lambda thread, ctx: None

# --- SAFE IMPORTS FOR OPTIONAL PACKAGES ---
try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

try:
    from google import genai
    from google.genai import types
    has_genai = True
except Exception:
    genai = None
    types = None
    has_genai = False

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
PEXELS_API_KEY = get_system_secret("PEXELS_API_KEY")
STABILITY_API_KEY = get_system_secret("STABILITY_API_KEY")
ELEVENLABS_API_KEY = get_system_secret("ELEVENLABS_API_KEY")
GEMINI_API_KEY = get_system_secret("GEMINI_API_KEY")
LUMA_API_KEY = get_system_secret("LUMA_API_KEY")
RUNWAY_API_KEY = get_system_secret("RUNWAY_API_KEY")
HUGGINGFACE_API_KEY = get_system_secret("HUGGINGFACE_API_KEY")
DEEPSEEK_API_KEY = get_system_secret("DEEPSEEK_API_KEY")
REPLICATE_API_KEY = get_system_secret("REPLICATE_API_KEY")
TRIPO_API_KEY = get_system_secret("TRIPO_API_KEY")  

class SceneDetail(BaseModel):
    scene_text: str = Field(description="The portion of script written specifically for this scene narration.")
    search_keyword: str = Field(description="Strictly 2 to 4 premium English descriptive keywords. Do not use Hindi language words.")
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

def get_music_path(mood: str) -> str:
    base_path = os.path.join("assets", "music")
    target_path = os.path.join(base_path, f"{mood.lower()}.mp3")
    default_path = os.path.join(base_path, "default.mp3")
    return target_path if os.path.exists(target_path) else default_path

def get_audio_duration(audio_path: str) -> float:
    try:
        audio = MP3(audio_path)
        return float(audio.info.length)
    except Exception:
        try:
            cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return float(result.stdout.strip())
        except Exception:
            return 5.0

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

def get_video_resolution(video_path: str) -> Tuple[Optional[int], Optional[int]]:
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        res_split = result.stdout.strip().split('x')
        if len(res_split) == 2:
            return int(res_split[0]), int(res_split[1])
    except Exception:
        pass
    return None, None

def parse_tagged_script(script_text: str) -> List[Dict[str, Any]]:
    paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]
    scenes_mapped = []
    for para in paragraphs:
        keyword = "mystery"
        clean_text = para
        if "[" in para and "]" in para:
            start_idx = para.find("[")
            end_idx = para.find("]")
            tag_content = para[start_idx+1:end_idx]
            clean_text = para[end_idx+1:].strip()
            keyword = tag_content.split(":")[-1].strip() if ":" in tag_content else tag_content.strip()
        else:
            para_lower = para.lower()
            if any(x in para_lower for x in ["haveli", "palace", "castle"]):
                keyword = "palace"
            elif any(x in para_lower for x in ["darkness", "dark", "shadow"]):
                keyword = "darkness"
            elif any(x in para_lower for x in ["secret", "mystery"]):
                keyword = "mystery"
            else:
                words = [w.strip(",.?!\"'") for w in para.split() if len(w) > 4]
                stopwords = {"there", "their", "about", "would", "could", "should", "under", "these"}
                valid_words = [w for w in words if w.lower() not in stopwords]
                if valid_words:
                    keyword = " ".join(valid_words[:3])
        scenes_mapped.append({
            "scene_text": clean_text,
            "search_keyword": keyword,
            "duration": 5
        })
    return scenes_mapped

def run_async_in_thread(coro: Any) -> Any:
    result, exception = [], []
    def target():
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

class ScriptingEngine:
    @staticmethod
    def generate_script(topic: str, duration_choice: str, selected_model: str, language_choice: str) -> Tuple[List[Dict[str, Any]], str]:
        if has_genai and GEMINI_API_KEY:
            try:
                client_gen = genai.Client(api_key=GEMINI_API_KEY)
                num_scenes = 4 if "1 Minute" in duration_choice else 3
                lang_instruction = "fluent Hinglish (Hindi written in Latin script)" if "Hinglish" in language_choice else "clear modern English"
                
                prompt = (
                    f"Write a premium engaging short video script about '{topic}' in {lang_instruction}. "
                    f"Divide the video into exactly {num_scenes} sequential scenes. "
                    f"Each scene must contain unique descriptive text and a short English search keyword phrase (strictly 2 to 4 words) matching the visual context. "
                    f"Strictly avoid full sentences, verbs, or Hindi language words in the search_keyword field. "
                    f"Also, determine the overall emotional mood/vibe for background music for this video. "
                    f"Choose ONE of: 'uplifting', 'dramatic', 'calm', 'energetic', 'mysterious', or 'cinematic'. "
                    f"Return this as a 'music_mood' field in the JSON response."
                )
                
                response = client_gen.models.generate_content(
                    model=selected_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=VideoScriptBreakdown,
                        temperature=0.7
                    )
                )
                
                data = json.loads(response.text)
                scenes_mapped = []
                for item in data.get("scenes", []):
                    kw = item.get("search_keyword", "mystery").strip()
                    if len(kw.split()) > 5 or "." in kw:
                        kw = " ".join(kw.split()[:3]).replace(".", "")
                    scenes_mapped.append({
                        "scene_text": item.get("scene_text", "").strip(),
                        "search_keyword": kw,
                        "duration": item.get("duration", 5)
                    })
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

class VisualEngine:
    @staticmethod
    def fetch_pexels_clip(query: str, output_filename: str) -> bool:
        pexels_key = os.getenv("PEXELS_API_KEY") or get_system_secret("PEXELS_API_KEY")
        if not pexels_key:
            return False
        safe_remove_file(output_filename)
        clean_query = query.replace('"', '').replace("'", "").strip()
        url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(clean_query)}&per_page=1"
        headers = {"Authorization": pexels_key}
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                videos = data.get("videos", [])
                if videos:
                    video_files = videos[0].get("video_files", [])
                    if video_files:
                        video_url = video_files[0].get("link")
                        if video_url:
                            with requests.get(video_url, stream=True, timeout=15) as r:
                                with open(output_filename, 'wb') as f:
                                    for chunk in r.iter_content(chunk_size=8192):
                                        f.write(chunk)
                            return os.path.exists(output_filename) and os.path.getsize(output_filename) > 100000
        except Exception:
            pass
        return False

    @staticmethod
    def fetch_pixabay_clip(query: str, output_filename: str) -> bool:
        pixabay_key = os.getenv("PIXABAY_API_KEY") or get_system_secret("PIXABAY_API_KEY")
        if not pixabay_key:
            return False
        safe_remove_file(output_filename)
        clean_query = query.replace('"', '').replace("'", "").strip().split()[0]
        url = f"https://pixabay.com/api/videos/?key={pixabay_key}&q={clean_query}&per_page=10&video_type=film"
        try:
            res = requests.get(url, timeout=12)
            if res.status_code == 200:
                response = res.json()
                if "hits" in response and len(response["hits"]) > 0:
                    selected_video = random.choice(response["hits"])
                    videos_dict = selected_video.get("videos", {})
                    target_video = videos_dict.get("medium") or videos_dict.get("small") or videos_dict.get("large")
                    if target_video and "url" in target_video:
                        video_url = target_video["url"]
                        with requests.get(video_url, stream=True, timeout=15) as r:
                            with open(output_filename, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192): 
                                    f.write(chunk)
                        return os.path.exists(output_filename) and os.path.getsize(output_filename) > 100000
        except Exception: 
            pass
        return False

    @staticmethod
    def generate_sd_core_image(prompt: str, output_filename: str, aspect_ratio_str: str = "9:16") -> bool:
        st_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")
        sd_aspect = "9:16"
        if "16:9" in aspect_ratio_str:
            sd_aspect = "16:9"
        elif "1:1" in aspect_ratio_str:
            sd_aspect = "1:1"
            
        safe_remove_file(output_filename)
        
        if st_key and st_key != "mock" and len(st_key.strip()) > 5:
            url = "https://api.stability.ai/v2beta/stable-image/generate/core"
            headers = {"authorization": f"Bearer {st_key}", "accept": "image/*"}
            data = {"prompt": f"Cinematic masterpiece, highly detailed: {prompt}", "output_format": "png", "aspect_ratio": sd_aspect}
            try:
                files = {k: (None, str(v)) for k, v in data.items()}
                response = requests.post(url, headers=headers, files=files, timeout=25)
                if response.status_code == 200 and len(response.content) > 10000:
                    with open(output_filename, "wb") as f:
                        f.write(response.content)
                    return True
            except Exception:
                pass
                
        try:
            width, height = 768, 1344
            if sd_aspect == "16:9":
                width, height = 1344, 768
            elif sd_aspect == "1:1":
                width, height = 1024, 1024
                
            clean_prompt = prompt.replace('"', '').replace("'", "").strip()
            encoded_prompt = urllib.parse.quote(f"Cinematic masterpiece, highly detailed: {clean_prompt}")
            poll_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width={width}&height={height}&seed={random.randint(1, 999999)}&nologo=true"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
            }
            response = requests.get(poll_url, headers=headers, timeout=25)
            if response.status_code == 200 and len(response.content) > 10000:
                with open(output_filename, "wb") as f:
                    f.write(response.content)
                return True
        except Exception:
            pass
            
        return False

    @staticmethod
    def convert_image_to_video(image_path: str, output_video_path: str, duration: float, res_width: int, res_height: int) -> bool:
        safe_remove_file(output_video_path)
        cmd = [
            'ffmpeg', '-y', '-loop', '1', '-i', image_path,
            '-t', f"{duration:.2f}",
            '-vf', f'scale={res_width}:{res_height}:force_original_aspect_ratio=increase,crop={res_width}:{res_height},setsar=1',
            '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-r', '24', output_video_path
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except Exception:
            return False

class AudioEngine:
    @staticmethod
    def generate_elevenlabs_speech(text: str, output_filename: str, voice_id: str) -> bool:
        eleven_key = os.getenv("ELEVENLABS_API_KEY") or get_system_secret("ELEVENLABS_API_KEY")
        if not eleven_key:
            return False
        safe_remove_file(output_filename)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": eleven_key}
        data = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
        try:
            box = requests.post(url, json=data, headers=headers, timeout=30)
            if box.status_code == 200:
                with open(output_filename, "wb") as f: 
                    f.write(box.content)
                return True
        except Exception: 
            pass
        return False

    @staticmethod
    def run_fallback_tts(text: str, output_filename: str, language_choice: str, voice_profile: str) -> None:
        safe_remove_file(output_filename)
        is_male = "Drew" in voice_profile or "Male" in voice_profile
        if "English" in language_choice:
            voice_name = "en-US-GuyNeural" if is_male else "en-US-AriaNeural"
        else:
            voice_name = "hi-IN-MadhurNeural" if is_male else "hi-IN-SwaraNeural"
        run_async_in_thread(edge_tts.Communicate(text, voice_name).save(output_filename))

class StitcherEngine:
    @staticmethod
    def generate_ai_video(image_path: str, output_video_path: str) -> bool:
        stability_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")
        if not stability_key:
            return False
            
        url = "https://api.stability.ai/v2beta/image-to-video"
        headers = {"authorization": f"Bearer {stability_key}"}
        try:
            with open(image_path, "rb") as img_file:
                files = {"image": img_file}
                data = {"seed": 0, "cfg_scale": 1.8, "motion_bucket_id": 127}
                response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                
            if response.status_code != 200:
                return False
                
            generation_id = response.json().get("id")
            if not generation_id:
                return False
                
            result_url = f"https://api.stability.ai/v2beta/image-to-video/result/{generation_id}"
            headers_get = {"authorization": f"Bearer {stability_key}", "accept": "video/*"}
            
            for _ in range(12):
                time.sleep(5)
                res = requests.get(result_url, headers=headers_get, timeout=20)
                if res.status_code == 202:
                    continue
                elif res.status_code == 200:
                    with open(output_video_path, "wb") as f:
                        f.write(res.content)
                    return True
                else:
                    break
        except Exception:
            pass
        return False

    @staticmethod
    def generate_smart_fallback_motion(text: str, image_path: Optional[str], output_video_path: str, status_dict: Optional[dict] = None) -> bool:
        os.makedirs("temp_scenes", exist_ok=True)
        safe_remove_file(output_video_path)

        if status_dict is not None:
            status_dict["status_text"] = "Rendering fallback movement..."
            
        fallback_source_image = image_path
        if not fallback_source_image or not os.path.exists(fallback_source_image):
            fallback_source_image = os.path.join("temp_scenes", f"temp_solid_canvas_{uuid.uuid4().hex[:6]}.png")
            cmd_img = [
                'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=#050508:s=1280x720',
                '-vframes', '1', fallback_source_image
            ]
            subprocess.run(cmd_img, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            cmd = [
                'ffmpeg', '-y', '-loop', '1', '-i', fallback_source_image,
                '-t', '5',
                '-vf', "zoompan=z='min(zoom+0.0018,1.5)':d=120:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720",
                '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-r', '24', output_video_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 1000:
                return True
        except Exception:
            pass

        return create_emergency_solid_clip(output_video_path, 5.0, 1280, 720)

    @staticmethod
    def build_scene_stitched_video_isolated(
        scenes_data: List[Dict[str, Any]],
        video_output: str,
        size_choice: str,
        voice_profile: str,
        language_choice: str,
        bgm_path: Optional[str] = None,
        bgm_volume: float = 0.3,
        music_mood: Optional[str] = None,
        status_dict: Optional[dict] = None,
        ctx: Optional[Any] = None
    ) -> bool:
        safe_remove_file(video_output)
        res_width, res_height = 720, 1280  
        if "16:9" in size_choice: 
            res_width, res_height = 1280, 720
        elif "1:1" in size_choice: 
            res_width, res_height = 1080, 1080
            
        session_workspace_id = f"workspace_{uuid.uuid4().hex}"
        workspace_dir = os.path.join("temp_scenes", session_workspace_id)
        os.makedirs(workspace_dir, exist_ok=True)
        compiled_scenes_paths = []
        
        def process_scene_segment(idx: int, scene: Dict[str, Any]) -> Optional[str]:
            # Attaches Streamlit's script execution context to avoid runtime container errors
            if ctx:
                add_script_run_context(threading.current_thread(), ctx)

            text = scene["scene_text"]
            kw = scene["search_keyword"]

            if status_dict is not None:
                status_dict["status_text"] = f"Scene {idx+1}: Synthesizing vocal track..."

            audio_segment_path = os.path.join(workspace_dir, f"temp_voice_{idx}.mp3")
            voice_built = False
            selected_voice_id = "21m00Tcm4TlvDq8ikWAM" if "Drew" in voice_profile else "pNInz6obpgDQ5IdwJg7p"

            if ELEVENLABS_API_KEY:
                voice_built = AudioEngine.generate_elevenlabs_speech(text, audio_segment_path, selected_voice_id)
            if not voice_built:
                AudioEngine.run_fallback_tts(
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
            
            # Stock Media Search
            if status_dict is not None:
                status_dict["status_text"] = f"Scene {idx+1}: Locating stock frames..."
            success = VisualEngine.fetch_pexels_clip(kw, raw_video_path)
            if not success:
                success = VisualEngine.fetch_pixabay_clip(kw, raw_video_path)
            if not success:
                success = get_premium_local_backup(raw_video_path)

            # High Fidelity Fallback Rendering
            if not success or not os.path.exists(raw_video_path) or os.path.getsize(raw_video_path) < 1000:
                if status_dict is not None:
                    status_dict["status_text"] = f"Scene {idx+1}: Sourcing base art frame..."
                sd_temp_img = os.path.join(workspace_dir, f"temp_sd_base_{idx}.png")
                sd_success = VisualEngine.generate_sd_core_image(text, sd_temp_img, size_choice)
                
                StitcherEngine.generate_smart_fallback_motion(
                    text=text,
                    image_path=sd_temp_img if sd_success else None,
                    output_video_path=raw_video_path,
                    status_dict=status_dict
                )
                safe_remove_file(sd_temp_img)

            if not os.path.exists(raw_video_path) or os.path.getsize(raw_video_path) < 1000:
                create_emergency_solid_clip(raw_video_path, dur, res_width, res_height)

            segment_mux_path = os.path.join(workspace_dir, f"temp_seg_mux_{idx}.mp4")
            safe_text = text.replace('\\', '').replace("'", "").replace('"', '').replace(':', ' ').strip()
            fontsize = int(res_width * 0.045)
            y_pos = int(res_height * 0.75)
            drawtext_filter = f"drawtext=text='{safe_text}':fontcolor=yellow:fontsize={fontsize}:box=1:boxcolor=black@0.6:boxborderw=10:x=(w-text_w)/2:y={y_pos}"
            fade_out_start = max(0.0, dur - 0.4)

            v_w, v_h = get_video_resolution(raw_video_path)
            if v_w == res_width and v_h == res_height:
                vf_filter_with_text = f"eq=saturation=1.15:contrast=1.05,{drawtext_filter},fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start:.2f}:d=0.4"
                vf_filter_no_text = f"eq=saturation=1.15:contrast=1.05,fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start:.2f}:d=0.4"
            else:
                vf_filter_with_text = f'scale={res_width}:{res_height}:force_original_aspect_ratio=increase,crop={res_width}:{res_height},setsar=1,eq=saturation=1.15:contrast=1.05,{drawtext_filter},fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start:.2f}:d=0.4'
                vf_filter_no_text = f'scale={res_width}:{res_height}:force_original_aspect_ratio=increase,crop={res_width}:{res_height},setsar=1,eq=saturation=1.15:contrast=1.05,fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start:.2f}:d=0.4'

            ff_cmd = [
                'ffmpeg', *get_hwaccel_args(), '-y', '-stream_loop', '-1',
                '-i', raw_video_path, '-i', audio_segment_path, '-t', f"{dur:.2f}",
                '-vf', vf_filter_with_text,
                '-af', f'afade=t=in:ss=0:d=0.4,afade=t=out:st={fade_out_start:.2f}:d=0.4,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo',
                '-r', '24', '-pix_fmt', 'yuv420p',
                '-c:v', 'libx264', '-crf', '18', '-preset', 'ultrafast',
                '-c:a', 'aac', '-ac', '2', '-ar', '44100',
                '-map', '0:v:0', '-map', '1:a:0', '-shortest',
                segment_mux_path,
            ]

            try:
                subprocess.run(ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                if os.path.exists(segment_mux_path) and os.path.getsize(segment_mux_path) > 0:
                    return segment_mux_path
            except Exception:
                fallback_cmd = [
                    'ffmpeg', *get_hwaccel_args(), '-y', '-stream_loop', '-1',
                    '-i', raw_video_path, '-i', audio_segment_path, '-t', f"{dur:.2f}",
                    '-vf', vf_filter_no_text,
                    '-af', 'aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo',
                    '-r', '24', '-pix_fmt', 'yuv420p',
                    '-c:v', 'libx264', '-preset', 'ultrafast',
                    '-c:a', 'aac', '-ac', '2', '-ar', '44100',
                    '-map', '0:v:0', '-map', '1:a:0', '-shortest',
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
            segment_results = {}
            
            # Thread worker wraps target process using script context variables
            def context_safe_worker(idx, scene):
                if ctx:
                    add_script_run_context(threading.current_thread(), ctx)
                return process_scene_segment(idx, scene)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_idx = {
                    executor.submit(context_safe_worker, idx, scene): idx
                    for idx, scene in enumerate(scenes_data)
                }
                for future in concurrent.futures.as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        scene_path = future.result()
                    except Exception:
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

            validated_scenes = []
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
                'ffmpeg', *get_hwaccel_args(), '-y', '-f', 'concat', '-safe', '0', '-i', manifest_file,
                '-c:v', 'copy', '-c:a', 'copy', temp_stitched_output
            ]
            subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            
            if bgm_path and os.path.exists(bgm_path):
                mix_cmd = [
                    'ffmpeg', *get_hwaccel_args(), '-y', '-i', temp_stitched_output, '-stream_loop', '-1', '-i', bgm_path,
                    '-filter_complex', f'[0:a]volume=1.0[a0];[1:a]volume={bgm_volume:.2f}[a1];[a0][a1]amix=inputs=2:duration=first[aout]',
                    '-map', '0:v:0', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', video_output
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
            shutil.rmtree(workspace_dir, ignore_errors=True)

# --- BACKEND WRAPPERS ---
def generate_script(prompt: str) -> List[Dict[str, Any]]:
    try:
        scenes_list, _ = generate_ai_script_and_scenes(
            topic=prompt, duration_choice="45 Seconds (3 Scenes)",
            selected_model="gemini-2.5-flash", language_choice="English"
        )
        return scenes_list
    except Exception:
        return [{"scene_text": "Fallback Scene Viewport", "search_keyword": "abstract", "duration": 5}]

def fetch_assets(keywords: List[str]) -> List[str]:
    try:
        os.makedirs("temp_scenes", exist_ok=True)
        downloaded = []
        for i, kw in enumerate(keywords):
            temp_path = os.path.join("temp_scenes", f"fetched_{i}_{uuid.uuid4().hex[:8]}.mp4")
            success = VisualEngine.fetch_pixabay_clip(kw, temp_path)
            if not success:
                success = get_premium_local_backup(temp_path)
            if not success:
                create_emergency_solid_clip(temp_path, 5.0, 720, 1280)
            downloaded.append(temp_path)
        return downloaded
    except Exception:
        return []

def compile_video(assets: List[str], output_path: str = "final_shorts.mp4") -> Optional[str]:
    try:
        if not assets:
            return None
        manifest_path = os.path.join("temp_scenes", f"manifest_{uuid.uuid4().hex[:8]}.txt")
        with open(manifest_path, "w") as f:
            for path in assets:
                f.write(f"file '{os.path.abspath(path).replace('\\', '/')}'\n")
        
        concat_cmd = [
            "ffmpeg", *get_hwaccel_args(), "-y", "-f", "concat", "-safe", "0", "-i", manifest_path,
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", output_path
        ]
        try:
            subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            safe_remove_file(manifest_path)
            return output_path
        except Exception:
            return None
    except Exception:
        return None

def convert_image_to_video_svd_robust(image_path: str, motion_bucket_id: int = 127) -> Optional[str]:
    video_path = None
    hf_key = os.getenv("HUGGINGFACE_API_KEY") or get_system_secret("HUGGINGFACE_API_KEY")
    
    if hf_key and InferenceClient is not None and image_path and os.path.exists(image_path):
        try:
            try:
                client_hf = InferenceClient(token=hf_key)
            except Exception:
                client_hf = InferenceClient(api_key=hf_key)
                
            with open(image_path, "rb") as img_file:
                img_data = img_file.read()
                
            response = client_hf.post(
                model="stabilityai/stable-video-diffusion-img2vid-xt",
                data=img_data,
                headers={"Accept": "video/mp4"},
                json={"parameters": {"motion_bucket_id": int(motion_bucket_id)}}
            )
            if response and len(response) > 5000:
                output_video_path = f"saved_renders/svd_output_{uuid.uuid4().hex[:6]}.mp4"
                with open(output_video_path, "wb") as out_f:
                    out_f.write(response)
                video_path = output_video_path
        except Exception:
            pass

    if not video_path:
        stability_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")
        if stability_key and stability_key != "mock":
            output_video_path = f"saved_renders/svd_output_{uuid.uuid4().hex[:6]}.mp4"
            success = StitcherEngine.generate_ai_video(image_path, output_video_path)
            if success and os.path.exists(output_video_path):
                video_path = output_video_path

    if not video_path:
        output_video_path = f"saved_renders/svd_output_{uuid.uuid4().hex[:6]}.mp4"
        try:
            cmd = [
                'ffmpeg', '-y', '-loop', '1', '-i', image_path, '-t', '4',
                '-vf', "zoompan=z='min(zoom+0.0015,1.5)':d=96:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720",
                '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-r', '24', output_video_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(output_video_path):
                video_path = output_video_path
        except Exception:
            pass

    return video_path

def generate_pro_image(prompt: str, aspect_ratio: str = "16:9", negative_prompt: str = "") -> Optional[str]:
    api_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")
    width, height = 1024, 1024
    if aspect_ratio == "16:9":
        width, height = 1344, 768
    elif aspect_ratio == "9:16":
        width, height = 768, 1344

    if api_key and api_key != "mock" and len(api_key.strip()) > 5:
        url = "https://api.stability.ai/v2beta/stable-image/generate/core"
        headers = {"authorization": f"Bearer {api_key}", "accept": "image/*"}
        files = {
            "prompt": (None, f"{prompt}, cinematic lighting, 8k, photorealistic"),
            "aspect_ratio": (None, aspect_ratio),
        }
        if negative_prompt.strip():
            files["negative_prompt"] = (None, negative_prompt.strip())
            
        try:
            response = requests.post(url, headers=headers, files=files, timeout=30)
            if response.status_code == 200 and len(response.content) > 10000:
                output_path = f"workshop_output_{uuid.uuid4().hex[:6]}.png"
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return output_path
        except Exception:
            pass

    try:
        clean_prompt = prompt.replace('"', '').replace("'", "").strip()
        encoded_prompt = urllib.parse.quote(f"{clean_prompt}, cinematic, 8k resolution, highly detailed")
        poll_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width={width}&height={height}&seed={random.randint(1, 999999)}&nologo=true"
        if negative_prompt.strip():
            poll_url += f"&negative={urllib.parse.quote(negative_prompt.strip())}"
            
        response = requests.get(poll_url, timeout=25)
        if response.status_code == 200 and len(response.content) > 10000:
            output_path = f"workshop_output_{uuid.uuid4().hex[:6]}.png"
            with open(output_path, "wb") as f:
                f.write(response.content)
            return output_path
    except Exception:
        pass

    return None

def get_premium_local_backup(output_filename: str) -> bool:
    local_dir = "local_assets"
    if os.path.exists(local_dir) and os.path.isdir(local_dir):
        files = [os.path.join(local_dir, f) for f in os.listdir(local_dir) if f.endswith(".mp4")]
        if files:
            try:
                shutil.copy(random.choice(files), output_filename)
                return True
            except Exception:
                pass
    return False

def create_emergency_solid_clip(output_filename: str, duration: float, res_width: int, res_height: int) -> bool:
    safe_remove_file(output_filename)
    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=#050508:s={res_width}x{res_height}:r=24',
        '-t', str(duration), '-pix_fmt', 'yuv420p', '-c:v', 'libx264', output_filename
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def create_emergency_silent_audio(output_filename: str, duration: float) -> bool:
    safe_remove_file(output_filename)
    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
        '-t', str(duration), '-c:a', 'libmp3lame', output_filename
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
        'ffmpeg', *get_hwaccel_args(), '-y', '-i', mp4_path,
        '-c:v', 'libvpx-vp9', '-crf', '32', '-b:v', '0', '-c:a', 'libopus', webm_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def find_valid_logo_path() -> Optional[str]:
    candidates = ["logo.png", "logo.jpeg", "watermarked_img_368871974808060610.png"]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None

def get_base64_img_raw(path: str) -> Optional[str]:
    import base64
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

def verify_system_folders() -> str:
    os.makedirs("saved_renders", exist_ok=True)
    os.makedirs("temp_scenes", exist_ok=True)
    os.makedirs("assets", exist_ok=True)
    os.makedirs(os.path.join("assets", "cache"), exist_ok=True)
    return "Ready"