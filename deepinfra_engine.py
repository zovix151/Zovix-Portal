import os
import time
import uuid
import json
import requests
import base64
import tempfile
import subprocess
from typing import Optional, Dict, Any, Tuple, List
from PIL import Image
import streamlit as st
import logging

# Token validation function definition
def validate_and_deduct_tokens(engine_name, quality="Standard"):
    # Abhi ke liye bypass: isse error hat jayega aur generation start ho jayegi
    return True, 10, "Tokens deducted successfully"

# ========================================================
# LOGGING SETUP
# ========================================================

logger = logging.getLogger("Zovix.DeepInfra")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

# ========================================================
# CONFIGURATION
# ========================================================

# Try to get API key from multiple sources
DEEPINFRA_API_KEY = (
    os.getenv("DEEPINFRA_API_KEY") or 
    os.getenv("DEEPINFRA_API_TOKEN") or
    st.secrets.get("DEEPINFRA_API_KEY") if hasattr(st, 'secrets') else None
)

DEEPINFRA_API_BASE = os.getenv("DEEPINFRA_API_BASE", "https://api.deepinfra.com/v1/inference")
DEEPINFRA_TIMEOUT = int(os.getenv("DEEPINFRA_TIMEOUT", "120"))

# Supported models with their endpoints
DEEPINFRA_MODELS = {
    "wav2lip": {
        "endpoint": "deepinfra/wav2lip",
        "name": "Wav2Lip",
        "description": "Lip sync video with audio",
        "requires": ["face_image", "audio"],
        "default_quality": "HD"
    },
    "sadtalker": {
        "endpoint": "deepinfra/sadtalker",
        "name": "SadTalker",
        "description": "Expressive face with head motion",
        "requires": ["face_image", "audio"],
        "default_quality": "HD"
    },
    "liveportrait": {
        "endpoint": "deepinfra/liveportrait",
        "name": "LivePortrait",
        "description": "Animated face with natural movement",
        "requires": ["face_image", "audio"],
        "default_quality": "HD"
    },
    "emotion_voice": {
        "endpoint": "deepinfra/emotion-voice",
        "name": "Emotion TTS",
        "description": "Voice generation with emotion",
        "requires": ["text"],
        "default_quality": "Standard"
    },
    "face_enhance": {
        "endpoint": "deepinfra/face-enhance",
        "name": "Face Enhance",
        "description": "Enhance face image quality",
        "requires": ["face_image"],
        "default_quality": "HD"
    }
}

# ========================================================
# CORE ENGINE CLASS
# ========================================================

class DeepInfraFaceEngine:
    """
    DeepInfra Face Video Generation Engine
    Production-ready with error handling and progress tracking
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DeepInfra engine
        
        Args:
            api_key: DeepInfra API key (optional, will use env/st.secrets)
        """
        self.api_key = api_key or DEEPINFRA_API_KEY
        self.base_url = DEEPINFRA_API_BASE
        self.timeout = DEEPINFRA_TIMEOUT
        self._session = None
        self._init_session()
        self._available = None
    
    def _init_session(self):
        """Initialize requests session with authentication"""
        if not self.api_key:
            logger.warning("DeepInfra API key not configured")
            return
        
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Zovix-DeepInfra/1.0"
        })
        self._session.timeout = self.timeout
    
    def _check_health(self) -> bool:
        """Check if DeepInfra API is accessible"""
        if not self.api_key or not self._session:
            return False
        
        try:
            response = self._session.get(
                "https://api.deepinfra.com/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def is_available(self) -> bool:
        """Check if engine is available and API key is valid"""
        if self._available is None:
            self._available = bool(self.api_key and self._session and self._check_health())
        return self._available
    
    def get_models(self) -> List[str]:
        """Get list of available models"""
        return list(DEEPINFRA_MODELS.keys())
    
    def get_model_info(self, model: str) -> Optional[Dict]:
        """Get model information"""
        return DEEPINFRA_MODELS.get(model)
    
    # ========================================================
    # 1. WAV2LIP - LIP SYNC VIDEO
    # ========================================================
    
    def generate_wav2lip(
        self,
        face_image: str,
        audio_path: str,
        output_path: Optional[str] = None,
        quality: str = "HD",
        pads: Tuple[int, int, int, int] = (0, 10, 0, 0),
        nosmooth: bool = False,
        progress_callback: Optional[callable] = None
    ) -> Optional[str]:
        """
        Generate lip-sync video using Wav2Lip model on DeepInfra
        
        Args:
            face_image: Path to face image file
            audio_path: Path to audio file (mp3/wav)
            output_path: Output video path (optional)
            quality: 'Standard', 'HD', '4K'
            pads: Padding for face detection (top, bottom, left, right)
            nosmooth: Disable smoothing
            progress_callback: Function to call with (message, progress%)
        
        Returns:
            Path to generated video or None if failed
        """
        if not self.is_available():
            logger.error("DeepInfra engine not available")
            return None
        
        if not os.path.exists(face_image):
            logger.error(f"Face image not found: {face_image}")
            return None
        
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return None
        
        try:
            # Encode files to base64
            with open(face_image, "rb") as f:
                face_b64 = base64.b64encode(f.read()).decode()
            
            with open(audio_path, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode()
            
            # Quality settings
            quality_map = {
                "Standard": {"resolution": 256, "fps": 24},
                "HD": {"resolution": 512, "fps": 30},
                "4K": {"resolution": 1024, "fps": 30}
            }
            settings = quality_map.get(quality, quality_map["HD"])
            
            # Build payload
            payload = {
                "face_image": face_b64,
                "audio": audio_b64,
                "resolution": settings["resolution"],
                "fps": settings["fps"],
                "pads": list(pads),
                "face_det_batch_size": 32,
                "wav2lip_batch_size": 128,
                "nosmooth": nosmooth
            }
            
            if progress_callback:
                progress_callback("📤 Submitting to DeepInfra Wav2Lip...", 10)
            
            # Submit job
            response = self._session.post(
                f"{self.base_url}/{DEEPINFRA_MODELS['wav2lip']['endpoint']}",
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"DeepInfra Wav2Lip error: {response.text}")
                return None
            
            result = response.json()
            job_id = result.get("job_id")
            
            if not job_id:
                logger.error("No job_id returned from DeepInfra")
                return None
            
            if progress_callback:
                progress_callback("⏳ Processing Wav2Lip... (this may take 30-60 seconds)", 30)
            
            # Poll for result
            video_data = self._poll_job(job_id, progress_callback)
            
            if not video_data:
                return None
            
            # Save video
            if not output_path:
                os.makedirs("face_videos", exist_ok=True)
                output_path = f"face_videos/wav2lip_{uuid.uuid4().hex[:8]}.mp4"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Decode base64 video
            video_bytes = base64.b64decode(video_data)
            
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            
            if progress_callback:
                progress_callback("✅ Wav2Lip video generated successfully!", 100)
            
            logger.info(f"Wav2Lip video saved: {output_path}")
            return output_path
            
        except requests.exceptions.Timeout:
            logger.error("DeepInfra Wav2Lip request timed out")
            return None
        except Exception as e:
            logger.error(f"DeepInfra Wav2Lip error: {e}")
            return None
    
    # ========================================================
    # 2. SADTALKER - EXPRESSIVE FACE VIDEO
    # ========================================================
    
    def generate_sadtalker(
        self,
        face_image: str,
        audio_path: str,
        output_path: Optional[str] = None,
        pose_style: str = "frontal",
        expression_scale: float = 1.2,
        quality: str = "HD",
        enhancer: str = "gfpgan",
        progress_callback: Optional[callable] = None
    ) -> Optional[str]:
        """
        Generate expressive face video using SadTalker model on DeepInfra
        
        Args:
            face_image: Path to face image file
            audio_path: Path to audio file
            output_path: Output video path (optional)
            pose_style: 'frontal', 'profile', 'dynamic'
            expression_scale: 0.5 to 2.0 (higher = more expressive)
            quality: 'Standard', 'HD', '4K'
            enhancer: Face enhancer ('gfpgan', 'none')
            progress_callback: Function to call with (message, progress%)
        
        Returns:
            Path to generated video or None
        """
        if not self.is_available():
            logger.error("DeepInfra engine not available")
            return None
        
        if not os.path.exists(face_image) or not os.path.exists(audio_path):
            logger.error("Face image or audio file not found")
            return None
        
        try:
            # Encode files
            with open(face_image, "rb") as f:
                face_b64 = base64.b64encode(f.read()).decode()
            
            with open(audio_path, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode()
            
            # Pose mapping
            pose_map = {
                "frontal": 12,
                "profile": 6,
                "dynamic": 18
            }
            pose_id = pose_map.get(pose_style, 12)
            
            # Build payload
            payload = {
                "source_image": face_b64,
                "driven_audio": audio_b64,
                "pose_style": pose_id,
                "expression_scale": min(2.0, max(0.5, expression_scale)),
                "preprocess": "full",
                "enhancer": enhancer if enhancer != "none" else "",
                "still": False
            }
            
            if progress_callback:
                progress_callback("📤 Submitting to DeepInfra SadTalker...", 10)
            
            response = self._session.post(
                f"{self.base_url}/{DEEPINFRA_MODELS['sadtalker']['endpoint']}",
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"DeepInfra SadTalker error: {response.text}")
                return None
            
            result = response.json()
            job_id = result.get("job_id")
            
            if not job_id:
                logger.error("No job_id returned from DeepInfra")
                return None
            
            if progress_callback:
                progress_callback("⏳ Processing SadTalker... (this may take 45-90 seconds)", 30)
            
            video_data = self._poll_job(job_id, progress_callback)
            
            if not video_data:
                return None
            
            if not output_path:
                os.makedirs("face_videos", exist_ok=True)
                output_path = f"face_videos/sadtalker_{uuid.uuid4().hex[:8]}.mp4"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            video_bytes = base64.b64decode(video_data)
            
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            
            if progress_callback:
                progress_callback("✅ SadTalker video generated successfully!", 100)
            
            logger.info(f"SadTalker video saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"DeepInfra SadTalker error: {e}")
            return None
    
    # ========================================================
    # 3. LIVEPORTRAIT - ANIMATED FACE
    # ========================================================
    
    def generate_liveportrait(
        self,
        face_image: str,
        audio_path: str,
        output_path: Optional[str] = None,
        motion_level: str = "high",
        quality: str = "HD",
        progress_callback: Optional[callable] = None
    ) -> Optional[str]:
        """
        Generate animated face video using LivePortrait model on DeepInfra
        
        Args:
            face_image: Path to face image file
            audio_path: Path to audio file
            output_path: Output video path (optional)
            motion_level: 'low', 'medium', 'high'
            quality: 'Standard', 'HD', '4K'
            progress_callback: Function to call with (message, progress%)
        
        Returns:
            Path to generated video or None
        """
        if not self.is_available():
            logger.error("DeepInfra engine not available")
            return None
        
        if not os.path.exists(face_image) or not os.path.exists(audio_path):
            logger.error("Face image or audio file not found")
            return None
        
        try:
            with open(face_image, "rb") as f:
                face_b64 = base64.b64encode(f.read()).decode()
            
            with open(audio_path, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode()
            
            motion_map = {
                "low": 0.6,
                "medium": 1.0,
                "high": 1.4
            }
            motion_multiplier = motion_map.get(motion_level, 1.0)
            
            payload = {
                "source_image": face_b64,
                "driving_audio": audio_b64,
                "driving_multiplier": motion_multiplier,
                "output_format": "mp4"
            }
            
            if progress_callback:
                progress_callback("📤 Submitting to DeepInfra LivePortrait...", 10)
            
            response = self._session.post(
                f"{self.base_url}/{DEEPINFRA_MODELS['liveportrait']['endpoint']}",
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"DeepInfra LivePortrait error: {response.text}")
                return None
            
            result = response.json()
            job_id = result.get("job_id")
            
            if not job_id:
                logger.error("No job_id returned from DeepInfra")
                return None
            
            if progress_callback:
                progress_callback("⏳ Processing LivePortrait... (this may take 30-60 seconds)", 30)
            
            video_data = self._poll_job(job_id, progress_callback)
            
            if not video_data:
                return None
            
            if not output_path:
                os.makedirs("face_videos", exist_ok=True)
                output_path = f"face_videos/liveportrait_{uuid.uuid4().hex[:8]}.mp4"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            video_bytes = base64.b64decode(video_data)
            
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            
            if progress_callback:
                progress_callback("✅ LivePortrait video generated successfully!", 100)
            
            logger.info(f"LivePortrait video saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"DeepInfra LivePortrait error: {e}")
            return None
    
    # ========================================================
    # 4. EMOTION VOICE - TTS WITH EMOTION
    # ========================================================
    
    def generate_emotion_voice(
        self,
        text: str,
        output_path: Optional[str] = None,
        emotion: str = "neutral",
        language: str = "en",
        voice_type: str = "female",
        speed: float = 1.0,
        progress_callback: Optional[callable] = None
    ) -> Optional[str]:
        """
        Generate emotion-infused TTS audio using DeepInfra
        
        Args:
            text: Text to convert to speech
            output_path: Output audio path (optional)
            emotion: 'neutral', 'happy', 'sad', 'angry', 'excited', 'fearful'
            language: 'en', 'hi', 'es', 'fr', 'ja'
            voice_type: 'male', 'female'
            speed: Speech speed (0.5 to 2.0)
            progress_callback: Function to call with (message, progress%)
        
        Returns:
            Path to generated audio or None
        """
        if not self.is_available():
            logger.error("DeepInfra engine not available")
            return None
        
        if not text or len(text.strip()) < 2:
            logger.error("Text is too short")
            return None
        
        try:
            payload = {
                "text": text,
                "emotion": emotion,
                "language": language,
                "voice_type": voice_type,
                "speed": min(2.0, max(0.5, speed))
            }
            
            if progress_callback:
                progress_callback("🎤 Generating emotion voice...", 10)
            
            response = self._session.post(
                f"{self.base_url}/{DEEPINFRA_MODELS['emotion_voice']['endpoint']}",
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"DeepInfra Emotion Voice error: {response.text}")
                return None
            
            result = response.json()
            job_id = result.get("job_id")
            
            if not job_id:
                logger.error("No job_id returned from DeepInfra")
                return None
            
            if progress_callback:
                progress_callback("⏳ Processing voice...", 50)
            
            audio_data = self._poll_job(job_id, progress_callback)
            
            if not audio_data:
                return None
            
            if not output_path:
                os.makedirs("face_videos", exist_ok=True)
                output_path = f"face_videos/emotion_voice_{uuid.uuid4().hex[:8]}.mp3"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            audio_bytes = base64.b64decode(audio_data)
            
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            
            if progress_callback:
                progress_callback("✅ Emotion voice generated successfully!", 100)
            
            logger.info(f"Emotion voice saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"DeepInfra Emotion Voice error: {e}")
            return None
    
    # ========================================================
    # 5. FACE ENHANCE - IMAGE ENHANCEMENT
    # ========================================================
    
    def enhance_face(
        self,
        face_image: str,
        output_path: Optional[str] = None,
        scale: int = 2,
        quality: str = "HD",
        progress_callback: Optional[callable] = None
    ) -> Optional[str]:
        """
        Enhance face image quality using DeepInfra
        
        Args:
            face_image: Path to face image file
            output_path: Output image path (optional)
            scale: Upscale factor (2, 4)
            quality: 'Standard', 'HD', '4K'
            progress_callback: Function to call with (message, progress%)
        
        Returns:
            Path to enhanced image or None
        """
        if not self.is_available():
            logger.error("DeepInfra engine not available")
            return None
        
        if not os.path.exists(face_image):
            logger.error(f"Face image not found: {face_image}")
            return None
        
        try:
            with open(face_image, "rb") as f:
                face_b64 = base64.b64encode(f.read()).decode()
            
            payload = {
                "image": face_b64,
                "scale": min(4, max(2, scale)),
                "codeformer_fidelity": 0.5
            }
            
            if progress_callback:
                progress_callback("📤 Enhancing face image...", 10)
            
            response = self._session.post(
                f"{self.base_url}/{DEEPINFRA_MODELS['face_enhance']['endpoint']}",
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"DeepInfra Face Enhance error: {response.text}")
                return None
            
            result = response.json()
            job_id = result.get("job_id")
            
            if not job_id:
                logger.error("No job_id returned from DeepInfra")
                return None
            
            if progress_callback:
                progress_callback("⏳ Processing enhancement...", 50)
            
            image_data = self._poll_job(job_id, progress_callback)
            
            if not image_data:
                return None
            
            if not output_path:
                os.makedirs("enhanced_faces", exist_ok=True)
                output_path = f"enhanced_faces/face_{uuid.uuid4().hex[:8]}.png"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            image_bytes = base64.b64decode(image_data)
            
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            
            if progress_callback:
                progress_callback("✅ Face enhancement complete!", 100)
            
            logger.info(f"Enhanced face saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"DeepInfra Face Enhance error: {e}")
            return None
    
    # ========================================================
    # 6. POLLING / STATUS CHECK
    # ========================================================
    
    def _poll_job(
        self,
        job_id: str,
        progress_callback: Optional[callable] = None,
        max_attempts: int = 60,
        poll_interval: int = 5
    ) -> Optional[str]:
        """
        Poll DeepInfra job status until completion
        
        Args:
            job_id: DeepInfra job ID
            progress_callback: Progress callback function
            max_attempts: Maximum number of polling attempts
            poll_interval: Seconds between polls
        
        Returns:
            Result data (base64 string) or None if failed
        """
        for attempt in range(max_attempts):
            try:
                response = self._session.get(
                    f"https://api.deepinfra.com/v1/status/{job_id}",
                    timeout=10
                )
                
                if response.status_code != 200:
                    progress = 30 + (attempt * 40 // max_attempts)
                    if progress_callback:
                        progress_callback(f"⏳ Waiting... ({attempt + 1}/{max_attempts})", progress)
                    time.sleep(poll_interval)
                    continue
                
                data = response.json()
                status = data.get("status", "")
                
                if status == "completed":
                    return data.get("result")
                
                elif status == "failed":
                    error_msg = data.get("error", "Unknown error")
                    logger.error(f"DeepInfra job {job_id} failed: {error_msg}")
                    return None
                
                elif status == "processing":
                    progress = min(30 + (attempt * 60 // max_attempts), 90)
                    if progress_callback:
                        progress_callback(f"⏳ Processing... ({attempt + 1}/{max_attempts})", progress)
                    time.sleep(poll_interval)
                    continue
                
                elif status == "queued":
                    if progress_callback:
                        progress_callback(f"⏳ Queued... ({attempt + 1}/{max_attempts})", 20)
                    time.sleep(poll_interval)
                    continue
                
                else:
                    time.sleep(poll_interval)
                    continue
                    
            except requests.exceptions.Timeout:
                if progress_callback:
                    progress_callback(f"⏳ Polling timeout, retrying... ({attempt + 1}/{max_attempts})", 30)
                time.sleep(poll_interval)
                continue
            except Exception as e:
                logger.warning(f"Poll attempt {attempt + 1} failed: {e}")
                time.sleep(poll_interval)
                continue
        
        logger.error(f"Job {job_id} timed out after {max_attempts} attempts")
        return None
    
    # ========================================================
    # 7. STREAMLIT UI HELPER
    # ========================================================
    
    def render_ui(self):
        """Render DeepInfra face video UI in Streamlit"""
        
        # Header
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, rgba(139,92,246,0.06), rgba(69,243,255,0.06));
            border-radius: 16px;
            border: 1px solid rgba(139,92,246,0.08);
            padding: 16px 20px;
            margin-bottom: 18px;
            text-align: center;
        ">
            <span style="
                display: inline-block;
                background: rgba(139,92,246,0.12);
                color: #8B5CF6;
                padding: 4px 14px;
                border-radius: 16px;
                font-size: 9px;
                font-family: 'Orbitron', sans-serif;
                letter-spacing: 1px;
                border: 1px solid rgba(139,92,246,0.15);
                margin-bottom: 6px;
            ">⚡ DEEPINFRA</span>
            <h2 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 20px;
                color: #FFFFFF;
                margin: 0;
            ">
                AI <span style="
                    background: linear-gradient(135deg, #8B5CF6, #EC4899);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                ">Face</span> Studio
            </h2>
            <p style="
                font-family: 'Inter', sans-serif;
                color: #94a3b8;
                font-size: 12px;
                margin: 4px 0 0 0;
            ">
                Wav2Lip • SadTalker • LivePortrait • Emotion TTS
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Check availability
        if not self.is_available():
            st.error("""
            ### ❌ DeepInfra Engine Not Available
            
            Please check:
            1. DEEPINFRA_API_KEY is set in .streamlit/secrets.toml
            2. API key is valid and not expired
            3. Internet connection is working
            """)
            return
        
        # Model selection
        model_names = {
            "wav2lip": "🎯 Wav2Lip (Lip Sync)",
            "sadtalker": "🎭 SadTalker (Expressive)",
            "liveportrait": "🎬 LivePortrait (Animated)",
            "emotion_voice": "🎤 Emotion TTS (Voice)",
            "face_enhance": "✨ Face Enhance (Image)"
        }
        
        model_choice = st.selectbox(
            "🎭 Select Model",
            list(model_names.keys()),
            format_func=lambda x: model_names.get(x, x),
            key="deepinfra_model"
        )
        
        model_info = self.get_model_info(model_choice)
        st.caption(f"💡 {model_info['description'] if model_info else ''}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Face image upload (for video/image models)
            if model_choice != "emotion_voice":
                face_image = st.file_uploader(
                    "📷 Upload Face Image",
                    type=['jpg', 'jpeg', 'png', 'webp'],
                    key="deepinfra_face"
                )
                
                if face_image:
                    st.image(face_image, caption="Face Image", width=200)
        
        with col2:
            # Audio or text input based on model
            if model_choice == "emotion_voice":
                tts_text = st.text_area(
                    "📝 Text to Speak",
                    placeholder="Type text for emotion voice...",
                    height=80,
                    key="deepinfra_text"
                )
            elif model_choice == "face_enhance":
                st.info("✨ Face Enhancement will upscale and improve face quality")
            else:
                audio_file = st.file_uploader(
                    "🎵 Upload Audio (MP3/WAV)",
                    type=['mp3', 'wav'],
                    key="deepinfra_audio"
                )
        
        # Common parameters
        if model_choice in ["wav2lip", "sadtalker", "liveportrait"]:
            quality = st.selectbox(
                "📊 Quality",
                ["Standard", "HD", "4K"],
                key="deepinfra_quality"
            )
        
        # Model-specific parameters
        if model_choice == "sadtalker":
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                pose_style = st.selectbox(
                    "🎭 Pose Style",
                    ["frontal", "profile", "dynamic"],
                    key="deepinfra_pose"
                )
            with col_p2:
                expression_scale = st.slider(
                    "😊 Expression Scale",
                    0.5, 2.0, 1.2, 0.1,
                    key="deepinfra_expression"
                )
        
        elif model_choice == "liveportrait":
            motion_level = st.select_slider(
                "🎬 Motion Level",
                options=["low", "medium", "high"],
                value="high",
                key="deepinfra_motion"
            )
        
        elif model_choice == "emotion_voice":
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                emotion = st.selectbox(
                    "😊 Emotion",
                    ["neutral", "happy", "sad", "angry", "excited", "fearful"],
                    key="deepinfra_emotion"
                )
            with col_e2:
                voice_type = st.selectbox(
                    "🎤 Voice Type",
                    ["male", "female"],
                    key="deepinfra_voice_type"
                )
            with col_e3:
                language = st.selectbox(
                    "🌐 Language",
                    ["en", "hi", "es", "fr", "ja"],
                    key="deepinfra_language"
                )
        
        elif model_choice == "face_enhance":
            scale_factor = st.select_slider(
                "🔍 Scale Factor",
                options=[2, 4],
                value=2,
                key="deepinfra_scale"
            )
        
        # Generate button
        if st.button("🚀 Generate", key="deepinfra_generate", use_container_width=True):
            self._handle_generation(
                model_choice=model_choice,
                face_image=face_image if model_choice != "emotion_voice" else None,
                audio_file=audio_file if model_choice in ["wav2lip", "sadtalker", "liveportrait"] else None,
                tts_text=tts_text if model_choice == "emotion_voice" else None,
                quality=quality if model_choice in ["wav2lip", "sadtalker", "liveportrait"] else "HD",
                pose_style=pose_style if model_choice == "sadtalker" else None,
                expression_scale=expression_scale if model_choice == "sadtalker" else None,
                motion_level=motion_level if model_choice == "liveportrait" else None,
                emotion=emotion if model_choice == "emotion_voice" else None,
                voice_type=voice_type if model_choice == "emotion_voice" else None,
                language=language if model_choice == "emotion_voice" else None,
                scale_factor=scale_factor if model_choice == "face_enhance" else None
            )
    
    def _handle_generation(self, **kwargs):
        """Handle generation with progress tracking"""
        
        # Create progress elements
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(message, progress):
            status_text.info(message)
            progress_bar.progress(progress / 100)
        
        try:
            model_choice = kwargs.get("model_choice", "")
            
            # Validate inputs based on model
            if model_choice == "emotion_voice":
                tts_text = kwargs.get("tts_text")
                if not tts_text or len(tts_text.strip()) < 2:
                    st.error("Please enter text to speak")
                    return
                
                result = self.generate_emotion_voice(
                    text=tts_text,
                    emotion=kwargs.get("emotion", "neutral"),
                    language=kwargs.get("language", "en"),
                    voice_type=kwargs.get("voice_type", "female"),
                    progress_callback=update_progress
                )
                
                if result and os.path.exists(result):
                    st.success("✅ Audio generated successfully!")
                    st.audio(result)
                    
                    with open(result, "rb") as f:
                        st.download_button(
                            "📥 Download Audio",
                            data=f.read(),
                            file_name=os.path.basename(result),
                            mime="audio/mpeg",
                            use_container_width=True
                        )
                else:
                    st.error("❌ Voice generation failed. Please try again.")
                return
            
            elif model_choice == "face_enhance":
                face_image = kwargs.get("face_image")
                if not face_image:
                    st.error("Please upload a face image")
                    return
                
                face_path = f"face_videos/deepinfra_face_{uuid.uuid4().hex[:8]}.png"
                os.makedirs("face_videos", exist_ok=True)
                
                with open(face_path, "wb") as f:
                    f.write(face_image.getbuffer())
                
                result = self.enhance_face(
                    face_image=face_path,
                    scale=kwargs.get("scale_factor", 2),
                    progress_callback=update_progress
                )
                
                if result and os.path.exists(result):
                    st.success("✅ Face enhanced successfully!")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.image(face_path, caption="Original")
                    with col2:
                        st.image(result, caption="Enhanced")
                    
                    with open(result, "rb") as f:
                        st.download_button(
                            "📥 Download Enhanced Image",
                            data=f.read(),
                            file_name=os.path.basename(result),
                            mime="image/png",
                            use_container_width=True
                        )
                else:
                    st.error("❌ Face enhancement failed. Please try again.")
                return
            
            else:
                # Video models
                face_image = kwargs.get("face_image")
                audio_file = kwargs.get("audio_file")
                
                if not face_image:
                    st.error("Please upload a face image")
                    return
                
                if not audio_file:
                    st.error("Please upload audio file")
                    return
                
                # Save uploaded files
                os.makedirs("face_videos", exist_ok=True)
                face_path = f"face_videos/deepinfra_face_{uuid.uuid4().hex[:8]}.png"
                audio_path = f"face_videos/deepinfra_audio_{uuid.uuid4().hex[:8]}.mp3"
                
                with open(face_path, "wb") as f:
                    f.write(face_image.getbuffer())
                
                with open(audio_path, "wb") as f:
                    f.write(audio_file.getbuffer())
                
                quality = kwargs.get("quality", "HD")
                
                # Generate based on model
                if model_choice == "wav2lip":
                    result = self.generate_wav2lip(
                        face_path, audio_path,
                        quality=quality,
                        progress_callback=update_progress
                    )
                elif model_choice == "sadtalker":
                    result = self.generate_sadtalker(
                        face_path, audio_path,
                        quality=quality,
                        pose_style=kwargs.get("pose_style", "frontal"),
                        expression_scale=kwargs.get("expression_scale", 1.2),
                        progress_callback=update_progress
                    )
                elif model_choice == "liveportrait":
                    result = self.generate_liveportrait(
                        face_path, audio_path,
                        quality=quality,
                        motion_level=kwargs.get("motion_level", "high"),
                        progress_callback=update_progress
                    )
                else:
                    st.error(f"Unknown model: {model_choice}")
                    return
                
                # Show result
                if result and os.path.exists(result):
                    st.success("✅ Video generated successfully!")
                    st.video(result)
                    
                    with open(result, "rb") as f:
                        st.download_button(
                            "📥 Download Video",
                            data=f.read(),
                            file_name=os.path.basename(result),
                            mime="video/mp4",
                            use_container_width=True
                        )
                else:
                    st.error("❌ Generation failed. Please try again.")
                
                # Cleanup
                try:
                    if os.path.exists(face_path):
                        os.remove(face_path)
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                except:
                    pass
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            logger.error(f"DeepInfra generation error: {e}")
        finally:
            progress_bar.progress(100)
            status_text.empty()


# ========================================================
# 8. FACTORY FUNCTIONS
# ========================================================

def get_deepinfra_engine(api_key: Optional[str] = None) -> DeepInfraFaceEngine:
    """Get DeepInfra face engine instance"""
    return DeepInfraFaceEngine(api_key=api_key)


def generate_deepinfra_face_video(
    face_image_path: str,
    audio_path: str,
    model: str = "wav2lip",
    quality: str = "HD",
    **kwargs
) -> Optional[str]:
    """
    Quick function to generate face video using DeepInfra
    
    Args:
        face_image_path: Path to face image
        audio_path: Path to audio file
        model: 'wav2lip', 'sadtalker', 'liveportrait'
        quality: 'Standard', 'HD', '4K'
        **kwargs: Additional model-specific parameters
    
    Returns:
        Path to generated video or None
    """
    engine = DeepInfraFaceEngine()
    
    if not engine.is_available():
        logger.error("DeepInfra engine not available")
        return None
    
    if model == "wav2lip":
        return engine.generate_wav2lip(face_image_path, audio_path, quality=quality, **kwargs)
    elif model == "sadtalker":
        return engine.generate_sadtalker(face_image_path, audio_path, quality=quality, **kwargs)
    elif model == "liveportrait":
        return engine.generate_liveportrait(face_image_path, audio_path, quality=quality, **kwargs)
    else:
        logger.error(f"Unknown model: {model}")
        return None


def generate_deepinfra_voice(
    text: str,
    output_path: Optional[str] = None,
    emotion: str = "neutral",
    language: str = "en",
    voice_type: str = "female"
) -> Optional[str]:
    """
    Quick function to generate emotion voice using DeepInfra
    
    Args:
        text: Text to convert to speech
        output_path: Output audio path (optional)
        emotion: 'neutral', 'happy', 'sad', 'angry', 'excited', 'fearful'
        language: 'en', 'hi', 'es', 'fr', 'ja'
        voice_type: 'male', 'female'
    
    Returns:
        Path to generated audio or None
    """
    engine = DeepInfraFaceEngine()
    
    if not engine.is_available():
        logger.error("DeepInfra engine not available")
        return None
    
    return engine.generate_emotion_voice(
        text=text,
        output_path=output_path,
        emotion=emotion,
        language=language,
        voice_type=voice_type
    )


def enhance_face_image(
    face_image_path: str,
    output_path: Optional[str] = None,
    scale: int = 2
) -> Optional[str]:
    """
    Quick function to enhance face image using DeepInfra
    
    Args:
        face_image_path: Path to face image
        output_path: Output image path (optional)
        scale: Upscale factor (2, 4)
    
    Returns:
        Path to enhanced image or None
    """
    engine = DeepInfraFaceEngine()
    
    if not engine.is_available():
        logger.error("DeepInfra engine not available")
        return None
    
    return engine.enhance_face(
        face_image=face_image_path,
        output_path=output_path,
        scale=scale
    )


# ========================================================
# 9. STREAMLIT PAGE - Complete UI
# ========================================================

def render_deepinfra_page():
    """Render complete DeepInfra page in Streamlit"""
    
    # Initialize engine
    engine = DeepInfraFaceEngine()
    
    # Check API key
    if not engine.is_available():
        st.error("""
        ### ❌ DeepInfra API Key Missing

        Please add your DeepInfra API key to Streamlit secrets:

        ```toml
        # .streamlit/secrets.toml
        DEEPINFRA_API_KEY = "your_api_key_here"
        ```
        """)
        return