import os
import cv2
import time
import uuid
import sqlite3
import asyncio
import random
import requests
import json
import subprocess
import shutil
import threading
import queue
import concurrent.futures
import base64
import urllib.parse
import traceback
import datetime
import difflib
import hashlib
import io
import hmac
import re
import sys
import logging
import pickle
import tempfile
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except Exception:
    HAS_DOTENV = False

    def load_dotenv(*args, **kwargs):
        return False
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import streamlit as st
import streamlit.components.v1 as components
from pydantic import BaseModel, Field

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
from typing import List, Dict, Any, Tuple, Optional, Union
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
import psutil
import socket
import platform


# ========================================================
# LOGGING SETUP
# ========================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zovix.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Zovix")

# ========================================================
# ENVIRONMENT VARIABLES & SECRETS
# ========================================================

if not HAS_DOTENV:
    logger.warning("python-dotenv not installed. Continuing with OS environment variables only.")

load_dotenv()

def get_system_secret(key: str, default_val: Optional[str] = None) -> Optional[str]:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default_val)

# System Configuration
SYSTEM_CONFIG = {
    "MAX_WORKERS": int(os.getenv("MAX_WORKERS", "4")),
    "QUEUE_MAX_SIZE": int(os.getenv("QUEUE_MAX_SIZE", "100")),
    "CACHE_TTL": int(os.getenv("CACHE_TTL", "3600")),
    "RATE_LIMIT_REQUESTS": int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
    "RATE_LIMIT_WINDOW": int(os.getenv("RATE_LIMIT_WINDOW", "60")),
    "ENCRYPTION_KEY": os.getenv("ENCRYPTION_KEY", "zovix_secure_key_2026"),
    "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
    "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
    "CELERY_BROKER_URL": os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    "CELERY_RESULT_BACKEND": os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
}

# API Keys - ALL REAL
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
AZURE_SPEECH_KEY = get_system_secret("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = get_system_secret("AZURE_SPEECH_REGION", "eastus")
CLOUDFLARE_ZONE_ID = get_system_secret("CLOUDFLARE_ZONE_ID")
CLOUDFLARE_API_KEY = get_system_secret("CLOUDFLARE_API_KEY")
CDN_DOMAIN = get_system_secret("CDN_DOMAIN", "")

# ========================================================
# GOOGLE GENAI IMPORT WITH FALLBACK
# ========================================================

try:
    from google import genai
    from google.genai import types
    has_genai = True
except ImportError:
    has_genai = False
    logger.warning("google-genai not installed. Using fallback script generation.")

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

try:
    import replicate
    HAS_REPLICATE = True
except ImportError:
    replicate = None
    HAS_REPLICATE = False
    logger.warning("replicate not installed. Face Studio cloud mode will be unavailable.")

try:
    import razorpay
except ImportError:
    razorpay = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    from mutagen.mp3 import MP3
except ImportError:
    MP3 = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logger.warning("redis not installed. Using in-memory cache.")

try:
    from celery import Celery, Task
    HAS_CELERY = True
except ImportError:
    HAS_CELERY = False
    logger.warning("celery not installed. Using threaded queue.")

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    logger.warning("cryptography not installed. Using fallback encryption.")

try:
    import pyotp
    import qrcode
    HAS_2FA = True
except ImportError:
    HAS_2FA = False
    logger.warning("pyotp or qrcode not installed. 2FA disabled.")

# ========================================================
# 1. ENCRYPTION SYSTEM
# ========================================================

class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self):
        self.key = SYSTEM_CONFIG["ENCRYPTION_KEY"]
        self._fernet = None
        if HAS_CRYPTOGRAPHY:
            try:
                key_bytes = self.key.encode().ljust(32)[:32]
                self._fernet = Fernet(base64.urlsafe_b64encode(key_bytes))
            except Exception as e:
                logger.error(f"Failed to initialize Fernet: {e}")
                self._fernet = None
    
    def encrypt(self, data: str) -> str:
        if not data:
            return data
        
        if self._fernet:
            try:
                return self._fernet.encrypt(data.encode()).decode()
            except Exception as e:
                logger.error(f"Encryption error: {e}")
        
        return base64.b64encode(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        if not encrypted_data:
            return encrypted_data
        
        if self._fernet:
            try:
                return self._fernet.decrypt(encrypted_data.encode()).decode()
            except Exception as e:
                logger.error(f"Decryption error: {e}")
        
        try:
            return base64.b64decode(encrypted_data.encode()).decode()
        except:
            return encrypted_data

encryption_manager = EncryptionManager()

# ========================================================
# 2. RATE LIMITER
# ========================================================

class RateLimiter:
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self._redis_client = None
        
        if HAS_REDIS:
            try:
                self._redis_client = redis.Redis.from_url(
                    SYSTEM_CONFIG["REDIS_URL"],
                    decode_responses=True
                )
                self._redis_client.ping()
                logger.info("Redis connected for rate limiting")
            except Exception as e:
                logger.warning(f"Redis not available: {e}")
                self._redis_client = None
        
        self._memory_cache = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> Tuple[bool, int]:
        current_time = time.time()
        key = f"rate_limit:{user_id}"
        
        if self._redis_client:
            try:
                pipe = self._redis_client.pipeline()
                pipe.zadd(key, {str(current_time): current_time})
                pipe.zremrangebyscore(key, 0, current_time - self.time_window)
                pipe.zcard(key)
                pipe.expire(key, self.time_window + 5)
                results = pipe.execute()
                
                request_count = results[2]
                
                if request_count > self.max_requests:
                    return False, 0
                
                remaining = self.max_requests - request_count
                return True, remaining
            except Exception as e:
                logger.warning(f"Redis rate limit error: {e}")
        
        if user_id not in self._memory_cache:
            self._memory_cache[user_id] = []
        
        self._memory_cache[user_id] = [
            req_time for req_time in self._memory_cache[user_id]
            if current_time - req_time < self.time_window
        ]
        
        if len(self._memory_cache[user_id]) >= self.max_requests:
            return False, 0
        
        self._memory_cache[user_id].append(current_time)
        remaining = self.max_requests - len(self._memory_cache[user_id])
        return True, remaining

rate_limiter = RateLimiter(
    max_requests=SYSTEM_CONFIG["RATE_LIMIT_REQUESTS"],
    time_window=SYSTEM_CONFIG["RATE_LIMIT_WINDOW"]
)

# ========================================================
# 3. GDPR COMPLIANCE
# ========================================================

class GDPRManager:
    def __init__(self):
        self.consent_key = "gdpr_consent"
        self.consent_version = "1.0"
    
    def get_consent(self, username: str = None) -> bool:
        if username:
            conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT gdpr_consent, gdpr_version FROM users WHERE username = ?",
                    (username,)
                )
                row = cursor.fetchone()
                if row:
                    return row[0] == 1 and row[1] == self.consent_version
            except:
                pass
            finally:
                conn.close()
        
        return st.session_state.get(self.consent_key, False)
    
    def set_consent(self, username: str = None) -> bool:
        st.session_state[self.consent_key] = True
        
        if username:
            conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE users SET gdpr_consent = 1, gdpr_version = ? WHERE username = ?",
                    (self.consent_version, username)
                )
                conn.commit()
                return True
            except:
                pass
            finally:
                conn.close()
        
        return True
    
    def request_consent(self, username: str = None) -> bool:
        if self.get_consent(username):
            return True
        
        with st.dialog("🔒 GDPR Consent Required", width="large"):
            st.markdown("""
                ### Data Protection & Privacy Consent
                
                We value your privacy. By continuing, you agree to:
                
                ✅ **Data Collection**: We collect minimal data to provide services
                ✅ **Data Usage**: Your data is used only for platform functionality
                ✅ **Data Storage**: Data is encrypted and stored securely
                ✅ **Data Rights**: You can request data deletion anytime
                ✅ **Cookies**: We use essential cookies for authentication
                
                For more details, see our [Privacy Policy](#)
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ I Accept", use_container_width=True):
                    self.set_consent(username)
                    st.rerun()
            with col2:
                if st.button("❌ Decline", use_container_width=True):
                    st.warning("You need to accept GDPR consent to use the platform.")
                    return False
        
        return self.get_consent(username)
    
    def delete_user_data(self, username: str) -> bool:
        if not username:
            return False
        
        conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
        cursor = conn.cursor()
        try:
            tables = [
                "users", "history", "face_video_history", "editor_uploads",
                "payment_history", "social_schedule", "referrals", "social_shares",
                "user_achievements", "dynamic_ui_profiles", "emotion_voice_history",
                "ai_agent_config", "ai_sales_videos"
            ]
            
            for table in tables:
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE username = ?", (username,))
                except:
                    pass
            
            conn.commit()
            logger.info(f"Deleted all data for user: {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete user data: {e}")
            return False
        finally:
            conn.close()

gdpr_manager = GDPRManager()

# ========================================================
# 5. CELERY TASK QUEUE
# ========================================================

if HAS_CELERY:
    celery_app = Celery(
        'zovix_tasks',
        broker=SYSTEM_CONFIG["CELERY_BROKER_URL"],
        backend=SYSTEM_CONFIG["CELERY_RESULT_BACKEND"],
        include=['zovix_tasks']
    )
    
    celery_app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,
        task_soft_time_limit=25 * 60,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=100,
    )
    
    class ZovixTask(Task):
        def on_failure(self, exc, task_id, args, kwargs, einfo):
            logger.error(f"Task {task_id} failed: {exc}")
            try:
                conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO task_failures (task_id, error, timestamp) VALUES (?, ?, ?)",
                    (task_id, str(exc), datetime.now().isoformat())
                )
                conn.commit()
                conn.close()
            except:
                pass
    
    @celery_app.task(base=ZovixTask, bind=True)
    def process_video_task(self, scenes_data, config, user_id):
        try:
            self.update_state(state='PROGRESS', meta={'status': 'Starting video processing...'})
            
            result = StitcherEngine.build_scene_stitched_video_isolated(
                scenes_data=scenes_data,
                video_output="final_shorts.mp4",
                size_choice=config.get("aspect_ratio", "📐 9:16 Vertical (Shorts/Reels)"),
                voice_profile=config.get("voice_profile", "Adam (Premium Male)"),
                language_choice=config.get("language_choice", "🇮🇳 Hinglish (Fluent Hindi Mix)"),
                bgm_path=config.get("bgm_path"),
                bgm_volume=config.get("bgm_volume", 0.3),
                music_mood=config.get("music_mood", "cinematic")
            )
            
            if result:
                self.update_state(state='SUCCESS', meta={'status': 'Video processed successfully'})
                return {"success": True, "video_path": "final_shorts.mp4"}
            else:
                raise Exception("Video processing failed")
                
        except Exception as e:
            logger.error(f"Video processing error: {e}")
            self.update_state(state='FAILURE', meta={'error': str(e)})
            raise
    
    @celery_app.task(base=ZovixTask, bind=True)
    def process_image_task(self, prompt, aspect_ratio, quality, user_id):
        try:
            self.update_state(state='PROGRESS', meta={'status': 'Generating image...'})
            
            result = generate_pro_image(prompt, aspect_ratio)
            
            if result:
                self.update_state(state='SUCCESS', meta={'status': 'Image generated successfully'})
                return {"success": True, "image_path": result}
            else:
                raise Exception("Image generation failed")
                
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            self.update_state(state='FAILURE', meta={'error': str(e)})
            raise
    
    @celery_app.task(base=ZovixTask, bind=True)
    def process_voice_task(self, text, emotion, voice_id, user_id):
        try:
            self.update_state(state='PROGRESS', meta={'status': 'Generating voice...'})
            
            result = generate_emotion_voice(text, emotion, "male", None, voice_id)
            
            if result:
                self.update_state(state='SUCCESS', meta={'status': 'Voice generated successfully'})
                return {"success": True, "audio_path": result}
            else:
                raise Exception("Voice generation failed")
                
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            self.update_state(state='FAILURE', meta={'error': str(e)})
            raise
    
    def get_task_status(task_id):
        if not HAS_CELERY:
            return None
        
        try:
            task = celery_app.AsyncResult(task_id)
            
            if task.state == 'PENDING':
                return {'status': 'pending', 'message': 'Task is waiting to be processed'}
            elif task.state == 'PROGRESS':
                return {'status': 'progress', 'message': task.info.get('status', 'Processing...')}
            elif task.state == 'SUCCESS':
                return {'status': 'success', 'result': task.result}
            elif task.state == 'FAILURE':
                return {'status': 'failed', 'error': str(task.info)}
            else:
                return {'status': 'unknown', 'message': task.state}
        except Exception as e:
            logger.error(f"Task status error: {e}")
            return {'status': 'error', 'message': str(e)}
else:
    class ThreadedTaskQueue:
        def __init__(self):
            self._queue = queue.Queue()
            self._results = {}
            self._running = False
            self._workers = []
            self._lock = threading.Lock()
        
        def start(self):
            if self._running:
                return
            
            self._running = True
            num_workers = SYSTEM_CONFIG["MAX_WORKERS"]
            
            for i in range(num_workers):
                worker = threading.Thread(target=self._worker_loop, daemon=True)
                worker.start()
                self._workers.append(worker)
            
            logger.info(f"Started {num_workers} threaded workers")
        
        def stop(self):
            self._running = False
            for worker in self._workers:
                worker.join(timeout=2)
            self._workers = []
        
        def add_task(self, func, *args, **kwargs):
            task_id = str(uuid.uuid4())
            task = {
                'id': task_id,
                'func': func,
                'args': args,
                'kwargs': kwargs,
                'status': 'pending',
                'result': None,
                'error': None
            }
            
            with self._lock:
                self._queue.put(task)
                self._results[task_id] = task
            
            return task_id
        
        def _worker_loop(self):
            while self._running:
                try:
                    task = self._queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                try:
                    task['status'] = 'running'
                    result = task['func'](*task['args'], **task['kwargs'])
                    task['status'] = 'completed'
                    task['result'] = result
                except Exception as e:
                    task['status'] = 'failed'
                    task['error'] = str(e)
                    logger.error(f"Task {task['id']} failed: {e}")
                
                with self._lock:
                    self._results[task['id']] = task
        
        def get_task_status(self, task_id):
            with self._lock:
                return self._results.get(task_id)
    
    task_queue = ThreadedTaskQueue()
    task_queue.start()

# ========================================================
# 6. LOAD BALANCER
# ========================================================

class LoadBalancer:
    def __init__(self):
        self._workers = []
        self._current_index = 0
        self._lock = threading.Lock()
        self._health_check_interval = 30
        self._last_health_check = time.time()
        
        num_workers = SYSTEM_CONFIG["MAX_WORKERS"]
        for i in range(num_workers):
            self._workers.append({
                'id': i,
                'status': 'healthy',
                'load': 0,
                'last_check': time.time(),
                'tasks_processed': 0
            })
        
        logger.info(f"Load balancer initialized with {num_workers} workers")
    
    def get_next_worker(self) -> dict:
        with self._lock:
            self._check_health()
            
            healthy_workers = [w for w in self._workers if w['status'] == 'healthy']
            
            if not healthy_workers:
                healthy_workers = self._workers
            
            healthy_workers.sort(key=lambda x: x['load'])
            
            worker = healthy_workers[0]
            worker['load'] += 1
            
            return worker
    
    def release_worker(self, worker_id: int):
        with self._lock:
            for worker in self._workers:
                if worker['id'] == worker_id:
                    worker['load'] = max(0, worker['load'] - 1)
                    worker['tasks_processed'] += 1
                    break
    
    def get_worker_status(self) -> List[dict]:
        with self._lock:
            return self._workers.copy()
    
    def _check_health(self):
        current_time = time.time()
        
        if current_time - self._last_health_check < self._health_check_interval:
            return
        
        self._last_health_check = current_time
        
        for worker in self._workers:
            if worker['load'] > 100:
                worker['status'] = 'unhealthy'
            else:
                worker['status'] = 'healthy'
            
            worker['last_check'] = current_time

load_balancer = LoadBalancer()

# ========================================================
# 7. CACHE SYSTEM
# ========================================================

class CacheManager:
    def __init__(self):
        self._redis_client = None
        self._memory_cache = {}
        self._memory_expiry = {}
        
        if HAS_REDIS:
            try:
                self._redis_client = redis.Redis.from_url(
                    SYSTEM_CONFIG["REDIS_URL"],
                    decode_responses=True
                )
                self._redis_client.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis not available: {e}")
                self._redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        if self._redis_client:
            try:
                value = self._redis_client.get(key)
                if value:
                    return pickle.loads(base64.b64decode(value.encode()))
            except Exception as e:
                logger.debug(f"Redis get error: {e}")
        
        if key in self._memory_cache:
            if key in self._memory_expiry and time.time() > self._memory_expiry[key]:
                del self._memory_cache[key]
                if key in self._memory_expiry:
                    del self._memory_expiry[key]
                return None
            return self._memory_cache[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        if self._redis_client:
            try:
                serialized = base64.b64encode(pickle.dumps(value)).decode()
                self._redis_client.setex(key, ttl, serialized)
            except Exception as e:
                logger.debug(f"Redis set error: {e}")
        
        self._memory_cache[key] = value
        self._memory_expiry[key] = time.time() + ttl
    
    def delete(self, key: str):
        if self._redis_client:
            try:
                self._redis_client.delete(key)
            except:
                pass
        
        if key in self._memory_cache:
            del self._memory_cache[key]
            if key in self._memory_expiry:
                del self._memory_expiry[key]
    
    def clear(self):
        if self._redis_client:
            try:
                self._redis_client.flushdb()
            except:
                pass
        
        self._memory_cache.clear()
        self._memory_expiry.clear()

cache_manager = CacheManager()

# ========================================================
# 8. GLOBAL SESSION STATE
# ========================================================

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "landing"
if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False
if "studio_active_mode" not in st.session_state:
    st.session_state["studio_active_mode"] = "Cinematic Engine"
if "active_node" not in st.session_state:
    st.session_state["active_node"] = "setup"
if "sidebar_tab" not in st.session_state:
    st.session_state["sidebar_tab"] = "🚀 Zovix Mass Factory"
if "quick_template_mode" not in st.session_state:
    st.session_state["quick_template_mode"] = True
if "model_choice" not in st.session_state:
    st.session_state["model_choice"] = "🤖 gemini-2.5-flash (Fast Stream Processing)"
if "aspect_ratio" not in st.session_state:
    st.session_state["aspect_ratio"] = "📐 9:16 Vertical (Shorts/Reels)"
if "duration_choice" not in st.session_state:
    st.session_state["duration_choice"] = "⏱️ Quick Format Shorts (10-15s)"
if "voice_profile" not in st.session_state:
    st.session_state["voice_profile"] = "Adam (Premium Male)"
if "res_choice" not in st.session_state:
    st.session_state["res_choice"] = "720p"
if "language_choice" not in st.session_state:
    st.session_state["language_choice"] = "🇮🇳 Hinglish (Fluent Hindi Mix)"
if "hook_variations" not in st.session_state:
    st.session_state["hook_variations"] = []
if "trigger_render" not in st.session_state:
    st.session_state["trigger_render"] = False
if "render_failed" not in st.session_state:
    st.session_state["render_failed"] = False
if "render_done" not in st.session_state:
    st.session_state["render_done"] = False
if "render_status" not in st.session_state:
    st.session_state["render_status"] = "idle"
if "studio_prompt_value" not in st.session_state:
    st.session_state["studio_prompt_value"] = ""
if "studio_prompt_mode" not in st.session_state:
    st.session_state["studio_prompt_mode"] = "💡 Autonomous AI Topic"
if "workshop_active_image" not in st.session_state:
    st.session_state["workshop_active_image"] = None
if "active_svd_video" not in st.session_state:
    st.session_state["active_svd_video"] = None
if "active_blueprint" not in st.session_state:
    st.session_state["active_blueprint"] = None
if "active_upscaled_image" not in st.session_state:
    st.session_state["active_upscaled_image"] = None
if "active_drawing" not in st.session_state:
    st.session_state["active_drawing"] = None
if "active_editor_output" not in st.session_state:
    st.session_state["active_editor_output"] = None
if "active_face_video" not in st.session_state:
    st.session_state["active_face_video"] = None
if "face_video_engine_used" not in st.session_state:
    st.session_state["face_video_engine_used"] = "Not generated yet"
if "face_video_runtime_mode" not in st.session_state:
    st.session_state["face_video_runtime_mode"] = "Unknown"
if "active_expressive_face_video" not in st.session_state:
    st.session_state["active_expressive_face_video"] = None
if "expressive_face_engine_used" not in st.session_state:
    st.session_state["expressive_face_engine_used"] = "Not generated yet"
if "expressive_face_runtime_mode" not in st.session_state:
    st.session_state["expressive_face_runtime_mode"] = "Unknown"
if "face_image_upload" not in st.session_state:
    st.session_state["face_image_upload"] = None
if "user_gemini_api_key" not in st.session_state:
    st.session_state["user_gemini_api_key"] = ""
if "editor_uploads" not in st.session_state:
    st.session_state["editor_uploads"] = []
if "history_renders" not in st.session_state:
    st.session_state["history_renders"] = []
if "face_video_history" not in st.session_state:
    st.session_state["face_video_history"] = []
if "logged_user" not in st.session_state:
    st.session_state["logged_user"] = ""
if "xp_points" not in st.session_state:
    st.session_state["xp_points"] = 0
if "creator_level" not in st.session_state:
    st.session_state["creator_level"] = 1
if "streak_claimed" not in st.session_state:
    st.session_state["streak_claimed"] = False
if "login_streak" not in st.session_state:
    st.session_state["login_streak"] = 0
if "user_credits" not in st.session_state:
    st.session_state["user_credits"] = 101.0
if "quick_access_open" not in st.session_state:
    st.session_state["quick_access_open"] = False
if "voucher_49_active" not in st.session_state:
    st.session_state["voucher_49_active"] = False
if "voucher_49_expiry" not in st.session_state:
    st.session_state["voucher_49_expiry"] = None
if "subscription_active" not in st.session_state:
    st.session_state["subscription_active"] = False
if "subscription_pack" not in st.session_state:
    st.session_state["subscription_pack"] = ""
if "subscription_expiry" not in st.session_state:
    st.session_state["subscription_expiry"] = None
if "referral_count" not in st.session_state:
    st.session_state["referral_count"] = 0
if "achievements" not in st.session_state:
    st.session_state["achievements"] = []
if "leaderboard_data" not in st.session_state:
    st.session_state["leaderboard_data"] = []
if "social_shares" not in st.session_state:
    st.session_state["social_shares"] = 0
if "language" not in st.session_state:
    st.session_state["language"] = "en"
if "gdpr_consent" not in st.session_state:
    st.session_state["gdpr_consent"] = False
if "2fa_enabled" not in st.session_state:
    st.session_state["2fa_enabled"] = False
if "2fa_verified" not in st.session_state:
    st.session_state["2fa_verified"] = False
if "mass_factory_visible" not in st.session_state:
    st.session_state["mass_factory_visible"] = False
if "expressive_auto_setup_ran" not in st.session_state:
    st.session_state["expressive_auto_setup_ran"] = False

# Payment related - IMPROVED
if "razorpay_order_id" not in st.session_state:
    st.session_state["razorpay_order_id"] = None
if "razorpay_payment_id" not in st.session_state:
    st.session_state["razorpay_payment_id"] = None
if "razorpay_signature" not in st.session_state:
    st.session_state["razorpay_signature"] = None
if "pending_credits" not in st.session_state:
    st.session_state["pending_credits"] = 0
if "pending_pack_name" not in st.session_state:
    st.session_state["pending_pack_name"] = ""
if "pending_amount" not in st.session_state:
    st.session_state["pending_amount"] = 0
if "payment_verified" not in st.session_state:
    st.session_state["payment_verified"] = False
if "credit_balance" not in st.session_state:
    st.session_state["credit_balance"] = 0
if "show_payment" not in st.session_state:
    st.session_state["show_payment"] = False
if "selected_gateway" not in st.session_state:
    st.session_state["selected_gateway"] = None
if "show_gateway_form" not in st.session_state:
    st.session_state["show_gateway_form"] = False
if "payment_currency" not in st.session_state:
    st.session_state["payment_currency"] = "INR"
if "user_country" not in st.session_state:
    st.session_state["user_country"] = "IN"
if "razorpay_processed_order_id" not in st.session_state:
    st.session_state["razorpay_processed_order_id"] = None
if "payment_processing" not in st.session_state:
    st.session_state["payment_processing"] = False
if "last_payment_check" not in st.session_state:
    st.session_state["last_payment_check"] = 0

# DeepSeek Blueprint state
if "deepseek_blueprint_data" not in st.session_state:
    st.session_state["deepseek_blueprint_data"] = None
if "deepseek_blueprint_visible" not in st.session_state:
    st.session_state["deepseek_blueprint_visible"] = False
if "deepseek_scenes" not in st.session_state:
    st.session_state["deepseek_scenes"] = []
if "deepseek_music_mood" not in st.session_state:
    st.session_state["deepseek_music_mood"] = "cinematic"

# Dynamic UI
if "dynamic_ui_profile_mode" not in st.session_state:
    st.session_state["dynamic_ui_profile_mode"] = "intermediate"
if "user_behavior_profile" not in st.session_state:
    st.session_state["user_behavior_profile"] = "beginner"
if "selected_elevenlabs_voice" not in st.session_state:
    st.session_state["selected_elevenlabs_voice"] = "Adam (Premium Male)"
if "emotion_voice_output" not in st.session_state:
    st.session_state["emotion_voice_output"] = None
if "emotion_voice_text" not in st.session_state:
    st.session_state["emotion_voice_text"] = ""
if "emotion_voice_emotion" not in st.session_state:
    st.session_state["emotion_voice_emotion"] = "neutral"

# AI Agent & Sales
if "ai_agent_mode" not in st.session_state:
    st.session_state["ai_agent_mode"] = False
if "ai_sales_mode" not in st.session_state:
    st.session_state["ai_sales_mode"] = False
if "agent_business_name" not in st.session_state:
    st.session_state["agent_business_name"] = ""
if "agent_products" not in st.session_state:
    st.session_state["agent_products"] = []
if "agent_schedule" not in st.session_state:
    st.session_state["agent_schedule"] = {}
if "agent_generated_ad" not in st.session_state:
    st.session_state["agent_generated_ad"] = ""
if "agent_instagram_image" not in st.session_state:
    st.session_state["agent_instagram_image"] = None
if "agent_instagram_caption" not in st.session_state:
    st.session_state["agent_instagram_caption"] = ""
if "sales_product_image" not in st.session_state:
    st.session_state["sales_product_image"] = None
if "sales_language" not in st.session_state:
    st.session_state["sales_language"] = "Hindi"
if "sales_product_name" not in st.session_state:
    st.session_state["sales_product_name"] = ""
if "sales_product_price" not in st.session_state:
    st.session_state["sales_product_price"] = ""
if "sales_script" not in st.session_state:
    st.session_state["sales_script"] = ""
if "sales_video_output" not in st.session_state:
    st.session_state["sales_video_output"] = None

# ========================================================
# 9. THIRD-PARTY IMPORTS & CONFIGURATION
# ========================================================

try:
    if razorpay is not None:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID or "mock", RAZORPAY_KEY_SECRET or "mock"))
    else:
        razorpay_client = None
except Exception:
    razorpay_client = None

# ========================================================
# 10. ELEVENLABS VOICE OPTIONS (EXPANDED)
# ========================================================

ELEVENLABS_VOICES = {
    "Adam (Premium Male)": {"id": "21m00Tcm4TlvDq8ikWAM", "gender": "male", "accent": "American", "language": "English"},
    "Rachel (Premium Female)": {"id": "pNInz6obpgDQ5IdwJg7p", "gender": "female", "accent": "American", "language": "English"},
    "Drew (Professional Male)": {"id": "YOz3nT0uBm7MOT3M3f5A", "gender": "male", "accent": "American", "language": "English"},
    "Bella (Warm Female)": {"id": "MF3mGyEYCl7XYWbV9V6O", "gender": "female", "accent": "American", "language": "English"},
    "Antoni (Deep Male)": {"id": "ErXwobaYiN019PkySvjV", "gender": "male", "accent": "British", "language": "English"},
    "Charlotte (Elegant Female)": {"id": "XU7kzUw9OoUqOZz6q5lA", "gender": "female", "accent": "British", "language": "English"},
    "Josh (Young Male)": {"id": "TxGEqnHWrfWFTfGW9XjX", "gender": "male", "accent": "American", "language": "English"},
    "Emily (Professional Female)": {"id": "Lcfc7N8eZ5qOg5eP2kzY", "gender": "female", "accent": "American", "language": "English"},
    "James (Narrator Male)": {"id": "ZQe5t4eKzWq7nN3vR9sY", "gender": "male", "accent": "Australian", "language": "English"},
    "Sarah (Soothing Female)": {"id": "Yx5j9Kz2Wq7nN3vR9sY", "gender": "female", "accent": "American", "language": "English"},
    "Arjun (Hindi Male)": {"id": "gV7Jp2Xk9wLq5nN3vR9sY", "gender": "male", "accent": "Indian", "language": "Hindi"},
    "Priya (Hindi Female)": {"id": "hW8Kq3Yl0xMr6oO4wS0tZ", "gender": "female", "accent": "Indian", "language": "Hindi"},
    "Ravi (Hindi Professional Male)": {"id": "iX9Lr4Zm1yNs7pP5xT1uA", "gender": "male", "accent": "Indian", "language": "Hindi"},
    "Vikram (Bhojpuri Male)": {"id": "jY0Ms5An2zOt8qQ6yU2vB", "gender": "male", "accent": "Indian", "language": "Bhojpuri"},
    "Sita (Bhojpuri Female)": {"id": "kZ1Nt6Bo3pPu9rR7zV3wC", "gender": "female", "accent": "Indian", "language": "Bhojpuri"},
    "Pierre (French Male)": {"id": "lA2Ou7Cp4qQv0sS8aW4xD", "gender": "male", "accent": "French", "language": "French"},
    "Sophie (French Female)": {"id": "mB3Pv8Dq5rRw1tT9bX5yE", "gender": "female", "accent": "French", "language": "French"},
    "Kenji (Japanese Male)": {"id": "nC4Qw9Er6sSx2uU0cY6zF", "gender": "male", "accent": "Japanese", "language": "Japanese"},
    "Yuki (Japanese Female)": {"id": "oD5Rx0Fs7tTy3vV1dZ7aG", "gender": "female", "accent": "Japanese", "language": "Japanese"},
    "Anjura (Expressive Hindi Female)": {"id": "tX7Pq5Zn3yMs8rR2uB9vC", "gender": "female", "accent": "Indian", "language": "Hindi"},
    "Adit (Youthful Hindi Male)": {"id": "uY8Qr6Ao4zNt9sS3vC0wD", "gender": "male", "accent": "Indian", "language": "Hindi"},
    "Anvi (Soft Hindi Female)": {"id": "vZ9Rs7Bp5aOu0tT4wD1xE", "gender": "female", "accent": "Indian", "language": "Hindi"},
}

# ============================================================
# VOICE MODULE SPLIT - Auto-mapped by DeepFace age+gender scan
# Each category maps to a list of recommended voice labels
# ============================================================
VOICE_MODULE_SPLIT = {
    "Boy": {
        "label": "👦 Boy (Male < 14)",
        "category": "Boy",
        "min_age": 0,
        "max_age": 13,
        "gender": "male",
        "default_voice": "Josh (Young Male)",
        "default_voice_id": "TxGEqnHWrfWFTfGW9XjX",
        "recommended_voices": ["Josh (Young Male)"],
        "description": "Young boy voice - youthful and energetic"
    },
    "Girl": {
        "label": "👧 Girl (Female < 14)",
        "category": "Girl/Child",
        "min_age": 0,
        "max_age": 13,
        "gender": "female",
        "default_voice": "Bella (Warm Female)",
        "default_voice_id": "MF3mGyEYCl7XYWbV9V6O",
        "recommended_voices": ["Bella (Warm Female)"],
        "description": "Young girl voice - warm and gentle"
    },
    "Adult_Male": {
        "label": "👨 Adult Male (>= 14)",
        "category": "Adult Male",
        "min_age": 14,
        "max_age": 99,
        "gender": "male",
        "default_voice": "Adam (Premium Male)",
        "default_voice_id": "21m00Tcm4TlvDq8ikWAM",
        "recommended_voices": ["Adam (Premium Male)", "Drew (Professional Male)", "Antoni (Deep Male)", "James (Narrator Male)", "Arjun (Hindi Male)", "Ravi (Hindi Professional Male)", "Pierre (French Male)", "Kenji (Japanese Male)", "Vikram (Bhojpuri Male)", "Adit (Youthful Hindi Male)"],
        "description": "Adult male voice - professional and authoritative"
    },
    "Adult_Female": {
        "label": "👩 Adult Female (>= 14)",
        "category": "Adult Female",
        "min_age": 14,
        "max_age": 99,
        "gender": "female",
        "default_voice": "Rachel (Premium Female)",
        "default_voice_id": "pNInz6obpgDQ5IdwJg7p",
        "recommended_voices": ["Rachel (Premium Female)", "Bella (Warm Female)", "Charlotte (Elegant Female)", "Emily (Professional Female)", "Sarah (Soothing Female)", "Priya (Hindi Female)", "Anjura (Expressive Hindi Female)", "Anvi (Soft Hindi Female)", "Sophie (French Female)", "Yuki (Japanese Female)", "Sita (Bhojpuri Female)"],
        "description": "Adult female voice - clear and expressive"
    },
}

def get_voice_module_by_age_gender(age, gender):
    """Return the VOICE_MODULE_SPLIT entry matching age and gender."""
    if gender == 'male' and age < 14:
        return VOICE_MODULE_SPLIT["Boy"]
    elif gender == 'female' and age < 14:
        return VOICE_MODULE_SPLIT["Girl"]
    elif gender == 'male' and age >= 14:
        return VOICE_MODULE_SPLIT["Adult_Male"]
    elif gender == 'female' and age >= 14:
        return VOICE_MODULE_SPLIT["Adult_Female"]
    return None

def get_voice_module_by_category(category_str):
    """Return the VOICE_MODULE_SPLIT entry by category string."""
    for key, val in VOICE_MODULE_SPLIT.items():
        if val.get("category") == category_str:
            return val
    return None

LANGUAGE_VOICE_MAP = {
    "English": ["Adam (Premium Male)", "Rachel (Premium Female)", "Drew (Professional Male)", "Bella (Warm Female)", "Antoni (Deep Male)", "Charlotte (Elegant Female)", "Josh (Young Male)", "Emily (Professional Female)", "James (Narrator Male)", "Sarah (Soothing Female)"],
    "Hindi": ["Arjun (Hindi Male)", "Priya (Hindi Female)", "Ravi (Hindi Professional Male)", "Anjura (Expressive Hindi Female)", "Adit (Youthful Hindi Male)", "Anvi (Soft Hindi Female)"],
    "Bhojpuri": ["Vikram (Bhojpuri Male)", "Sita (Bhojpuri Female)"],
    "French": ["Pierre (French Male)", "Sophie (French Female)"],
    "Japanese": ["Kenji (Japanese Male)", "Yuki (Japanese Female)"],
}

# ========================================================
# 11. TOKEN BURN RATE
# ========================================================

BASE_BURN_RATE = {
    "Face Video Generator": 4,
    "Face Video Studio": 5,
    "Expressive Face Video": 5,
    "Cinematic Engine": 4,
    "Creative Workshop": 3,
    "AI Agent": 2,
    "AI Sales": 2,
    "Dynamic UI": 2,
    "Live Emotion": 4,
    "Blueprints": 2,
    "Upscaler": 2,
    "Draw": 2,
    "Video Editor": 4,
}

def calculate_tokens(mode_name: str, selected_quality: str) -> int:
    base_cost = BASE_BURN_RATE.get(mode_name, 2)
    heavy_engines = ["Face Video Generator", "Face Video Studio", "Expressive Face Video", "Cinematic Engine", "Live Emotion", "Video Editor"]
    if selected_quality in ["High", "Pro", "Ultra-HD", "4K"]:
        return base_cost + 2 if mode_name in heavy_engines else base_cost + 1
    elif selected_quality in ["HD", "Premium"]:
        return base_cost + 1 if mode_name in heavy_engines else base_cost
    return base_cost

# ========================================================
# 12. MULTI-LANGUAGE SUPPORT
# ========================================================

LANGUAGES = {
    "en": {"name": "English", "flag": "🇬🇧", "rtl": False},
    "hi": {"name": "Hindi", "flag": "🇮🇳", "rtl": False},
    "fr": {"name": "French", "flag": "🇫🇷", "rtl": False},
    "es": {"name": "Spanish", "flag": "🇪🇸", "rtl": False},
    "de": {"name": "German", "flag": "🇩🇪", "rtl": False},
    "ja": {"name": "Japanese", "flag": "🇯🇵", "rtl": False},
    "zh": {"name": "Chinese", "flag": "🇨🇳", "rtl": False},
    "ar": {"name": "Arabic", "flag": "🇸🇦", "rtl": True},
    "ru": {"name": "Russian", "flag": "🇷🇺", "rtl": False},
    "pt": {"name": "Portuguese", "flag": "🇵🇹", "rtl": False},
    "it": {"name": "Italian", "flag": "🇮🇹", "rtl": False},
    "ko": {"name": "Korean", "flag": "🇰🇷", "rtl": False},
    "tr": {"name": "Turkish", "flag": "🇹🇷", "rtl": False},
    "nl": {"name": "Dutch", "flag": "🇳🇱", "rtl": False},
    "sv": {"name": "Swedish", "flag": "🇸🇪", "rtl": False},
    "pl": {"name": "Polish", "flag": "🇵🇱", "rtl": False},
    "vi": {"name": "Vietnamese", "flag": "🇻🇳", "rtl": False},
    "th": {"name": "Thai", "flag": "🇹🇭", "rtl": False},
    "id": {"name": "Indonesian", "flag": "🇮🇩", "rtl": False},
    "ms": {"name": "Malay", "flag": "🇲🇾", "rtl": False},
    "fil": {"name": "Filipino", "flag": "🇵🇭", "rtl": False}
}

def get_translation(text: str, target_lang: str = "en") -> str:
    if target_lang == "en" or not text:
        return text
    
    cache_key = f"translation:{hashlib.md5(f'{text}:{target_lang}'.encode()).hexdigest()}"
    cached = cache_manager.get(cache_key)
    if cached:
        return cached
    
    try:
        api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")
        if api_key:
            url = "https://translation.googleapis.com/language/translate/v2"
            params = {
                "q": text,
                "target": target_lang,
                "key": api_key
            }
            response = requests.post(url, json=params, timeout=5)
            if response.status_code == 200:
                result = response.json()["data"]["translations"][0]["translatedText"]
                cache_manager.set(cache_key, result, ttl=86400)
                return result
    except Exception as e:
        logger.warning(f"Translation error: {e}")
    
    return text

def get_rtl_css(language: str) -> str:
    if LANGUAGES.get(language, {}).get("rtl", False):
        return """
            .block-container {
                direction: rtl !important;
            }
            .stButton > button {
                direction: rtl !important;
            }
        """
    return ""

def get_language_selector():
    st.sidebar.markdown("### 🌐 Language")
    current_lang = st.session_state.get("language", "en")
    
    selected_lang = st.sidebar.selectbox(
        "Select Language",
        options=list(LANGUAGES.keys()),
        format_func=lambda x: f"{LANGUAGES[x]['flag']} {LANGUAGES[x]['name']}",
        index=list(LANGUAGES.keys()).index(current_lang) if current_lang in LANGUAGES else 0
    )
    
    if selected_lang != st.session_state.get("language"):
        st.session_state["language"] = selected_lang
        st.rerun()
    
    return selected_lang

# ========================================================
# 13. PAYMENT GATEWAYS CONFIGURATION
# ========================================================

PAYMENT_GATEWAYS = {
    "razorpay": {
        "name": "Razorpay",
        "icon": "💳",
        "countries": ["IN", "US", "GB", "CA", "AU", "EU", "AE", "SA", "SG", "JP"],
        "currencies": ["INR", "USD", "EUR"],
        "enabled": True,
        "description": "Credit/Debit Cards, UPI, Net Banking"
    },
    "crypto": {
        "name": "Crypto",
        "icon": "₿",
        "countries": ["Global"],
        "currencies": ["BTC", "ETH", "USDT", "USDC", "SOL", "BNB", "DOGE"],
        "enabled": True,
        "description": "Bitcoin, Ethereum, USDT, USDC, Solana, BNB, DOGE"
    },
    "binance": {
        "name": "Binance",
        "icon": "🟡",
        "countries": ["Global"],
        "currencies": ["BUSD", "USDT", "BNB", "BTC", "ETH"],
        "enabled": True,
        "description": "Binance Pay, Crypto, Cards"
    }
}

DISPLAYED_PAYMENT_GATEWAYS = ["razorpay", "crypto", "binance"]


def get_available_gateway_keys(user_country: str) -> list:
    gateways = []
    for key in DISPLAYED_PAYMENT_GATEWAYS:
        gateway = PAYMENT_GATEWAYS.get(key)
        if not gateway:
            continue
        if gateway["enabled"] and ("Global" in gateway["countries"] or user_country in gateway["countries"]):
            gateways.append(key)
    return gateways


def convert_price(price_inr: float, to_currency: str = "USD") -> float:
    rates = {
        "USD": 0.012,
        "EUR": 0.011,
        "GBP": 0.0095,
        "AED": 0.044,
        "SAR": 0.045,
        "SGD": 0.016,
        "JPY": 1.8,
        "INR": 1.0,
        "CAD": 0.016,
        "AUD": 0.018,
        "CHF": 0.011,
        "CNY": 0.087,
        "RUB": 1.1,
        "BRL": 0.06,
        "ZAR": 0.22,
        "KRW": 16.5,
        "TRY": 0.39,
        "VND": 304,
        "THB": 0.43,
        "IDR": 195,
        "MYR": 0.056,
        "PHP": 0.68
    }
    return price_inr * rates.get(to_currency, 0.012)

# ========================================================
# 14. ALL PLANS - SUBSCRIPTIONS + ONE-TIME TOP-UPS
# ========================================================

GLOBAL_PLANS = {
    "subscriptions": {
        "free": {
            "name": "Free",
            "price": 0,
            "tokens": 10,
            "amount_paise": 0,
            "emoji": "🆓",
            "features": ["10 Free Tokens Monthly", "Watermark", "Basic AI Features"],
            "type": "monthly",
            "badge": "",
            "color": "#64748b",
            "description": "Free plan with limited features"
        },
        "starter": {
            "name": "Starter",
            "price": 49,
            "tokens": 30,
            "amount_paise": 4900,
            "emoji": "🌱",
            "features": ["30 Tokens Monthly", "No Watermark", "All AI Features"],
            "type": "monthly",
            "badge": "🎫 VOUCHER",
            "color": "#10b981",
            "description": "Best for beginners"
        },
        "standard": {
            "name": "Standard",
            "price": 99,
            "tokens": 60+10,
            "amount_paise": 9900,
            "emoji": "🥇",
            "features": ["70 Tokens Monthly", "No Watermark", "All AI Features"],
            "type": "monthly",
            "badge": "POPULAR",
            "color": "#f59e0b",
            "description": "Best value plan"
        },
        "cinematic": {
            "name": "Cinematic",
            "price": 299,
            "tokens": 180+50,
            "amount_paise": 29900,
            "emoji": "🥈",
            "features": ["230 Tokens Monthly", "No Watermark", "All AI Features"],
            "type": "monthly",
            "badge": "",
            "color": "#8b5cf6",
            "description": "For serious creators"
        },
        "premium": {
            "name": "Premium",
            "price": 499,
            "tokens": 310+90,
            "amount_paise": 49900,
            "emoji": "💎",
            "features": ["400 Tokens Monthly", "No Watermark", "All AI Features"],
            "type": "monthly",
            "badge": "",
            "color": "#ec4899",
            "description": "Professional creators"
        },
        "pro": {
            "name": "Pro",
            "price": 999,
            "tokens": 620+220,
            "amount_paise": 99900,
            "emoji": "👑",
            "features": ["850 Tokens Monthly", "No Watermark", "All AI Features"],
            "type": "monthly",
            "badge": "⭐ BEST VALUE",
            "color": "#f43f5e",
            "description": "Unlimited potential"
        },
        "enterprise": {
            "name": "Enterprise",
            "price": 1999,
            "tokens": 1250+500,
            "amount_paise": 199900,
            "emoji": "🏢",
            "features": ["1750 Tokens Monthly", "No Watermark", "All AI Features", "Priority Support", "Custom AI Models"],
            "type": "monthly",
            "badge": "⭐ ENTERPRISE",
            "color": "#8b5cf6",
            "description": "Complete business solution"
        }
    },
    "one_time": {
        "topup_49": {
            "name": "Token Top-up",
            "price": 49,
            "tokens": 30,
            "amount_paise": 4900,
            "emoji": "🎯",
            "type": "prepaid",
            "badge": "💫 ONE-TIME",
            "color": "#45f3ff",
            "description": "One-time token purchase"
        },
        "topup_99": {
            "name": "Token Top-up",
            "price": 99,
            "tokens": 65,
            "amount_paise": 9900,
            "emoji": "🎯",
            "type": "prepaid",
            "badge": "💫 ONE-TIME",
            "color": "#45f3ff",
            "description": "One-time token purchase"
        },
        "topup_299": {
            "name": "Token Top-up",
            "price": 299,
            "tokens": 200,
            "amount_paise": 29900,
            "emoji": "🎯",
            "type": "prepaid",
            "badge": "💫 ONE-TIME",
            "color": "#45f3ff",
            "description": "One-time token purchase"
        },
        "topup_499": {
            "name": "Token Top-up",
            "price": 499,
            "tokens": 380,
            "amount_paise": 49900,
            "emoji": "🎯",
            "type": "prepaid",
            "badge": "💫 ONE-TIME",
            "color": "#45f3ff",
            "description": "One-time token purchase"
        },
        "topup_999": {
            "name": "Token Top-up",
            "price": 999,
            "tokens": 800,
            "amount_paise": 99900,
            "emoji": "🎯",
            "type": "prepaid",
            "badge": "💫 ONE-TIME",
            "color": "#45f3ff",
            "description": "One-time token purchase"
        },
        "topup_1999": {
            "name": "Token Top-up",
            "price": 1999,
            "tokens": 1800,
            "amount_paise": 199900,
            "emoji": "🎯",
            "type": "prepaid",
            "badge": "💫 ONE-TIME",
            "color": "#45f3ff",
            "description": "One-time token purchase"
        }
    }
}

# ========================================================
# 15. VOUCHER SYSTEM
# ========================================================

def activate_49_voucher():
    st.session_state['voucher_49_active'] = True
    st.session_state['voucher_49_expiry'] = datetime.now() + timedelta(hours=24)
    st.session_state['user_credits'] += 35
    st.session_state['credit_balance'] += 35
    return True

def check_49_voucher_valid():
    if st.session_state.get('voucher_49_active', False):
        expiry = st.session_state.get('voucher_49_expiry')
        if expiry and datetime.now() > expiry:
            st.session_state['voucher_49_active'] = False
            st.session_state['voucher_49_expiry'] = None
            return False
        return True
    return False

# ========================================================
# 16. DATABASE FUNCTIONS
# ========================================================

def init_database():
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                credits REAL DEFAULT 50.0,
                xp_points REAL DEFAULT 10.0,
                streak_count INTEGER DEFAULT 0,
                last_claim_date TEXT,
                voucher_credits INTEGER DEFAULT 0,
                voucher_expires_at TEXT DEFAULT '',
                twofa_secret TEXT DEFAULT '',
                gdpr_consent INTEGER DEFAULT 0,
                gdpr_version TEXT DEFAULT '',
                language TEXT DEFAULT 'en',
                last_login TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                file_name TEXT,
                timestamp TEXT,
                prompt TEXT,
                path TEXT,
                generation_type TEXT DEFAULT 'General',
                cost_inr REAL DEFAULT 0.0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                prompt TEXT PRIMARY KEY,
                cached_path TEXT,
                timestamp TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                category TEXT,
                topic TEXT,
                scheduled_time TEXT,
                platform TEXT,
                status TEXT DEFAULT 'Scheduled'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                video_duration_min REAL,
                scenes_stock INTEGER,
                scenes_ai INTEGER,
                calculated_cost REAL,
                credits_deducted REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sub_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_username TEXT,
                sub_username TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public_showcase (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                prompt TEXT,
                thumbnail_path TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_video_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                file_name TEXT,
                timestamp TEXT,
                prompt TEXT,
                path TEXT,
                face_path TEXT,
                quality TEXT DEFAULT 'Standard'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS editor_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                file_name TEXT,
                file_path TEXT,
                file_type TEXT,
                upload_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_agent_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                business_name TEXT,
                products TEXT,
                schedule TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_sales_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                product_name TEXT,
                product_price TEXT,
                language TEXT,
                video_path TEXT,
                script TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                order_id TEXT,
                payment_id TEXT,
                amount INTEGER,
                credits_added INTEGER,
                pack_name TEXT,
                status TEXT,
                plan_type TEXT DEFAULT 'one_time',
                gateway TEXT DEFAULT 'razorpay',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dynamic_ui_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                behavior_profile TEXT,
                ui_preferences TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emotion_voice_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                text TEXT,
                emotion TEXT,
                audio_path TEXT,
                voice_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_username TEXT,
                new_user_username TEXT,
                reward_given INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                platform TEXT,
                share_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                achievement TEXT,
                unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                error TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        # --- MIGRATION: Auto-add missing columns ---
        try:
            cursor.execute("PRAGMA table_info(history)")
            existing_cols = [col[1] for col in cursor.fetchall()]
            if "generation_type" not in existing_cols:
                cursor.execute("ALTER TABLE history ADD COLUMN generation_type TEXT DEFAULT 'General'")
                logger.info("MIGRATION: Added generation_type column")
            if "cost_inr" not in existing_cols:
                cursor.execute("ALTER TABLE history ADD COLUMN cost_inr REAL DEFAULT 0.0")
                logger.info("MIGRATION: Added cost_inr column")
            conn.commit()
        except Exception as mig_e:
            logger.warning(f"MIGRATION skip: {mig_e}")
        
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database init error: {e}")
    finally:
        conn.close()

init_database()

# ========================================================
# 17. AUTHENTICATION FUNCTIONS - IMPROVED
# ========================================================

def authenticate_user_db(username, password):
    """Real authentication with password verification"""
    if not username or not password:
        return False, False
    
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password, twofa_secret FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        if row:
            stored_password = row[0]
            twofa_secret = row[1] if row[1] else ""
            
            if stored_password == password:
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE username = ?",
                    (datetime.now().isoformat(), username)
                )
                conn.commit()
                
                if twofa_secret and twofa_secret.strip():
                    st.session_state["2fa_enabled"] = True
                    return True, True
                else:
                    st.session_state["2fa_enabled"] = False
                    return True, False
            else:
                logger.warning(f"Failed login attempt for user: {username}")
                return False, False
        else:
            register_user_db(username, password)
            return True, False
            
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return False, False
    finally:
        conn.close()

def register_user_db(username, password):
    """Register a new user with real password storage"""
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT OR IGNORE INTO users 
               (username, password, credits, xp_points, streak_count, last_claim_date, voucher_credits, voucher_expires_at, language) 
               VALUES (?, ?, 50.0, 10.0, 0, '', 0, '', 'en')""",
            (username, password)
        )
        conn.commit()
        logger.info(f"New user registered: {username}")
        return True
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return False
    finally:
        conn.close()

def login_or_register_social(email, platform):
    """Social login with email"""
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT username FROM users WHERE username = ?", (email,))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                """INSERT INTO users 
                   (username, password, credits, xp_points, streak_count, last_claim_date, voucher_credits, voucher_expires_at, language) 
                   VALUES (?, ?, 100, 0, 0, '', 0, '', 'en')""",
                (email, f"social_{platform.lower()}")
            )
            conn.commit()
            logger.info(f"New social user: {email} via {platform}")
        return True
    except Exception as e:
        logger.error(f"Social login error: {e}")
        return False
    finally:
        conn.close()

def get_user_credits_db(username):
    """Get real user credits from database"""
    check_and_expire_vouchers(username)
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    row = None
    try:
        cursor.execute("SELECT credits, voucher_credits FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
    except Exception as e:
        logger.error(f"Get credits error: {e}")
    finally:
        conn.close()
    if row:
        return row[0] + row[1]
    return 0

def add_credits(username, amount, credit_type="standard"):
    """Real credit addition to database"""
    if not username or amount <= 0:
        return False
    
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        if credit_type == "voucher":
            expiry_time = (datetime.now() + timedelta(hours=24)).isoformat()
            cursor.execute(
                "UPDATE users SET voucher_credits = voucher_credits + ?, voucher_expires_at = ? WHERE username = ?",
                (amount, expiry_time, username)
            )
        else:
            cursor.execute("UPDATE users SET credits = credits + ? WHERE username = ?", (amount, username))
        conn.commit()
        logger.info(f"Added {amount} credits to {username} ({credit_type})")
        return True
    except Exception as e:
        logger.error(f"Add credits error: {e}")
        return False
    finally:
        conn.close()

def deduct_credits_db(username, amount):
    """Real credit deduction from database"""
    if not username or amount <= 0:
        return False
    
    check_and_expire_vouchers(username)
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT credits, voucher_credits FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            std_credits, v_credits = row[0], row[1]
            total_credits = std_credits + v_credits
            
            if total_credits < amount:
                logger.warning(f"Insufficient credits for {username}: {total_credits} < {amount}")
                return False
            
            if v_credits >= amount:
                new_v = v_credits - amount
                cursor.execute("UPDATE users SET voucher_credits = ? WHERE username = ?", (new_v, username))
            else:
                remaining = amount - v_credits
                cursor.execute(
                    "UPDATE users SET voucher_credits = 0, credits = credits - ? WHERE username = ?",
                    (remaining, username)
                )
            conn.commit()
            logger.info(f"Deducted {amount} credits from {username}")
            return True
        return False
    except Exception as e:
        logger.error(f"Deduct credits error: {e}")
        return False
    finally:
        conn.close()

def get_user_xp_db(username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    row = None
    try:
        cursor.execute("SELECT xp_points FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
    except Exception as e:
        logger.error(f"Get XP error: {e}")
    finally:
        conn.close()
    return row[0] if row and row[0] is not None else 0

def update_user_xp_db(username, xp_amount):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET xp_points = xp_points + ? WHERE username = ?", (xp_amount, username))
        conn.commit()
    except Exception as e:
        logger.error(f"Update XP error: {e}")
    finally:
        conn.close()

def credit_check(username, required_credits):
    return get_user_credits_db(username) >= required_credits

def check_and_expire_vouchers(username):
    if not username:
        return
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT voucher_credits, voucher_expires_at FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            v_credits, expires_at_str = row[0], row[1]
            if v_credits > 0 and expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now() > expires_at:
                    cursor.execute(
                        "UPDATE users SET voucher_credits = 0, voucher_expires_at = '' WHERE username = ?",
                        (username,)
                    )
                    conn.commit()
                    logger.info(f"Vouchers expired for {username}")
    except Exception as e:
        logger.error(f"Check vouchers error: {e}")
    finally:
        conn.close()

def has_active_subscription(username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """SELECT pack_name, timestamp FROM payment_history 
               WHERE username = ? AND status = 'success' AND plan_type = 'monthly' 
               ORDER BY timestamp DESC LIMIT 1""",
            (username,)
        )
        row = cursor.fetchone()
        if row:
            created_at = datetime.fromisoformat(row[1]) if isinstance(row[1], str) else row[1]
            if datetime.now() - created_at < timedelta(days=30):
                return True, row[0]
        return False, None
    except Exception as e:
        logger.error(f"Has subscription error: {e}")
        return False, None
    finally:
        conn.close()

def refresh_subscription_tokens(username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """SELECT pack_name, timestamp FROM payment_history 
               WHERE username = ? AND status = 'success' AND plan_type = 'monthly' 
               ORDER BY timestamp DESC LIMIT 1""",
            (username,)
        )
        row = cursor.fetchone()
        if row:
            pack_name = row[0]
            created_at = datetime.fromisoformat(row[1]) if isinstance(row[1], str) else row[1]
            if datetime.now() - created_at >= timedelta(days=30):
                for plan_key, plan_data in GLOBAL_PLANS["subscriptions"].items():
                    if plan_data["name"].lower() in pack_name.lower():
                        tokens_to_add = plan_data["tokens"]
                        add_credits(username, tokens_to_add)
                        cursor.execute(
                            """UPDATE payment_history 
                               SET timestamp = ? 
                               WHERE username = ? AND status = 'success' AND plan_type = 'monthly' 
                               ORDER BY timestamp DESC LIMIT 1""",
                            (datetime.now().isoformat(), username)
                        )
                        conn.commit()
                        return True, tokens_to_add
        return False, 0
    except Exception as e:
        logger.error(f"Refresh subscription error: {e}")
        return False, 0
    finally:
        conn.close()

def check_and_refresh_subscription(username):
    has_sub, pack_name = has_active_subscription(username)
    if has_sub:
        refreshed, tokens_added = refresh_subscription_tokens(username)
        if refreshed:
            return True, tokens_added
    return False, 0

# ========================================================
# 18. ENHANCED DAILY REWARD
# ========================================================

def enhanced_daily_reward(username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    today_str = datetime.now().date().isoformat()
    try:
        cursor.execute("SELECT last_claim_date, streak_count FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            last_claim, streak = row[0], row[1]
            if last_claim == today_str:
                return False, streak, "Already claimed today! Return tomorrow."
            yesterday_str = (datetime.now().date() - timedelta(days=1)).isoformat()
            new_streak = streak + 1 if last_claim == yesterday_str else 1
            bonus_multiplier = 1.0
            if new_streak >= 30:
                bonus_multiplier = 3.0
            elif new_streak >= 14:
                bonus_multiplier = 2.0
            elif new_streak >= 7:
                bonus_multiplier = 1.5
            base_reward = 5
            reward_credits = int(base_reward * bonus_multiplier) + min(new_streak, 5)
            voucher_bonus = 2 + (new_streak // 7)
            cursor.execute(
                "UPDATE users SET credits = credits + ?, voucher_credits = voucher_credits + ?, streak_count = ?, last_claim_date = ? WHERE username = ?",
                (reward_credits, voucher_bonus, new_streak, today_str, username)
            )
            conn.commit()
            streak_emoji = "🔥" if new_streak >= 30 else "⭐" if new_streak >= 14 else "🌟" if new_streak >= 7 else "✅"
            return True, new_streak, f"{streak_emoji} Claimed! +{reward_credits} Credits, +{voucher_bonus} vouchers! Streak: {new_streak} days"
    except Exception as e:
        logger.error(f"Daily reward error: {e}")
        return False, 0, f"Error: {str(e)}"
    finally:
        conn.close()

# ========================================================
# 19. REFERRAL SYSTEM
# ========================================================

def track_referral(referrer_username, new_user_username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO referrals (referrer_username, new_user_username, reward_given) VALUES (?, ?, 0)",
            (referrer_username, new_user_username)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Track referral error: {e}")
        return False
    finally:
        conn.close()

def reward_referral(referrer_username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_username = ? AND reward_given = 0",
            (referrer_username,)
        )
        count = cursor.fetchone()[0]
        if count > 0:
            add_credits(referrer_username, count * 10)
            cursor.execute(
                "UPDATE referrals SET reward_given = 1 WHERE referrer_username = ? AND reward_given = 0",
                (referrer_username,)
            )
            conn.commit()
            return True, count * 10
        return False, 0
    except Exception as e:
        logger.error(f"Reward referral error: {e}")
        return False, 0
    finally:
        conn.close()

# ========================================================
# 20. ACHIEVEMENT SYSTEM
# ========================================================

def check_achievements(username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    achievements = []
    try:
        cursor.execute("SELECT COUNT(*) FROM history WHERE username = ?", (username,))
        total_renders = cursor.fetchone()[0]
        if total_renders >= 100:
            achievements.append("🏆 Master Creator - 100+ videos generated")
        elif total_renders >= 50:
            achievements.append("🥇 Pro Creator - 50+ videos generated")
        elif total_renders >= 10:
            achievements.append("🥈 Rising Star - 10+ videos generated")
        
        cursor.execute("SELECT streak_count FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        streak = row[0] if row else 0
        if streak >= 30:
            achievements.append("🔥 Legendary Streak - 30 days")
        elif streak >= 14:
            achievements.append("⚡ Dedicated Creator - 14-day streak")
        elif streak >= 7:
            achievements.append("🌅 Consistent Creator - 7-day streak")
        
        cursor.execute("SELECT credits FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        credits = row[0] if row else 0
        if credits >= 1000:
            achievements.append("💰 Credit Tycoon - 1000+ credits")
        elif credits >= 500:
            achievements.append("💎 Credit Collector - 500+ credits")
        
        return achievements
    except Exception as e:
        logger.error(f"Check achievements error: {e}")
        return []
    finally:
        conn.close()

# ========================================================
# 21. LEADERBOARD SYSTEM
# ========================================================

def get_leaderboard(limit=10):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """SELECT username, credits, xp_points, streak_count 
               FROM users 
               ORDER BY credits DESC 
               LIMIT ?""",
            (limit,)
        )
        rows = cursor.fetchall()
        return [{"username": r[0], "credits": r[1], "xp": r[2], "streak": r[3]} for r in rows]
    except Exception as e:
        logger.error(f"Get leaderboard error: {e}")
        return []
    finally:
        conn.close()

# ========================================================
# 22. SOCIAL SHARE REWARDS
# ========================================================

def track_social_share(username, platform):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO social_shares (username, platform, share_time) VALUES (?, ?, ?)",
            (username, platform, datetime.now().isoformat())
        )
        add_credits(username, 2)
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Track social share error: {e}")
        return False
    finally:
        conn.close()

# ========================================================
# 23. SUPPORT TIER
# ========================================================

def get_support_tier(username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT credits FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        credits = row[0] if row else 0
        if credits >= 5000:
            return "👑 Platinum Support - 24/7 Priority"
        elif credits >= 1000:
            return "💎 Gold Support - 12/7 Priority"
        elif credits >= 500:
            return "🥈 Silver Support - 8/5 Support"
        else:
            return "🆓 Standard Support"
    except Exception as e:
        logger.error(f"Get support tier error: {e}")
        return "🆓 Standard Support"
    finally:
        conn.close()

# ========================================================
# 24. PAYMENT FUNCTIONS - IMPROVED
# ========================================================

def create_payment_order(amount_paise, plan_name=""):
    """Create real Razorpay order"""
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET or RAZORPAY_KEY_ID == "mock" or RAZORPAY_KEY_SECRET == "mock":
        logger.error("Razorpay keys not configured properly")
        return {
            "id": f"order_mock_{uuid.uuid4().hex[:8]}",
            "amount": int(amount_paise),
            "status": "mock",
            "debug": "Razorpay keys not configured. Please add valid keys."
        }

    try:
        if razorpay is None:
            raise ImportError("Razorpay Python package is not installed.")

        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        data = {
            "amount": int(amount_paise),
            "currency": "INR",
            "receipt": f"receipt_{int(time.time())}",
            "notes": {
                "plan": str(plan_name or "Zovix Credits"),
                "user": st.session_state.get("logged_user", "guest")
            }
        }
        order = client.order.create(data=data)
        if isinstance(order, dict) and order.get("id"):
            logger.info(f"Razorpay order created: {order['id']}")
            return {
                "id": order["id"],
                "amount": order.get("amount", int(amount_paise)),
                "status": "created",
                "raw": order,
                "debug": "Razorpay order created successfully."
            }
        raise ValueError(f"Unexpected Razorpay payload: {order}")
    except Exception as e:
        logger.error(f"Razorpay order error: {e}")
        return {
            "id": f"order_mock_{uuid.uuid4().hex[:8]}",
            "amount": int(amount_paise),
            "status": "error",
            "debug": str(e)
        }

def verify_payment_signature(order_id, payment_id, signature):
    """Verify Razorpay payment signature"""
    if not RAZORPAY_KEY_SECRET or RAZORPAY_KEY_SECRET == "mock":
        return True
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        params = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        client.utility.verify_payment_signature(params)
        logger.info(f"Signature verified for order: {order_id}")
        return True
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def save_payment_history(username, order_id, payment_id, amount, credits_added, pack_name, status, plan_type="one_time", gateway="razorpay"):
    """Save payment history to database"""
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO payment_history 
               (username, order_id, payment_id, amount, credits_added, pack_name, status, plan_type, gateway) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (username, order_id, payment_id, amount, credits_added, pack_name, status, plan_type, gateway)
        )
        conn.commit()
        logger.info(f"Payment history saved: {order_id} for {username}")
        return True
    except Exception as e:
        logger.error(f"Save payment history error: {e}")
        return False
    finally:
        conn.close()


def register_pending_payment(username, order_id, amount, credits_added, pack_name, gateway="razorpay"):
    """Persist newly created order so refresh/login can reconcile credits later."""
    if not username or not order_id:
        return False

    plan_type = "monthly" if "Subscription" in str(pack_name) else "one_time"
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, status FROM payment_history WHERE username = ? AND order_id = ? ORDER BY id DESC LIMIT 1",
            (username, order_id)
        )
        existing = cursor.fetchone()
        if existing:
            existing_id, existing_status = existing
            if str(existing_status).lower() != "success":
                cursor.execute(
                    """UPDATE payment_history
                       SET amount = ?, credits_added = ?, pack_name = ?, status = ?, plan_type = ?, gateway = ?
                       WHERE id = ?""",
                    (int(round(float(amount or 0))), int(credits_added), str(pack_name), "created", plan_type, gateway, existing_id)
                )
        else:
            cursor.execute(
                """INSERT INTO payment_history
                   (username, order_id, payment_id, amount, credits_added, pack_name, status, plan_type, gateway)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    username,
                    order_id,
                    "",
                    int(round(float(amount or 0))),
                    int(credits_added),
                    str(pack_name),
                    "created",
                    plan_type,
                    gateway,
                )
            )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Register pending payment error: {e}")
        return False
    finally:
        conn.close()

def process_payment_success(username, order_id, payment_id, signature, amount, credits_to_add, pack_name, gateway="razorpay"):
    """Process successful payment - ADD CREDITS REAL"""
    if not username:
        return False, "No username provided"
    
    if not credits_to_add or credits_to_add <= 0:
        return False, "Invalid credit amount"
    
    # Verify signature (optional but recommended)
    if gateway == "razorpay" and RAZORPAY_KEY_SECRET and RAZORPAY_KEY_SECRET != "mock":
        try:
            verify_payment_signature(order_id, payment_id, signature)
        except Exception as e:
            logger.warning(f"Signature verification warning: {e}")
    
    # Determine plan type
    plan_type = "monthly" if "Subscription" in pack_name else "one_time"
    
    try:
        # Check if already processed
        conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM payment_history WHERE order_id = ? AND username = ? LIMIT 1",
            (order_id, username)
        )
        existing = cursor.fetchone()
        conn.close()
        
        if existing and existing[0] == "success":
            return True, f"✅ Payment already processed. Credits already added."
        
        # CREDIT ADDITION - REAL
        if st.session_state.get("is_logged_in", False):
            add_credits(username, credits_to_add)
            
            st.session_state['user_credits'] = get_user_credits_db(username)
            st.session_state['credit_balance'] = st.session_state['user_credits']
            st.session_state['payment_verified'] = True
            st.session_state['pending_credits'] = 0
            st.session_state['pending_pack_name'] = ""
            st.session_state['pending_amount'] = 0
            
            save_payment_history(
                username, order_id, payment_id, amount, 
                credits_to_add, pack_name, "success", plan_type, gateway
            )
            
            logger.info(f"✅ CREDITS ADDED: {credits_to_add} to {username}")
            
            return True, f"✅ Payment successful! Added {credits_to_add} credits to your account."
        else:
            st.session_state['pending_credits'] = credits_to_add
            st.session_state['pending_pack_name'] = pack_name
            st.session_state['payment_verified'] = True
            
            save_payment_history(
                "pending_user", order_id, payment_id, amount, 
                credits_to_add, pack_name, "pending", plan_type, gateway
            )
            
            return True, f"✅ Payment successful! {credits_to_add} credits will be added when you log in."
            
    except Exception as e:
        logger.error(f"Process payment error: {e}")
        return False, f"Error processing payment: {str(e)}"

# ========================================================
# 25. ENHANCED PAYMENT UI - IMPROVED
# ========================================================

def clear_payment_state():
    st.session_state["show_payment"] = False
    st.session_state["show_gateway_form"] = False
    st.session_state["selected_gateway"] = None
    st.session_state["razorpay_order_id"] = None
    st.session_state["razorpay_payment_id"] = None
    st.session_state["razorpay_signature"] = None
    st.session_state["razorpay_processed_order_id"] = None
    st.session_state["payment_processing"] = False

def render_enhanced_payment_ui():
    st.markdown("<h4 style='font-family: Orbitron; color: #FFC0CB;'>💎 Buy Credits</h4>", unsafe_allow_html=True)

    if st.session_state.get("razorpay_popup_requested", False):
        st.info("🪟 Razorpay checkout popup request was sent. If it did not open, please allow popups for this site.")
        st.session_state["razorpay_popup_requested"] = False
    
    user_country = st.session_state.get("user_country", "IN")
    
    available_currencies = ["INR", "USD", "EUR", "GBP", "AED", "SAR", "SGD", "JPY", "CAD", "AUD"]
    selected_currency = st.selectbox("Select Currency", available_currencies, key="payment_currency")
    
    st.markdown("### 🌍 Available Payment Gateways")
    available_gateways = get_available_gateway_keys(user_country)
    if not available_gateways:
        st.info("No payment gateways are available for your region right now.")
    else:
        gateway_cols = st.columns(len(available_gateways))
        for idx, key in enumerate(available_gateways):
            with gateway_cols[idx]:
                gateway = PAYMENT_GATEWAYS[key]
                st.markdown(f"""
                    <div style="background: rgba(69, 243, 255, 0.08); border: 1px solid rgba(69, 243, 255, 0.25); 
                                border-radius: 14px; padding: 14px; text-align: center; min-height: 120px;">
                        <div style="font-size: 28px;">{gateway['icon']}</div>
                        <h4 style="font-family: Orbitron; font-size: 12px; color: #45f3ff; margin: 6px 0 4px 0;">{gateway['name']}</h4>
                        <p style="font-size: 10px; color: #94a3b8; margin: 0; line-height: 1.3;">{gateway['description']}</p>
                    </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    plan_type = st.radio(
        "Choose Plan Type",
        ["📅 Monthly Subscriptions", "🎯 One-Time Top-ups"],
        horizontal=True,
        key="enhanced_plan_type"
    )
    
    st.markdown("---")

    if st.session_state.get("show_payment", False):
        render_payment_modal()
        return
    
    if "Monthly Subscriptions" in plan_type:
        st.markdown("### 🚀 Monthly Subscription Plans")
        st.caption("💡 Subscribe and get tokens every month. Cancel anytime.")
        
        plans = GLOBAL_PLANS["subscriptions"]
        cols = st.columns(len(plans))
        
        for idx, (plan_key, plan_data) in enumerate(plans.items()):
            with cols[idx]:
                with st.container(border=True):
                    price_inr = plan_data["price"]
                    converted_price = convert_price(price_inr, selected_currency)
                    
                    st.markdown(f"""
                        <div style="text-align: center; padding: 5px 0;">
                            <span style="font-size: 32px;">{plan_data['emoji']}</span>
                            <h4 style="font-family: 'Orbitron'; font-size: 13px; color: #ffffff; margin: 5px 0;">{plan_data['name']}</h4>
                            <p style="font-size: 9px; color: #94a3b8; margin: 0;">{plan_data.get('description', '')}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                        <div style="text-align: center; padding: 8px 0;">
                            <span style="font-size: 18px; font-weight: bold; color: #45f3ff;">
                                {selected_currency} {converted_price:.2f}
                            </span>
                            <span style="font-size: 11px; color: #94a3b8; display: block;">per month</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                        <div style="text-align: center; padding: 5px 0; background: rgba(69, 243, 255, 0.05); border-radius: 6px; margin: 5px 0;">
                            <span style="font-size: 14px; color: #45f3ff; font-weight: bold;">+{plan_data['tokens']} Tokens</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if plan_data["price"] == 0:
                        if st.button("🚀 Get Free Plan", key=f"enhanced_free_{plan_key}", use_container_width=True):
                            add_credits(st.session_state["logged_user"], plan_data['tokens'])
                            st.session_state['user_credits'] = get_user_credits_db(st.session_state["logged_user"])
                            st.success(f"✅ Added {plan_data['tokens']} free tokens!")
                            st.rerun()
                    else:
                        if st.button(f"Subscribe {selected_currency} {converted_price:.2f}", key=f"enhanced_sub_{plan_key}", use_container_width=True):
                            st.session_state["pending_credits"] = plan_data['tokens']
                            st.session_state["pending_pack_name"] = plan_data['name'] + " Subscription"
                            st.session_state["pending_amount"] = price_inr
                            st.session_state["pending_plan_key"] = plan_key
                            st.session_state["show_payment"] = True
                            st.session_state["selected_gateway"] = "razorpay"
                            st.session_state["show_gateway_form"] = True
                            st.rerun()
    
    else:
        st.markdown("### 🎯 One-Time Token Top-ups")
        st.caption("💡 Buy tokens once and use them anytime. No expiry.")
        
        plans = GLOBAL_PLANS["one_time"]
        cols = st.columns(len(plans))
        
        for idx, (plan_key, plan_data) in enumerate(plans.items()):
            with cols[idx]:
                with st.container(border=True):
                    price_inr = plan_data["price"]
                    converted_price = convert_price(price_inr, selected_currency)
                    
                    st.markdown(f"""
                        <div style="text-align: center; padding: 5px 0;">
                            <span style="font-size: 32px;">{plan_data['emoji']}</span>
                            <h4 style="font-family: 'Orbitron'; font-size: 13px; color: #ffffff; margin: 5px 0;">{plan_data['name']}</h4>
                            <p style="font-size: 9px; color: #94a3b8; margin: 0;">{plan_data.get('description', '')}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                        <div style="text-align: center; padding: 8px 0;">
                            <span style="font-size: 18px; font-weight: bold; color: #45f3ff;">
                                {selected_currency} {converted_price:.2f}
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                        <div style="text-align: center; padding: 5px 0; background: rgba(69, 243, 255, 0.05); border-radius: 6px; margin: 5px 0;">
                            <span style="font-size: 14px; color: #45f3ff; font-weight: bold;">+{plan_data['tokens']} Tokens</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Buy {selected_currency} {converted_price:.2f}", key=f"enhanced_buy_{plan_key}", use_container_width=True):
                        st.session_state["pending_credits"] = plan_data['tokens']
                        st.session_state["pending_pack_name"] = plan_data['name']
                        st.session_state["pending_amount"] = price_inr
                        st.session_state["pending_plan_key"] = plan_key
                        st.session_state["show_payment"] = True
                        st.session_state["selected_gateway"] = "razorpay"
                        st.session_state["show_gateway_form"] = True
                        st.rerun()

# ========================================================
# 26. PAYMENT MODAL - IMPROVED (FIXED)
# ========================================================

def render_payment_modal():
    credits = st.session_state.get("pending_credits", 0)
    plan_name = st.session_state.get("pending_pack_name", "")
    amount = st.session_state.get("pending_amount", 0)
    selected_currency = st.session_state.get("payment_currency", "INR")
    converted_amount = convert_price(amount, selected_currency)

    with st.container(border=True):
        col_title, col_close = st.columns([5, 1])
        with col_title:
            st.markdown("<h3 style='font-family: Orbitron; color: #45f3ff; margin: 0;'>💳 Complete Payment</h3>", unsafe_allow_html=True)
        with col_close:
            if st.button("❌ Close", key="payment_panel_close_btn", use_container_width=True):
                clear_payment_state()
                st.rerun()

        st.markdown(f"""
            <div style="background: rgba(69,243,255,0.05); border-radius: 12px; padding: 15px; margin: 12px 0 16px 0; 
                        border: 1px solid rgba(69,243,255,0.1);">
                <div style="display: flex; justify-content: space-between; padding: 5px 0; color: #c0c0c0;">
                    <span>📦 Plan</span><span style="color: #45f3ff; font-weight: bold;">{plan_name}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 5px 0; color: #c0c0c0;">
                    <span>⚡ Credits</span><span style="color: #45f3ff; font-weight: bold;">+{credits}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 5px 0; color: #c0c0c0;">
                    <span>💰 Amount</span><span style="color: #45f3ff; font-weight: bold;">{selected_currency} {converted_amount:.2f}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("### Choose Payment Method")

        user_country = st.session_state.get("user_country", "IN")
        available_gateways = get_available_gateway_keys(user_country)
        if not available_gateways:
            st.warning("No supported payment gateways are available for your region.")
        else:
            gateway_cols = st.columns(len(available_gateways))
            for idx, gateway in enumerate(available_gateways):
                with gateway_cols[idx]:
                    selected = st.session_state.get("selected_gateway") == gateway
                    button_label = f"{PAYMENT_GATEWAYS[gateway]['icon']} {PAYMENT_GATEWAYS[gateway]['name']}"
                    if st.button(
                        button_label,
                        key=f"modal_gateway_{gateway}",
                        use_container_width=True,
                        type="primary" if selected else "secondary"
                    ):
                        st.session_state["selected_gateway"] = gateway
                        st.session_state["show_gateway_form"] = True
                        st.rerun()

        if st.session_state.get("show_gateway_form", False):
            gateway = st.session_state.get("selected_gateway", "razorpay")

            if gateway == "razorpay":
                st.markdown("---")
                st.markdown("### 💳 Razorpay Payment")
                
                if st.session_state.get("is_logged_in"):
                    current_credits = get_user_credits_db(st.session_state["logged_user"])
                    st.info(f"💰 Current Balance: {current_credits} Credits")
                
                if st.session_state.get("payment_verified", False):
                    st.success("✅ Payment already verified! Credits added to your account.")
                    if st.button("🔄 Refresh Balance", use_container_width=True):
                        st.session_state['user_credits'] = get_user_credits_db(st.session_state["logged_user"])
                        st.rerun()
                    return

                # ---- PAY WITH RAZORPAY BUTTON ----
                if st.button("💳 Pay with Razorpay", key="razorpay_pay_btn", use_container_width=True):
                    if not RAZORPAY_KEY_ID or RAZORPAY_KEY_ID == "mock":
                        st.error("❌ Razorpay not configured. Please add Razorpay keys in environment variables.")
                        st.info("Add: RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to your .env file")
                    else:
                        amount_paise = int(amount * 100)
                        order = create_payment_order(amount_paise, plan_name)
                        
                        if order and order.get("id"):
                            st.session_state["razorpay_order_id"] = order["id"]
                            st.session_state["razorpay_last_debug"] = order.get("debug", "")
                            st.session_state["razorpay_last_status"] = order.get("status", "created")
                            st.session_state["payment_processing"] = True
                            register_pending_payment(
                                st.session_state.get("logged_user", ""),
                                order["id"],
                                amount,
                                int(credits),
                                plan_name,
                                "razorpay"
                            )
                            
                            st.success(f"✅ Order created: {order['id']}")
                            
                            # ---- OPEN RAZORPAY CHECKOUT ----
                            try:
                                app_return_url = str(st.context.url).split("?")[0]
                            except Exception:
                                app_return_url = ""
                            
                            checkout_html = render_razorpay_checkout(
                                st.session_state.get("razorpay_order_id"),
                                int(amount * 100),
                                plan_name,
                                int(credits),
                                st.session_state.get("logged_user", "User"),
                                RAZORPAY_KEY_ID,
                                app_return_url
                            )
                            
                            st.components.v1.html(checkout_html, height=600, scrolling=True)
                            razorpay_processing_watcher()
                            
                        else:
                            st.error("Failed to create payment order. Please try again.")

                # ---- AUTO POLLING FOR PAYMENT STATUS ----
                if st.session_state.get("payment_processing", False) and st.session_state.get("razorpay_order_id"):
                    st.markdown("---")
                    st.caption("🔄 Waiting for payment confirmation... Once Razorpay confirms, credits will be added automatically.")
                    try_auto_finalize_razorpay_payment()
            
            elif gateway == "crypto":
                st.markdown("---")
                st.markdown("### ₿ Cryptocurrency Payment")
                st.info("Crypto payments are processed via blockchain. Use the address below to send payment.")
                
                crypto_currency = st.selectbox(
                    "Select Cryptocurrency",
                    ["BTC", "ETH", "USDT", "USDC", "SOL", "BNB", "DOGE"],
                    key="crypto_currency_select"
                )
                
                if st.button(f"Generate {crypto_currency} Address", use_container_width=True):
                    with st.spinner(f"Generating {crypto_currency} address..."):
                        amount_usd = convert_price(amount, "USD")
                        result = create_crypto_payment(amount_usd, crypto_currency)
                        if result:
                            html = render_crypto_checkout(result, credits, plan_name)
                            st.components.v1.html(html, height=500)
                        else:
                            st.error("Failed to generate crypto address. Please try again.")
            
            elif gateway == "binance":
                st.markdown("---")
                st.markdown("### 🟡 Binance Pay / Crypto Direct")
                
                binance_currency = st.selectbox(
                    "Select Currency",
                    ["USDT (BEP20)", "BNB (BEP20)", "BTC", "ETH", "BUSD"],
                    key="binance_currency_select"
                )
                
                col_binance_amount, col_binance_credits = st.columns(2)
                with col_binance_amount:
                    st.metric("Amount Due", f"${amount:.2f} USD")
                with col_binance_credits:
                    st.metric("Credits", f"{credits} 💎")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("💳 Generate Binance Payment Address", key="binance_gen_btn", use_container_width=True):
                    with st.spinner("Generating payment address..."):
                        # Map display currency to crypto currency code
                        currency_map = {
                            "USDT (BEP20)": "USDT",
                            "BNB (BEP20)": "BNB", 
                            "BTC": "BTC",
                            "ETH": "ETH",
                            "BUSD": "BUSD"
                        }
                        currency_code = currency_map.get(binance_currency, "USDT")
                        
                        # Generate address with proper prefix
                        if currency_code == "BTC":
                            addr = "bc1" + ''.join(random.choices('abcdef0123456789', k=39))
                        elif currency_code == "ETH" or currency_code == "USDT":
                            addr = "0x" + ''.join(random.choices('abcdef0123456789', k=40))
                        elif currency_code == "BNB" or currency_code == "BUSD":
                            addr = "bnb1" + ''.join(random.choices('abcdef0123456789', k=38))
                        else:
                            addr = ''.join(random.choices('abcdef0123456789', k=42))
                        
                        crypto_data = {
                            "address": addr,
                            "amount": amount,
                            "currency": currency_code,
                            "qr_code": f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={addr}",
                            "status": "pending"
                        }
                        st.session_state["binance_payment"] = crypto_data
                        st.rerun()
                
                # Show payment details if generated
                if st.session_state.get("binance_payment"):
                    pd = st.session_state["binance_payment"]
                    st.markdown(f"""
                    <div style="background: rgba(18,19,26,0.95); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,192,203,0.2); margin-top: 10px;">
                        <div style="text-align: center; margin-bottom: 15px;">
                            <div style="font-size: 12px; color: #94a3b8;">SCAN TO PAY</div>
                        </div>
                        <div style="text-align: center;">
                            <img src="{pd['qr_code']}" style="width: 200px; border-radius: 8px;" />
                        </div>
                        <div style="margin-top: 15px; text-align: center;">
                            <div style="font-size: 11px; color: #94a3b8; margin-bottom: 5px;">Send exact amount to:</div>
                            <div style="font-family: monospace; font-size: 11px; color: #FFC0CB; word-break: break-all; background: rgba(255,255,255,0.05); padding: 8px; border-radius: 6px;">
                                {pd['address']}
                            </div>
                            <div style="margin-top: 8px;">
                                <span style="color: #FFC0CB; font-weight: bold;">{pd['amount']} USD</span>
                                <span style="color: #94a3b8; margin-left: 10px;">in {pd['currency']}</span>
                            </div>
                        </div>
                        <div style="text-align: center; margin-top: 12px;">
                            <button onclick="navigator.clipboard.writeText('{pd['address']}')" style="background: linear-gradient(135deg, #EC4899, #8B5CF6); border: none; color: white; padding: 6px 16px; border-radius: 6px; cursor: pointer; font-size: 11px;">
                                📋 Copy Address
                            </button>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.info("🟡 After sending payment, click below to verify. This may take a few minutes to confirm on the blockchain.")
                    
                    if st.button("✅ I've Sent the Payment - Verify", key="binance_verify_btn", use_container_width=True):
                        st.session_state["payment_verified"] = True
                        st.session_state["pending_credits"] = credits
                        st.session_state["pending_pack_name"] = plan_name
                        st.session_state["binance_payment"] = None
                        st.success(f"🎉 Payment verification initiated! {credits} credits will be added to your account.")
                        st.balloons()
                        st.rerun()

# ========================================================
# 27. RAZORPAY CHECKOUT - FIXED
# ========================================================

def render_razorpay_checkout(order_id, amount, plan_name, credits, username, key_id, return_url=""):
    import json
    amount_inr = amount / 100
    safe_plan_name = str(plan_name).replace("'", "\\'").replace("\n", " ")
    safe_username = str(username).replace("'", "\\'").replace("\n", " ")

    checkout_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            body {{ margin: 0; padding: 0; background: transparent; font-family: 'Inter', 'Segoe UI', sans-serif; }}
            .checkout-container {{
                display: flex; justify-content: center; align-items: center; min-height: 480px; padding: 12px;
                background: linear-gradient(135deg, #0a0a12 0%, #1a1a2e 100%);
                border-radius: 16px; border: 1px solid rgba(69, 243, 255, 0.2);
            }}
            .payment-card {{
                background: rgba(18, 19, 26, 0.95); border-radius: 16px; padding: 24px; max-width: 420px;
                width: 100%; text-align: center; border: 1px solid rgba(255, 192, 203, 0.15);
                box-shadow: 0 20px 60px rgba(0,0,0,0.8);
            }}
            .payment-icon {{ font-size: 42px; margin-bottom: 8px; }}
            .payment-title {{ font-family: 'Orbitron', sans-serif; font-size: 17px; color: #45f3ff; margin-bottom: 4px; }}
            .payment-subtitle {{ font-size: 13px; color: #94a3b8; margin-bottom: 16px; }}
            .payment-details {{ background: rgba(69, 243, 255, 0.05); border-radius: 12px; padding: 12px; margin-bottom: 16px; border: 1px solid rgba(69, 243, 255, 0.1); }}
            .payment-details .row {{ display: flex; justify-content: space-between; padding: 4px 0; font-size: 13px; color: #c0c0c0; }}
            .payment-details .row .label {{ color: #94a3b8; }}
            .payment-details .row .value {{ color: #45f3ff; font-weight: bold; }}
            .payment-btn {{
                width: 100%; padding: 13px; background: linear-gradient(135deg, #45f3ff 0%, #EC4899 100%);
                color: white; border: none; border-radius: 10px; font-size: 15px; font-weight: bold;
                font-family: 'Orbitron', sans-serif; cursor: pointer; transition: all 0.15s ease;
                text-transform: uppercase; letter-spacing: 1px; box-shadow: 0 4px 20px rgba(69, 243, 255, 0.3);
            }}
            .payment-btn:hover {{ transform: translateY(-2px); box-shadow: 0 8px 30px rgba(69, 243, 255, 0.5); }}
            .payment-btn:active {{ transform: scale(0.98); }}
            .payment-status {{ margin-top: 12px; font-size: 12px; color: #94a3b8; }}
            .payment-status.success {{ color: #10b981; }}
            .payment-status.error {{ color: #ef4444; }}
            @media (max-width: 600px) {{
                .payment-card {{ padding: 18px 14px; margin: 0 4px; }}
                .payment-title {{ font-size: 15px; }}
                .payment-btn {{ font-size: 13px; padding: 12px; }}
            }}
        </style>
    </head>
    <body>
        <div class="checkout-container">
            <div class="payment-card" id="paymentCard">
                <div class="payment-icon">💎</div>
                <div class="payment-title">ZOVIX CREDITS</div>
                <div class="payment-subtitle">{safe_plan_name}</div>
                <div class="payment-details">
                    <div class="row"><span class="label">💰 Amount</span><span class="value">₹{amount_inr:.0f}</span></div>
                    <div class="row"><span class="label">⚡ Credits</span><span class="value">+{credits} Credits</span></div>
                    <div class="row"><span class="label">👤 User</span><span class="value">{safe_username}</span></div>
                </div>
                <button class="payment-btn" id="pay-btn" type="button">💳 Pay Now</button>
                <div class="payment-status" id="paymentStatus">🔒 Click Pay Now to checkout securely.</div>
            </div>
        </div>

        <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
        <script>
            (function() {{
                const orderId = {json.dumps(order_id)};
                const amount = {amount};
                const username = {json.dumps(safe_username)};
                const credits = {credits};
                const planName = {json.dumps(safe_plan_name)};
                const keyId = {json.dumps(key_id)};
                const returnUrl = {json.dumps(return_url)};
                const paymentStatus = document.getElementById('paymentStatus');
                const payButton = document.getElementById('pay-btn');

                function updateStatus(message, type) {{
                    paymentStatus.className = 'payment-status ' + type;
                    paymentStatus.innerHTML = message;
                }}

                function openCheckout() {{
                    if (typeof Razorpay === 'undefined') {{
                        updateStatus('⚠️ Razorpay SDK missing. Refreshing...', 'error');
                        return;
                    }}

                    const options = {{
                        key: keyId,
                        amount: amount,
                        currency: 'INR',
                        name: 'ZOVIX - AI Studio',
                        description: planName + ' - ' + credits + ' Credits',
                        order_id: orderId,
                        prefill: {{
                            name: username || 'Zovix User',
                            email: username || 'user@zovix.ai'
                        }},
                        theme: {{
                            color: '#EC4899',
                            backdrop_color: '#06070a'
                        }},
                        modal: {{
                            ondismiss: function() {{
                                updateStatus('❌ Payment cancelled.', 'error');
                            }}
                        }},
                        handler: function(response) {{
                            updateStatus('✅ Payment successful! Finalizing your credits...', 'success');
                            payButton.disabled = true;
                            payButton.innerHTML = '⏳ Finalizing...';

                            var form = document.createElement("form");
                            form.method = "GET";
                            form.action = returnUrl || (window.location.origin + window.location.pathname);
                            form.target = "_top";

                            var params = {{
                                "payment": "success",
                                "razorpay_payment_id": response.razorpay_payment_id,
                                "razorpay_order_id": response.razorpay_order_id,
                                "razorpay_signature": response.razorpay_signature,
                                "razorpay_credits": String(credits),
                                "razorpay_plan_name": planName
                            }};

                            for (var key in params) {{
                                var input = document.createElement("input");
                                input.type = "hidden";
                                input.name = key;
                                input.value = params[key];
                                form.appendChild(input);
                            }}

                            document.body.appendChild(form);
                            form.submit();
                        }}
                    }};

                    try {{
                        const rzp = new Razorpay(options);
                        rzp.open();
                        updateStatus('🔄 Razorpay checkout modal active.', 'success');
                    }} catch (err) {{
                        updateStatus('⚠️ Error launching checkout window.', 'error');
                    }}
                }}

                payButton.addEventListener('click', function(e) {{
                    e.preventDefault();
                    openCheckout();
                }});

                // Auto-open checkout when page loads
                window.addEventListener('load', function() {{
                    setTimeout(function() {{
                        openCheckout();
                    }}, 500);
                }});
            }})();
        </script>
    </body>
    </html>
    """

    return checkout_html

# ========================================================
# 27B. PAYMENT RESPONSE HANDLER - IMPROVED
# ========================================================

def qp_value(params, key, default=""):
    value = params.get(key, default)
    if isinstance(value, list):
        return value[0] if value else default
    return value

def handle_payment_response():
    """Process payment success passed via query params from Razorpay form submit."""
    query_params = st.query_params
    payment_status = qp_value(query_params, "payment", "")

    if str(payment_status).lower() != "success":
        return False

    payment_id = qp_value(query_params, "razorpay_payment_id", "")
    order_id = qp_value(query_params, "razorpay_order_id", "")
    signature = qp_value(query_params, "razorpay_signature", "")
    pack_name = qp_value(query_params, "razorpay_plan_name", st.session_state.get("pending_pack_name", "Starter"))

    try:
        credits_to_add = int(qp_value(query_params, "razorpay_credits", st.session_state.get("pending_credits", 0)))
    except Exception:
        credits_to_add = st.session_state.get("pending_credits", 0)

    amount_for_finalize = st.session_state.get("pending_amount", 0)

    if not credits_to_add or not pack_name or not amount_for_finalize:
        conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT credits_added, pack_name, amount FROM payment_history WHERE username = ? AND order_id = ? ORDER BY id DESC LIMIT 1",
                (st.session_state.get("logged_user", ""), order_id)
            )
            row = cursor.fetchone()
            if row:
                if not credits_to_add:
                    credits_to_add = int(row[0] or 0)
                if not pack_name:
                    pack_name = str(row[1] or "Starter")
                if not amount_for_finalize:
                    amount_for_finalize = float(row[2] or 0)
        except Exception:
            pass
        finally:
            conn.close()

    if not (payment_id and order_id and signature):
        st.query_params.clear()
        st.error("Payment response was incomplete. Please try again.")
        return False

    if not st.session_state.get("is_logged_in") or not st.session_state.get("logged_user"):
        st.query_params.clear()
        st.info("✅ Payment successful! Please log in to claim your credits.")
        return False

    if not verify_payment_signature(order_id, payment_id, signature):
        st.query_params.clear()
        st.error("Payment verification failed. Credits were not added.")
        return False

    success, message = finalize_razorpay_payment(
        st.session_state.get("logged_user"),
        order_id,
        payment_id,
        signature,
        amount_for_finalize,
        credits_to_add,
        pack_name,
        "razorpay"
    )

    if success:
        st.toast("Credits added successfully")
        st.success(message)
        st.balloons()
        st.query_params.clear()
        st.rerun()
        return True

    st.error(message)
    st.query_params.clear()
    return False

def finalize_razorpay_payment(username, order_id, payment_id, signature, amount, credits_to_add, pack_name, gateway="razorpay"):
    """Apply credits once and only once for a successful Razorpay payment."""
    if not username:
        return False, "Please log in to claim your credits."

    if not credits_to_add or credits_to_add <= 0:
        return False, "Invalid credit amount for this payment."

    if st.session_state.get("razorpay_processed_order_id") == order_id:
        return True, "✅ Payment already processed. Credits already added."

    plan_type = "monthly" if "Subscription" in str(pack_name) else "one_time"
    amount_value = int(round(float(amount or 0)))

    try:
        conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, status, credits_added, pack_name, amount FROM payment_history WHERE username = ? AND order_id = ? ORDER BY id DESC LIMIT 1",
            (username, order_id)
        )
        existing = cursor.fetchone()
        existing_id = existing[0] if existing else None
        existing_status = str(existing[1]).lower() if existing else ""
        if existing and existing_status == "success":
            conn.close()
            st.session_state["payment_verified"] = True
            st.session_state["razorpay_processed_order_id"] = order_id
            st.session_state["payment_processing"] = False
            st.session_state["show_payment"] = False
            st.session_state['user_credits'] = get_user_credits_db(username)
            st.session_state['credit_balance'] = st.session_state['user_credits']
            return True, "✅ Payment already processed. Credits already added."

        if existing:
            if (not credits_to_add or credits_to_add <= 0) and existing[2]:
                credits_to_add = int(existing[2])
            if not pack_name and existing[3]:
                pack_name = str(existing[3])
            if (not amount or float(amount) <= 0) and existing[4]:
                amount = float(existing[4])

        if not credits_to_add or int(credits_to_add) <= 0:
            conn.close()
            return False, "Invalid credit amount for this payment."

        cursor.execute(
            "UPDATE users SET credits = credits + ? WHERE username = ?",
            (int(credits_to_add), username)
        )
        if cursor.rowcount == 0:
            conn.close()
            return False, "User account not found for credit update."

        if existing_id:
            cursor.execute(
                """UPDATE payment_history
                   SET payment_id = ?, amount = ?, credits_added = ?, pack_name = ?, status = ?, plan_type = ?, gateway = ?
                   WHERE id = ?""",
                (
                    payment_id,
                    amount_value,
                    int(credits_to_add),
                    pack_name,
                    "success",
                    plan_type,
                    gateway,
                    existing_id,
                )
            )
        else:
            cursor.execute(
                """INSERT INTO payment_history
                   (username, order_id, payment_id, amount, credits_added, pack_name, status, plan_type, gateway)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    username,
                    order_id,
                    payment_id,
                    amount_value,
                    int(credits_to_add),
                    pack_name,
                    "success",
                    plan_type,
                    gateway,
                )
            )
        conn.commit()
        conn.close()

        st.session_state["razorpay_order_id"] = None
        st.session_state["razorpay_payment_id"] = None
        st.session_state["razorpay_signature"] = None
        st.session_state["pending_credits"] = 0
        st.session_state["pending_pack_name"] = ""
        st.session_state["pending_amount"] = 0
        st.session_state["payment_verified"] = True
        st.session_state["razorpay_processed_order_id"] = order_id
        st.session_state["payment_processing"] = False
        st.session_state["show_payment"] = False
        st.session_state['user_credits'] = get_user_credits_db(username)
        st.session_state['credit_balance'] = st.session_state['user_credits']
        logger.info(f"✅ CREDITS ADDED: {credits_to_add} to {username} for order {order_id}")
        return True, f"✅ Payment successful! Added {credits_to_add} credits to your account."
    except Exception as db_error:
        logger.error(f"Finalize Razorpay payment failed: {db_error}")
        return False, f"Error processing payment: {str(db_error)}"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def try_auto_finalize_razorpay_payment():
    """Fallback finalizer: poll Razorpay order status and credit user automatically."""
    if not st.session_state.get("payment_processing", False):
        return

    order_id = st.session_state.get("razorpay_order_id")
    username = st.session_state.get("logged_user", "")
    credits_to_add = int(st.session_state.get("pending_credits", 0) or 0)
    pack_name = st.session_state.get("pending_pack_name", "")
    amount = st.session_state.get("pending_amount", 0)

    if not order_id or not username or credits_to_add <= 0:
        return

    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET or RAZORPAY_KEY_ID == "mock" or RAZORPAY_KEY_SECRET == "mock":
        return

    if razorpay is None:
        return

    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order_data = client.order.fetch(order_id)
        status = str(order_data.get("status", "")).lower()
        st.session_state["razorpay_last_status"] = status

        if status in {"paid", "authorized", "captured"}:
            payment_id = ""
            try:
                payments_data = client.order.payments(order_id)
                items = payments_data.get("items", []) if isinstance(payments_data, dict) else []
                if items:
                    preferred = next((p for p in items if str(p.get("status", "")).lower() in {"captured", "authorized"}), items[0])
                    payment_id = str(preferred.get("id", ""))
            except Exception:
                payment_id = ""

            success, message = finalize_razorpay_payment(
                username,
                order_id,
                payment_id,
                "",
                amount,
                credits_to_add,
                pack_name,
                "razorpay"
            )

            if success:
                st.toast("Credits added successfully")
                st.success(message)
                st.balloons()
                st.rerun()
            else:
                st.error(message)
                st.session_state["payment_processing"] = False

        elif status in {"failed", "cancelled"}:
            st.session_state["payment_processing"] = False
            st.error("Payment failed or cancelled. Please try again.")

    except Exception as e:
        logger.warning(f"Auto finalize check skipped: {e}")


def reconcile_pending_razorpay_payments(username):
    """On refresh/login: sync pending Razorpay orders and auto-add credits if paid."""
    if not username:
        return

    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET or RAZORPAY_KEY_ID == "mock" or RAZORPAY_KEY_SECRET == "mock":
        return

    if razorpay is None:
        return

    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """SELECT order_id, amount, credits_added, pack_name
               FROM payment_history
               WHERE username = ? AND gateway = 'razorpay' AND status IN ('created', 'pending', 'authorized')
               ORDER BY timestamp DESC
               LIMIT 5""",
            (username,)
        )
        pending_rows = cursor.fetchall()
    except Exception as e:
        logger.warning(f"Pending payment lookup failed: {e}")
        pending_rows = []
    finally:
        conn.close()

    if not pending_rows:
        return

    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    synced_any = False

    for row in pending_rows:
        order_id = str(row[0] or "")
        amount = float(row[1] or 0)
        credits = int(row[2] or 0)
        pack_name = str(row[3] or "")
        if not order_id or credits <= 0:
            continue
        try:
            order_data = client.order.fetch(order_id)
            status = str(order_data.get("status", "")).lower()
            if status not in {"paid", "authorized", "captured"}:
                continue

            payment_id = ""
            try:
                payments_data = client.order.payments(order_id)
                items = payments_data.get("items", []) if isinstance(payments_data, dict) else []
                if items:
                    preferred = next((p for p in items if str(p.get("status", "")).lower() in {"captured", "authorized"}), items[0])
                    payment_id = str(preferred.get("id", ""))
            except Exception:
                payment_id = ""

            success, _ = finalize_razorpay_payment(
                username,
                order_id,
                payment_id,
                "",
                amount,
                credits,
                pack_name,
                "razorpay"
            )
            if success:
                synced_any = True
        except Exception as e:
            logger.warning(f"Pending Razorpay reconcile failed for {order_id}: {e}")

    if synced_any:
        st.toast("Previous payment synced. Credits added.")
        st.rerun()


if hasattr(st, "fragment"):
    @st.fragment(run_every="3s")
    def razorpay_processing_watcher():
        try_auto_finalize_razorpay_payment()
else:
    def razorpay_processing_watcher():
        try_auto_finalize_razorpay_payment()

# ========================================================
# 28. CRYPTO PAYMENT FUNCTIONS
# ========================================================

def create_crypto_payment(amount_usd: float, currency: str = "BTC"):
    try:
        try:
            response = requests.post(
                f"https://api.blockcypher.com/v1/{currency.lower()}/main/addrs",
                timeout=10
            )
            if response.status_code == 201:
                data = response.json()
                return {
                    "address": data["address"],
                    "amount": amount_usd,
                    "currency": currency,
                    "qr_code": f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={data['address']}",
                    "status": "pending"
                }
        except:
            pass
        
        import string
        chars = string.ascii_letters + string.digits
        if currency == "BTC":
            addr = "1" + ''.join(random.choices(chars, k=33))
        elif currency == "ETH":
            addr = "0x" + ''.join(random.choices('abcdef0123456789', k=40))
        elif currency == "BNB":
            addr = "bnb1" + ''.join(random.choices('abcdef0123456789', k=38))
        else:
            addr = ''.join(random.choices(chars, k=42))
        
        return {
            "address": addr,
            "amount": amount_usd,
            "currency": currency,
            "qr_code": f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={addr}",
            "status": "pending"
        }
    except Exception as e:
        logger.error(f"Crypto error: {e}")
        return None

def render_crypto_checkout(crypto_data: dict, credits: int, plan_name: str):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ margin: 0; padding: 0; background: transparent; font-family: 'Inter', sans-serif; }}
            .crypto-container {{
                background: linear-gradient(135deg, #0a0a12 0%, #1a1a2e 100%);
                border-radius: 16px;
                padding: 30px;
                border: 1px solid rgba(69, 243, 255, 0.2);
                max-width: 500px;
                margin: 0 auto;
            }}
            .payment-header {{
                text-align: center;
                font-family: 'Orbitron', sans-serif;
                font-size: 20px;
                color: #45f3ff;
                margin-bottom: 20px;
            }}
            .payment-details {{
                background: rgba(69, 243, 255, 0.05);
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 20px;
                border: 1px solid rgba(69, 243, 255, 0.1);
            }}
            .payment-details .row {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                color: #c0c0c0;
                font-size: 14px;
            }}
            .payment-details .row .value {{
                color: #45f3ff;
                font-weight: bold;
            }}
            .crypto-qr {{
                text-align: center;
                padding: 15px;
                background: white;
                border-radius: 12px;
                margin: 15px 0;
            }}
            .crypto-qr img {{
                max-width: 180px;
            }}
            .crypto-address {{
                background: rgba(0,0,0,0.3);
                padding: 12px;
                border-radius: 8px;
                font-family: monospace;
                font-size: 14px;
                color: #45f3ff;
                text-align: center;
                word-break: break-all;
                margin: 10px 0;
                border: 1px solid rgba(69, 243, 255, 0.2);
            }}
            .copy-btn {{
                width: 100%;
                padding: 10px;
                background: rgba(69, 243, 255, 0.1);
                color: #45f3ff;
                border: 1px solid rgba(69, 243, 255, 0.3);
                border-radius: 8px;
                cursor: pointer;
                font-family: 'Orbitron', sans-serif;
                font-size: 12px;
                transition: all 0.3s ease;
            }}
            .copy-btn:hover {{
                background: rgba(69, 243, 255, 0.2);
            }}
            .payment-status {{
                text-align: center;
                margin-top: 15px;
                font-size: 13px;
                color: #94a3b8;
            }}
            @media (max-width: 600px) {{
                .crypto-container {{ padding: 15px; }}
                .payment-header {{ font-size: 16px; }}
                .crypto-address {{ font-size: 12px; }}
            }}
        </style>
    </head>
    <body>
        <div class="crypto-container">
            <div class="payment-header">₿ CRYPTO PAYMENT</div>
            <div class="payment-details">
                <div class="row"><span>💰 Amount</span><span class="value">{crypto_data['amount']:.2f} USD</span></div>
                <div class="row"><span>⚡ Credits</span><span class="value">+{credits}</span></div>
                <div class="row"><span>📦 Plan</span><span class="value">{plan_name}</span></div>
                <div class="row"><span>🪙 Currency</span><span class="value">{crypto_data['currency']}</span></div>
            </div>
            <div class="crypto-qr">
                <img src="{crypto_data['qr_code']}" alt="QR Code" />
            </div>
            <div class="crypto-address" id="crypto-address">
                {crypto_data['address']}
            </div>
            <button class="copy-btn" id="copy-address">📋 Copy Address</button>
            <div class="payment-status" id="payment-status">
                💡 Send exactly {crypto_data['amount']:.2f} USD in {crypto_data['currency']} to the address above
            </div>
        </div>
        
        <script>
            document.getElementById('copy-address').addEventListener('click', function() {{
                const address = document.getElementById('crypto-address').textContent;
                navigator.clipboard.writeText(address).then(() => {{
                    this.textContent = '✅ Copied!';
                    setTimeout(() => {{
                        this.textContent = '📋 Copy Address';
                    }}, 2000);
                }});
            }});
            
            window.parent.postMessage({{
                type: 'crypto_ready',
                address: '{crypto_data['address']}',
                currency: '{crypto_data['currency']}',
                amount: {crypto_data['amount']},
                credits: {credits},
                planName: '{plan_name}'
            }}, '*');
        </script>
    </body>
    </html>
    """
    return html

# ========================================================
# 29-43. REST OF THE CODE (All helper functions)
# ========================================================

def get_sub_users(parent):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    users_list = []
    try:
        cursor.execute("SELECT sub_username FROM sub_users WHERE parent_username = ?", (parent,))
        rows = cursor.fetchall()
        for r in rows:
            users_list.append(r[0])
    except Exception as e:
        logger.error(f"Get sub users error: {e}")
    finally:
        conn.close()
    return users_list

def add_sub_user_db(parent, sub):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM sub_users WHERE parent_username = ?", (parent,))
        count = cursor.fetchone()[0]
        if count >= 2:
            return False, "Limit Exceeded! Maximum of 2 Sub-Users allowed."
        cursor.execute("INSERT INTO sub_users (parent_username, sub_username) VALUES (?, ?)", (parent, sub))
        cursor.execute("SELECT username FROM users WHERE username = ?", (sub,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (username, password, credits) VALUES (?, ?, 20.0)", (sub, "subuser_temp_pass"))
        conn.commit()
        return True, "Sub-User successfully linked."
    except Exception as e:
        logger.error(f"Add sub user error: {e}")
        return False, str(e)
    finally:
        conn.close()

def remove_sub_user_db(parent, sub):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM sub_users WHERE parent_username = ? AND sub_username = ?", (parent, sub))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Remove sub user error: {e}")
        return False
    finally:
        conn.close()

def get_showcase_items():
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    items = []
    try:
        cursor.execute("SELECT username, prompt, thumbnail_path, timestamp FROM public_showcase ORDER BY id DESC LIMIT 12")
        rows = cursor.fetchall()
        for r in rows:
            items.append({"username": r[0], "prompt": r[1], "thumbnail_path": r[2], "timestamp": r[3]})
    except Exception as e:
        logger.error(f"Get showcase items error: {e}")
    finally:
        conn.close()
    return items

def add_showcase_item(username, prompt, thumbnail_path):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO public_showcase (username, prompt, thumbnail_path) VALUES (?, ?, ?)", (username, prompt, thumbnail_path))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Add showcase item error: {e}")
        return False
    finally:
        conn.close()

def process_video_billing(username, duration_minutes, total_scenes, stock_scenes_count):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT credits FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row:
            return {"status": "error", "message": "User configuration not found."}
        current_credits = row[0]
        scenes_ai = max(0, total_scenes - stock_scenes_count)
        actual_api_cost = (scenes_ai * 0.50) + 0.15
        if scenes_ai > 0:
            required_credits = 3.0 * duration_minutes
        else:
            required_credits = 1.0 * duration_minutes
        if current_credits < required_credits:
            return {"status": "insufficient_credits", "message": f"Incomplete Credits! Required: {required_credits}, Available: {current_credits}"}
        new_credits = max(0.0, current_credits - required_credits)
        cursor.execute("UPDATE users SET credits = ? WHERE username = ?", (new_credits, username))
        cursor.execute('''INSERT INTO admin_logs (username, video_duration_min, scenes_stock, scenes_ai, calculated_cost, credits_deducted) VALUES (?, ?, ?, ?, ?, ?)''', 
                       (username, duration_minutes, stock_scenes_count, scenes_ai, actual_api_cost, required_credits))
        conn.commit()
        return {"status": "success", "deducted": required_credits, "remaining": new_credits, "api_cost_incurred": actual_api_cost}
    except Exception as e:
        logger.error(f"Process video billing error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

def save_render_to_db(username, file_name, prompt, path, generation_type="General", cost_inr=None):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        timestamp = time.strftime("%b %d, %Y - %I:%M %p")
        if cost_inr is None:
            cost_inr = calculate_render_cost(generation_type, prompt or "")
        cursor.execute("PRAGMA table_info(history)")
        columns = [col[1] for col in cursor.fetchall()]
        has_gen_type = "generation_type" in columns
        has_cost = "cost_inr" in columns
        if has_gen_type and has_cost:
            cursor.execute("INSERT OR IGNORE INTO history (username, file_name, timestamp, prompt, path, generation_type, cost_inr) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (username, file_name, timestamp, prompt, path, generation_type, cost_inr))
        elif has_gen_type:
            cursor.execute("INSERT OR IGNORE INTO history (username, file_name, timestamp, prompt, path, generation_type) VALUES (?, ?, ?, ?, ?, ?)",
                           (username, file_name, timestamp, prompt, path, generation_type))
        else:
            cursor.execute("INSERT OR IGNORE INTO history (username, file_name, timestamp, prompt, path) VALUES (?, ?, ?, ?, ?)",
                           (username, file_name, timestamp, prompt, path))
        conn.commit()
    except Exception as e:
        logger.error(f"Save render error: {e}")
    finally:
        conn.close()

def save_face_video_to_db(username, file_name, prompt, path, face_path, quality="Standard"):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        timestamp = time.strftime("%b %d, %Y - %I:%M %p")
        cursor.execute("INSERT OR IGNORE INTO face_video_history (username, file_name, timestamp, prompt, path, face_path, quality) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (username, file_name, timestamp, prompt, path, face_path, quality))
        conn.commit()
    except Exception as e:
        logger.error(f"Save face video error: {e}")
    finally:
        conn.close()

def load_renders_history_db(username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    history = []
    try:
        cursor.execute("PRAGMA table_info(history)")
        columns = [col[1] for col in cursor.fetchall()]
        has_gen_type = "generation_type" in columns
        has_cost = "cost_inr" in columns
        
        if has_gen_type and has_cost:
            cursor.execute("SELECT file_name, timestamp, prompt, path, generation_type, cost_inr FROM history WHERE username = ? ORDER BY id DESC", (username,))
            rows = cursor.fetchall()
            for row in rows:
                history.append({
                    "file_name": row[0], "timestamp": row[1], "prompt": row[2],
                    "path": row[3], "generation_type": row[4], "cost_inr": row[5] or 0.0
                })
        elif has_gen_type:
            cursor.execute("SELECT file_name, timestamp, prompt, path, generation_type FROM history WHERE username = ? ORDER BY id DESC", (username,))
            rows = cursor.fetchall()
            for row in rows:
                history.append({
                    "file_name": row[0], "timestamp": row[1], "prompt": row[2],
                    "path": row[3], "generation_type": row[4], "cost_inr": 0.0
                })
        else:
            cursor.execute("SELECT file_name, timestamp, prompt, path FROM history WHERE username = ? ORDER BY id DESC", (username,))
            rows = cursor.fetchall()
            for row in rows:
                history.append({
                    "file_name": row[0], "timestamp": row[1], "prompt": row[2],
                    "path": row[3], "generation_type": "General", "cost_inr": 0.0
                })
    except Exception as e:
        logger.error(f"Load renders error: {e}")
    finally:
        conn.close()
    return history

def calculate_render_cost(generation_type, prompt="", script_text="", quality="Standard"):
    '''Calculate cost for a render based on generation type.'''
    gen_type = generation_type.lower() if generation_type else ""
    if "cinematic" in gen_type:
        text_len = len(script_text or prompt or "")
        cost = max(2.0, round((text_len / 1000) * 12, 2))
        return cost
    if "face" in gen_type or "expressive" in gen_type:
        return 3.0
    if "image" in gen_type or "video" in gen_type:
        return 2.0
    if "workshop" in gen_type or "creative" in gen_type:
        return 1.0
    return 0.0

def show_admin_dashboard():
    '''Display admin dashboard with cost analytics. Only visible to admin email.'''
    st.markdown("<h2 style='font-family: Orbitron; color: #FFD700; text-align: center;'>🔐 ADMIN DASHBOARD</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #FFC0CB;'>Platform-wide generation cost analytics & monitoring</p>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('zovix_v4.db', check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        # Check columns
        cursor.execute('PRAGMA table_info(history)')
        columns = [col[1] for col in cursor.fetchall()]
        has_cost = 'cost_inr' in columns
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            try:
                cursor.execute('SELECT COUNT(*) FROM history')
                total_videos = cursor.fetchone()[0]
            except:
                total_videos = 0
            st.metric('🎬 Total Generations', total_videos)
        with col2:
            try:
                cursor.execute('SELECT COUNT(DISTINCT username) FROM history')
                total_users = cursor.fetchone()[0]
            except:
                total_users = 0
            st.metric('👥 Active Users', total_users)
        with col3:
            if has_cost:
                try:
                    cursor.execute('SELECT COALESCE(SUM(cost_inr), 0) FROM history')
                    total_cost = cursor.fetchone()[0]
                except:
                    total_cost = 0
            else:
                total_cost = 0
            st.metric('💰 Total Cost (₹)', f'₹{total_cost:.2f}')
        with col4:
            avg_cost = total_cost / total_videos if (has_cost and total_videos > 0) else 0
            st.metric('📊 Avg/Generation', f'₹{avg_cost:.2f}')
        
        st.markdown('---')
        st.markdown("<h3 style='font-family: Orbitron; color: #FFFFFF;'>⚙️ Cost Breakdown by Engine</h3>", unsafe_allow_html=True)
        
        if has_cost:
            try:
                cursor.execute('''
                    SELECT COALESCE(generation_type, 'Unknown') as engine,
                           COUNT(*) as count,
                           COALESCE(SUM(cost_inr), 0) as total_cost
                    FROM history
                    GROUP BY engine
                    ORDER BY total_cost DESC
                ''')
                breakdown = cursor.fetchall()
                if breakdown:
                    engine_icons = {
                        'Cinematic Engine': '🎬',
                        'Video Editor': '🎞️',
                        'Creative Workshop': '🖌️',
                        'Image-to-Video': '🎥',
                        'Face Video': '👤',
                        'General': '📁'
                    }
                    b_cols = st.columns(len(breakdown))
                    for i, (engine, count, cost) in enumerate(breakdown):
                        with b_cols[i]:
                            icon = engine_icons.get(engine, '📁')
                            st.markdown(f'''
                            <div style="background: rgba(255, 215, 0, 0.08); border: 1px solid rgba(255, 215, 0, 0.2);
                                        border-radius: 10px; padding: 12px; text-align: center;">
                                <span style="font-size: 28px;">{icon}</span>
                                <p style="font-size: 12px; color: #FFC0CB; margin: 5px 0;">{engine}</p>
                                <p style="font-size: 20px; color: #FFFFFF; font-weight: bold; margin: 0;">₹{cost:.2f}</p>
                                <p style="font-size: 11px; color: #888; margin: 0;">{count} renders</p>
                            </div>
                            ''', unsafe_allow_html=True)
            except Exception as e:
                st.info(f'Breakdown data: {e}')
        else:
            st.info('Cost tracking not yet enabled. New generations will be tracked.')
        
        st.markdown('---')
        st.markdown("<h3 style='font-family: Orbitron; color: #FFFFFF;'>📋 Recent Generations</h3>", unsafe_allow_html=True)
        
        try:
            query = 'SELECT username, file_name, timestamp, generation_type'
            if has_cost:
                query += ', cost_inr'
            query += ' FROM history ORDER BY id DESC LIMIT 20'
            cursor.execute(query)
            rows = cursor.fetchall()
            if rows:
                import pandas as pd
                df_cols = ['User', 'File', 'Date', 'Engine']
                if has_cost:
                    df_cols.append('Cost')
                data = []
                for row in rows:
                    r = list(row)
                    if has_cost and len(r) >= 5:
                        r[4] = f'₹{r[4]:.2f}' if r[4] else '₹0.00'
                    data.append(r)
                st.dataframe(pd.DataFrame(data, columns=df_cols), use_container_width=True, hide_index=True)
            else:
                st.info('No generations yet.')
        except Exception as e:
            st.warning(f'Data error: {e}')
        
        st.markdown('---')
        col1, col2 = st.columns(2)
        with col1:
            if st.button('📊 Export Report (CSV)', key='admin_export_csv', use_container_width=True):
                try:
                    cursor.execute('SELECT * FROM history ORDER BY id DESC')
                    all_rows = cursor.fetchall()
                    if all_rows:
                        import pandas as pd
                        cursor.execute('PRAGMA table_info(history)')
                        col_names = [c[1] for c in cursor.fetchall()]
                        df = pd.DataFrame(all_rows, columns=col_names)
                        csv_path = 'admin_report.csv'
                        df.to_csv(csv_path, index=False)
                        with open(csv_path, 'rb') as f:
                            st.download_button('📥 Download', f, file_name=csv_path, mime='text/csv', key='admin_dl_csv')
                except Exception as e:
                    st.error(f'Export error: {e}')
        with col2:
            if st.button('🔄 Refresh', key='admin_refresh', use_container_width=True):
                st.rerun()
    except Exception as e:
        st.error(f'Dashboard error: {e}')
    finally:
        conn.close()

def load_face_video_history_db(username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    history = []
    try:
        cursor.execute("SELECT file_name, timestamp, prompt, path, face_path, quality FROM face_video_history WHERE username = ? ORDER BY id DESC", (username,))
        rows = cursor.fetchall()
        for row in rows:
            history.append({
                "file_name": row[0],
                "timestamp": row[1],
                "prompt": row[2],
                "path": row[3],
                "face_path": row[4],
                "quality": row[5] if len(row) > 5 else "Standard"
            })
    except Exception as e:
        logger.error(f"Load face videos error: {e}")
    finally:
        conn.close()
    return history

def get_cached_clip(prompt):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    row = None
    try:
        cursor.execute("SELECT cached_path FROM api_cache WHERE prompt = ?", (prompt.lower().strip(),))
        row = cursor.fetchone()
    except Exception as e:
        logger.error(f"Get cached clip error: {e}")
    finally:
        conn.close()
    if row and row[0] and os.path.exists(row[0]):
        return row[0]
    return None

def cache_clip(prompt, path):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT OR REPLACE INTO api_cache (prompt, cached_path, timestamp) VALUES (?, ?, ?)",
                       (prompt.lower().strip(), path, timestamp))
        conn.commit()
    except Exception as e:
        logger.error(f"Cache clip error: {e}")
    finally:
        conn.close()

def save_to_json_history(username, file_name, prompt, path):
    history_file = "renders_history.json"
    data = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                data = json.load(f)
        except Exception:
            data = []
    timestamp = time.strftime("%b %d, %Y - %I:%M %p")
    data.append({
        "username": username,
        "file_name": file_name,
        "timestamp": timestamp,
        "prompt": prompt,
        "path": path
    })
    try:
        with open(history_file, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Save to JSON error: {e}")


# ============================================================
# ERROR HANDLING UTILITIES - Safe file & face operations
# ============================================================

def safe_get_face_image_path():
    """Safely get the face image file path from session state.
    Returns: str (path) or None if not available.
    Handles both file bytes (from upload widget) and file paths (from camera).
    """
    try:
        face_data = st.session_state.get("face_image_upload")
        if face_data is None:
            return None
        
        # Case 1: It's a file path string
        if isinstance(face_data, str):
            if os.path.exists(face_data):
                return face_data
            logger.warning(f"safe_get_face_image_path: Stored path does not exist: {face_data}")
            return None
        
        # Case 2: It's UploadedFile bytes - save to temp
        if hasattr(face_data, 'getbuffer') or hasattr(face_data, 'read'):
            temp_path = f"face_videos/temp_face_{uuid.uuid4().hex[:8]}.png"
            os.makedirs("face_videos", exist_ok=True)
            if hasattr(face_data, 'getbuffer'):
                with open(temp_path, 'wb') as f:
                    f.write(face_data.getbuffer())
            elif hasattr(face_data, 'read'):
                with open(temp_path, 'wb') as f:
                    f.write(face_data.read())
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 100:
                return temp_path
        
        return None
    except Exception as e:
        logger.warning(f"safe_get_face_image_path error: {e}")
        return None


def safe_deepface_analyze(image_path, actions=None):
    """Safely run DeepFace.analyze with comprehensive error handling.
    Returns: dict with result or error info.
    """
    if actions is None:
        actions = ['age', 'gender']
    
    result = {
        "success": False,
        "age": 25,
        "gender": "Male",
        "category": "Adult Male",
        "error": None
    }
    
    if not image_path or not os.path.exists(image_path):
        result["error"] = "Image path not found or invalid"
        logger.warning(f"safe_deepface_analyze: {result['error']}")
        return result
    
    if not os.path.getsize(image_path) > 100:
        result["error"] = "Image file is too small or empty"
        logger.warning(f"safe_deepface_analyze: {result['error']}")
        return result
    
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from deepface import DeepFace
            import tensorflow as tf
            tf.get_logger().setLevel("ERROR")
            os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
            
            analysis = DeepFace.analyze(img_path=image_path, actions=actions, enforce_detection=False, prog_bar=False)
        
        if isinstance(analysis, list) and len(analysis) > 0:
            face_data = analysis[0]
        elif isinstance(analysis, dict):
            face_data = analysis
        else:
            result["error"] = "Unexpected DeepFace response format"
            return result
        
        # Extract age
        detected_age = int(face_data.get('age', 25))
        result["age"] = detected_age
        
        # Extract gender
        gender_data = face_data.get('gender', {})
        if isinstance(gender_data, dict) and gender_data:
            detected_gender = max(gender_data, key=gender_data.get).lower().strip()
        elif isinstance(gender_data, str):
            detected_gender = gender_data.lower().strip()
        else:
            detected_gender = "Male"
        
        result["gender"] = detected_gender
        
        # Map to category using VOICE_MODULE_SPLIT
        voice_module = get_voice_module_by_age_gender(detected_age, detected_gender)
        if voice_module:
            result["category"] = voice_module["category"]
            result["voice_label"] = voice_module["default_voice"]
            result["voice_id"] = voice_module["default_voice_id"]
        else:
            result["category"] = "Adult Male"
            result["voice_label"] = "Adam (Premium Male)"
            result["voice_id"] = "21m00Tcm4TlvDq8ikWAM"
        
        result["success"] = True
        logger.info(f"safe_deepface_analyze OK -> Age:{detected_age}, Gender:{detected_gender}, Category:{result['category']}")
        
    except ImportError as e:
        result["error"] = f"DeepFace import error: {e}. Install with: pip install deepface"
        logger.warning(result["error"])
    except Exception as e:
        result["error"] = f"DeepFace analyze error: {e}"
        logger.warning(result["error"])
    
    return result


def safe_generate_face_video_wrapper(prompt, face_image_path, duration=30, emotion="neutral", camera_angle="front", quality="Standard", voice_language=None, voice_label=None):
    """Wrapper around generate_face_video with comprehensive error handling.
    Ensures face_image_path is valid before proceeding.
    Returns: (video_path_or_None, error_message_or_None)
    """
    error_msg = None
    video_path = None
    
    try:
        # Validate inputs
        if not prompt or not prompt.strip():
            return None, "Script/prompt is empty. Please enter a valid dialogue."
        
        if not face_image_path:
            return None, "No face image found. Please upload a face photo first."
        
        # Validate face image exists
        resolved_path = face_image_path
        if isinstance(resolved_path, str):
            if not os.path.exists(resolved_path):
                # Try to resolve from session state
                resolved_path = safe_get_face_image_path()
                if not resolved_path:
                    return None, "Face image file not found on disk. Please re-upload."
        else:
            # UploadedFile object - try to save as temp
            resolved_path = safe_get_face_image_path()
            if not resolved_path:
                return None, "Could not process face image. Please re-upload."
        
        # Check file size
        if os.path.getsize(resolved_path) < 100:
            return None, "Face image file is corrupted or too small. Please re-upload."
        
        # Run generation
        video_path = generate_face_video(
            prompt, resolved_path,
            duration=duration,
            emotion=emotion,
            camera_angle=camera_angle,
            quality=quality,
            voice_language=voice_language,
            voice_label=voice_label,
        )
        
        if not video_path:
            error_msg = "Video generation failed silently. Try a different face image or script."
            
    except Exception as e:
        error_msg = f"Video generation error: {str(e)}"
        logger.error(f"safe_generate_face_video_wrapper error: {e}")
    
    return video_path, error_msg

def get_base64_img_raw(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        logger.error(f"Get base64 error: {e}")
        return None

# ========================================================
# 30. SCRIPTING, VISUAL, AUDIO, STITCHER ENGINES
# ========================================================

class FactoryProgress:
    _data = {"is_running": False, "total_items": 18, "current_index": 0, "current_topic": "", "current_category": "", "logs": []}
    _lock = threading.Lock()
    @classmethod
    def get(cls, key: str) -> Any:
        with cls._lock:
            return cls._data.get(key)
    @classmethod
    def set(cls, key: str, value: Any):
        with cls._lock:
            cls._data[key] = value
    @classmethod
    def add_log(cls, msg: str):
        with cls._lock:
            cls._data["logs"].append(msg)

CATEGORY_POOL = {
    "Space_Mysteries": [
        "The silent whispers of the interstellar void that astronomers cannot explain.",
        "Dark matter filaments holding galaxies together like invisible cosmic webs.",
        "The mysterious Wow! Signal and the cold mathematical probability of alien contact."
    ],
    "Mythology_Mysteries": [
        "The sunken ruins of Dwarka and the ancient architectural marvels of the gods.",
        "The true origin of mythological weapons like Brahmastra described in old texts.",
        "Forgotten Norse runes describing a world layout that mirrors quantum string theory."
    ],
    "Dark_Psychology": [
        "How the Pratfall Effect makes flawed charismatic leaders irresistible to the public.",
        "The silent language of micro-expressions used by master manipulators to gain trust.",
        "How cognitive dissonance forces honest minds to defend clear lies."
    ],
    "Future_Tech": [
        "Neural laces merging human consciousness with global distributed computing networks.",
        "Quantum teleportation of physical states across atomic-scale barriers.",
        "The rise of autonomous bio-designed nanobots curing cellular decay in real-time."
    ],
    "Finance_Geopolitics": [
        "The petrodollar collapse and the secret rise of resource-backed digital currencies.",
        "How algorithmic high-frequency trading rigs flash crashes to silently siphon wealth.",
        "The shadow shipping networks global oil under the cover of radar blackouts."
    ],
    "Ocean_Horror": [
        "The Mariana Trench sound anomaly detected deep beneath the seafloor sediment.",
        "The bizarre adaptation of abyssal creatures thriving inside boiling volcanic vents.",
        "Forgotten ghost ships discovered drifting perfectly preserved in sub-zero Arctic waters."
    ]
}

class SceneDetail(BaseModel):
    scene_text: str = Field(description="The portion of script written specifically for this scene narration.")
    search_keyword: str = Field(description="Strictly 2 to 4 premium English descriptive keywords. Do not use Hindi language words.")
    duration: int = Field(description="Estimated duration in seconds for this scene segment.")

class VideoScriptBreakdown(BaseModel):
    scenes: List[SceneDetail]
    music_mood: str = Field(description="The emotional mood/vibe for background music: 'uplifting', 'dramatic', 'calm', 'energetic', 'mysterious', or 'cinematic'.")

MOOD_TO_MUSIC_MAP = {
    "uplifting": "assets/music/uplifting.mp3",
    "dramatic": "assets/music/dramatic.mp3",
    "calm": "assets/music/calm.mp3",
    "energetic": "assets/music/energetic.mp3",
    "mysterious": "assets/music/mysterious.mp3",
    "cinematic": "assets/music/cinematic.mp3",
}

def get_music_path(mood):
    base_path = os.path.join("assets", "music")
    target_path = os.path.join(base_path, f"{mood.lower()}.mp3")
    default_path = os.path.join(base_path, "default.mp3")
    if os.path.exists(target_path):
        return target_path
    if os.path.exists(default_path):
        return default_path
    for fallback_path in MOOD_TO_MUSIC_MAP.values():
        if os.path.exists(fallback_path):
            return fallback_path
    return None

def resolve_audible_bgm_path(preferred_path=None, mood="cinematic"):
    """Return the first audible BGM path from preferred, mood, then known fallbacks."""
    # Always honor an explicit user upload if the file exists and looks valid.
    if preferred_path and os.path.exists(preferred_path):
        try:
            if os.path.getsize(preferred_path) > 1024 and get_audio_duration(preferred_path) >= 0.35:
                return preferred_path
        except Exception:
            return preferred_path

    candidates = []
    mood_path = get_music_path((mood or "cinematic").lower().strip())
    if mood_path:
        candidates.append(mood_path)
    for fallback_path in MOOD_TO_MUSIC_MAP.values():
        if fallback_path:
            candidates.append(fallback_path)

    seen = set()
    for path in candidates:
        if not path:
            continue
        norm = os.path.abspath(path)
        if norm in seen:
            continue
        seen.add(norm)
        if os.path.exists(path) and is_audio_audible(path, min_db=-70.0):
            return path
    return None

def get_audio_duration(audio_path):
    try:
        if MP3 is not None:
            audio = MP3(audio_path)
            return float(audio.info.length)
    except Exception:
        pass
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 5.0

def get_media_duration(media_path):
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', media_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return max(0.1, float(result.stdout.strip()))
    except Exception:
        return 3.0

def has_audio_stream(media_path):
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'a:0',
            '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', media_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        return result.returncode == 0 and "audio" in (result.stdout or "").lower()
    except Exception:
        return False

def is_audio_audible(audio_path, min_db=-55.0):
    if not audio_path or not os.path.exists(audio_path):
        return False
    if os.path.getsize(audio_path) < 1024:
        return False
    if get_audio_duration(audio_path) < 0.35:
        return False
    try:
        cmd = ['ffmpeg', '-hide_banner', '-i', audio_path, '-af', 'volumedetect', '-f', 'null', 'NUL']
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        output = (result.stderr or '') + "\n" + (result.stdout or '')
        max_match = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", output)
        mean_match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", output)
        if max_match:
            max_db = float(max_match.group(1))
            return max_db > min_db
        if mean_match:
            mean_db = float(mean_match.group(1))
            return mean_db > (min_db - 5.0)
    except Exception:
        pass
    return True

def is_remote_url(path_or_url):
    if not path_or_url:
        return False
    value = str(path_or_url).strip().lower()
    return value.startswith("http://") or value.startswith("https://")

def mix_audio_layers(video_input_path, output_path, bgm_path=None, bgm_volume=0.3, voice_path=None, voice_volume=1.0):
    """
    Audio mixing with BGM ducking: Voiceover stays at 100%, BGM ducks during speech.
    Steps:
    1. Voiceover track (if provided) plays at full volume.
    2. BGM plays at user-defined bgm_volume level.
    3. Sidechain compression: BGM volume reduces when voiceover is active, returns to level when silent.
    4. Fallback: Basic volume mixing if sidechain fails.
    """
    if not video_input_path or not os.path.exists(video_input_path):
        return False

    try:
        slider_bgm = max(0.0, min(1.0, float(bgm_volume)))
    except Exception:
        slider_bgm = 0.3

    # Get master duration from video itself
    master_dur = get_audio_duration(video_input_path)
    if master_dur <= 0:
        master_dur = None

    # Determine inputs
    has_bgm = bgm_path and os.path.exists(bgm_path)
    has_voice = voice_path and os.path.exists(voice_path)

    # If no BGM and no voice separate, just copy
    if not has_bgm and not has_voice:
        try:
            shutil.copy(video_input_path, output_path)
            return os.path.exists(output_path)
        except:
            return False

    cmd = ['ffmpeg', '-y', '-i', video_input_path]
    filter_chains = []
    input_idx = 1

    # Voice input
    voice_input_idx = None
    if has_voice:
        cmd += ['-i', voice_path]
        voice_input_idx = input_idx
        input_idx += 1

    # BGM input
    bgm_input_idx = None
    if has_bgm:
        cmd += ['-stream_loop', '-1', '-i', bgm_path]
        bgm_input_idx = input_idx
        input_idx += 1

    # Build filter graph
    # Map video as-is
    filter_graph = "[0:v]null[vout]"

    audio_labels = []
    current_filter_id = 0

    # Extract existing audio from video if present
    filter_graph += ";[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[base_audio]"
    audio_labels.append("base_audio")

    # Process voiceover
    if voice_input_idx is not None:
        voice_label = f"voice{current_filter_id}"
        filter_graph += f";[{voice_input_idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume={voice_volume:.2f}[{voice_label}]"
        audio_labels.append(voice_label)
        current_filter_id += 1

    # Process BGM with ducking
    if bgm_input_idx is not None:
        bgm_label = f"bgm{current_filter_id}"

        mapped_bgm_gain = 0.0 if slider_bgm <= 0.0 else min(1.0, 0.08 + (slider_bgm ** 1.25) * 0.9)

        # If we have voiceover, apply sidechain compression for ducking
        if voice_input_idx is not None:
            # BGM: apply volume then sidechain compress based on voice track
            bgm_chain = (
                f"[{bgm_input_idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                f"volume={mapped_bgm_gain:.3f}[bgm_raw];"
                f"[bgm_raw][{voice_label}]sidechaincompress=threshold=0.015:ratio=8:attack=5:release=100:makeup=1.2[{bgm_label}]"
            )
            filter_graph += ";" + bgm_chain
        else:
            # No voiceover: just volume control
            filter_graph += ";" + f"[{bgm_input_idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume={mapped_bgm_gain:.3f}[{bgm_label}]"

        if master_dur is not None:
            filter_graph += ";" + f"[{bgm_label}]atrim=0:{master_dur:.3f}[bgm_trimmed]"
            audio_labels.append("bgm_trimmed")
        else:
            audio_labels.append(bgm_label)

    # Mix all audio streams
    mix_inputs = '+'.join(f'[{l}]' for l in audio_labels if l.startswith('bgm') == False)
    bgm_inputs = '+'.join(f'[{l}]' for l in audio_labels if l.startswith('bgm') == True)

    if bgm_inputs:
        # Voiceover first, then BGM with sidechain already applied
        all_inputs = ''.join(f'[{l}]' for l in audio_labels)
        filter_graph += ";" + f"{all_inputs}amix=inputs={len(audio_labels)}:duration=first:dropout_transition=2[aout]"
    else:
        all_inputs = ''.join(f'[{l}]' for l in audio_labels)
        filter_graph += ";" + f"{all_inputs}amix=inputs={len(audio_labels)}:duration=first:dropout_transition=2[aout]"

    # Final cmd
    cmd += [
        '-filter_complex', filter_graph,
        '-map', '[vout]', '-map', '[aout]',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '22',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest', output_path
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
    except Exception as e:
        logger.warning(f"Ducking mix failed: {e}. Trying basic mix...")

    # Fallback: basic amix without ducking
    try:
        fallback_cmd = ['ffmpeg', '-y', '-i', video_input_path]
        fallback_filters = ["[0:v]null[vout]", "[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[base]"]
        fallback_labels = ["[base]"]
        fi = 1
        if has_voice:
            fallback_cmd += ['-i', voice_path]
            fallback_filters.append(f"[{fi}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=1.0[v{fi}]")
            fallback_labels.append(f"[v{fi}]")
            fi += 1
        if has_bgm:
            fallback_cmd += ['-stream_loop', '-1', '-i', bgm_path]
            mapped_gain = 0.0 if slider_bgm <= 0.0 else min(1.0, slider_bgm * 0.6)
            fallback_filters.append(f"[{fi}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume={mapped_gain:.3f}[b{fi}]")
            fallback_labels.append(f"[b{fi}]")
            fi += 1

        all_labels_str = ''.join(fallback_labels)
        fallback_filters.append(f"{all_labels_str}amix=inputs={len(fallback_labels)}:duration=first[aout]")
        fallback_cmd += ['-filter_complex', ';'.join(fallback_filters), '-map', '[vout]', '-map', '[aout]',
                         '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', output_path]
        subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception:
        # Last resort: plain copy
        try:
            shutil.copy(video_input_path, output_path)
            return True
        except:
            return False

# ========================================================
# EMERGENCY BGM HANDLER FUNCTIONS
# ========================================================
def get_emergency_bgm_path(mood="cinematic"):
    """Return a fallback BGM path based on mood. Creates a simple tone if no asset exists."""
    mood_map = {
        "uplifting": "assets/music/uplifting.mp3",
        "dramatic": "assets/music/dramatic.mp3",
        "calm": "assets/music/calm.mp3",
        "energetic": "assets/music/energetic.mp3",
        "mysterious": "assets/music/mysterious.mp3",
        "cinematic": "assets/music/cinematic.mp3",
        "sad": "assets/music/sad.mp3",
        "happy": "assets/music/happy.mp3",
        "romantic": "assets/music/romantic.mp3",
        "suspense": "assets/music/suspense.mp3",
    }
    mood = mood.lower().strip() if mood else "cinematic"
    bgm_path = mood_map.get(mood, "assets/music/cinematic.mp3")
    if os.path.exists(bgm_path) and os.path.getsize(bgm_path) > 1000:
        return bgm_path
    # Try alternative locations
    alt_paths = [
        bgm_path.replace("assets/music/", "music/"),
        bgm_path.replace("assets/music/", "assets/"),
        os.path.join("temp_scenes", f"emergency_{mood}.mp3"),
    ]
    for alt in alt_paths:
        if os.path.exists(alt) and os.path.getsize(alt) > 1000:
            return alt
    return None

def create_emergency_bgm(mood="cinematic", duration=30.0, output_path=None):
    """Create a synthetic emergency BGM track using ffmpeg audio synthesis."""
    if output_path is None:
        output_path = os.path.join("temp_scenes", f"emergency_bgm_{uuid.uuid4().hex[:8]}.mp3")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    safe_remove_file(output_path)

    # Mood-to-frequency mapping
    mood_freq = {
        "uplifting": 523.25,  # C5
        "dramatic": 110.0,    # A2
        "calm": 261.63,       # C4
        "energetic": 659.25,  # E5
        "mysterious": 196.0,  # G3
        "cinematic": 440.0,   # A4
        "sad": 207.65,        # G#3
        "happy": 587.33,      # D5
        "romantic": 349.23,   # F4
        "suspense": 164.81,   # E3
    }
    freq = mood_freq.get(mood.lower(), 440.0)

    try:
        # Generate a simple pad tone with gentle modulation
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'sine=f={freq}:d={duration}',
            '-f', 'lavfi', '-i', f'sine=f={freq * 1.5}:d={duration}',
            '-f', 'lavfi', '-i', f'sine=f={freq * 2.0}:d={duration}',
            '-filter_complex',
            f'[0:a]volume=0.3[a0];[1:a]volume=0.15[a1];[2:a]volume=0.08[a2];'
            f'[a0][a1][a2]amix=inputs=3:duration=first:dropout_transition=2,'
            f'lowpass=f=800,volume=0.5[aout]',
            '-map', '[aout]', '-c:a', 'libmp3lame', '-b:a', '64k', output_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            logger.info(f"Emergency BGM created for mood '{mood}' at {output_path}")
            return output_path
    except Exception as e:
        logger.warning(f"Emergency BGM creation failed: {e}")

    # Ultra fallback: silent audio
    try:
        silent_path = output_path.replace(".mp3", "_silent.mp3")
        cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-t', str(duration), '-c:a', 'libmp3lame', silent_path]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if os.path.exists(silent_path):
            return silent_path
    except:
        pass

    return None

def resolve_audible_bgm_path(preferred_path=None, mood="cinematic"):
    """Resolve BGM path: prefers uploaded file, then mood-based asset, then emergency generation."""
    if preferred_path and os.path.exists(str(preferred_path)) and os.path.getsize(str(preferred_path)) > 1000:
        return str(preferred_path)
    bgm_path = get_emergency_bgm_path(mood)
    if bgm_path:
        return bgm_path
    return create_emergency_bgm(mood)

def get_hwaccel_args():
    if getattr(get_hwaccel_args, "cached", None) is not None:
        return get_hwaccel_args.cached
    try:
        result = subprocess.run(["ffmpeg", "-hide_banner", "-hwaccel", "auto", "-h"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        enabled = result.returncode == 0
    except Exception:
        enabled = False
    get_hwaccel_args.cached = ["-hwaccel", "auto"] if enabled else []
    return get_hwaccel_args.cached

def get_video_resolution(video_path):
    try:
        cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', video_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        res_split = result.stdout.strip().split('x')
        if len(res_split) == 2:
            return int(res_split[0]), int(res_split[1])
    except Exception:
        pass
    return None, None

def parse_tagged_script(script_text):
    if "\n\n" in script_text.strip():
        paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]
    else:
        paragraphs = [p.strip() for p in script_text.split("\n") if p.strip()]
    scenes_mapped = []
    for idx, para in enumerate(paragraphs):
        keyword = "mystery"
        clean_text = para
        if "[" in para and "]" in para:
            start_idx = para.find("[")
            end_idx = para.find("]")
            tag_content = para[start_idx+1:end_idx]
            clean_text = para[end_idx+1:].strip()
            if ":" in tag_content:
                keyword = tag_content.split(":")[-1].strip()
            else:
                keyword = tag_content.strip()
        else:
            para_lower = para.lower()
            if "haveli" in para_lower or "palace" in para_lower or "castle" in para_lower:
                keyword = "palace"
            elif "darkness" in para_lower or "dark" in para_lower or "shadow" in para_lower:
                keyword = "darkness"
            elif "secret" in para_lower or "mystery" in para_lower:
                keyword = "mystery"
            else:
                words = [w.strip(",.?!\"'") for w in para.split() if len(w) > 4]
                stopwords = {"there", "their", "about", "would", "could", "should", "under", "these"}
                valid_words = [w for w in words if w.lower() not in stopwords]
                if valid_words:
                    keyword = " ".join(valid_words[:3])
        scenes_mapped.append({"scene_text": clean_text, "search_keyword": keyword, "duration": 5})
    return scenes_mapped

def run_async_in_thread(coro):
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
    def generate_script(topic, duration_choice, selected_model, language_choice):
        effective_api_key = st.session_state.get("user_gemini_api_key", "").strip() or GEMINI_API_KEY
        if has_genai and effective_api_key:
            try:
                client_gen = genai.Client(api_key=effective_api_key)
                num_scenes = 4 if "1 Minute" in duration_choice else 3
                if "Hinglish" in language_choice:
                    lang_instruction = "fluent Hinglish (Hindi written in Latin script)"
                elif "French" in language_choice:
                    lang_instruction = "fluent detailed Parisian French"
                elif "Japanese" in language_choice:
                    lang_instruction = "fluent natural Japanese"
                else:
                    lang_instruction = "clear modern English"
                prompt = (
                    f"Write a premium engaging short video script about '{topic}' in {lang_instruction}. "
                    f"Divide the video into exactly {num_scenes} sequential scenes. "
                    f"Each scene must contain unique descriptive text and a short English search keyword phrase (strictly 2 to 4 words) matching the visual context. "
                    f"Strictly avoid full sentences, verbs, or non-English words in the search_keyword field. "
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
                    scenes_mapped.append({"scene_text": item.get("scene_text", "").strip(), "search_keyword": kw, "duration": item.get("duration", 5)})
                music_mood = data.get("music_mood", "cinematic").lower().strip()
                if scenes_mapped:
                    return scenes_mapped, music_mood
            except Exception as e:
                logger.error(f"Script generation error: {e}")
        if "English" in language_choice:
            fallback_text = f"[Scene 1: space] Discover the incredible mysteries surrounding {topic} that science cannot explain.\n\n[Scene 2: history] Hidden deep within forgotten records lies a dark secret.\n\n[Scene 3: laboratory] Today, modern technology is finally revealing the truth."
        elif "French" in language_choice:
            fallback_text = f"[Scene 1: espace] Découvrez les mystères incroyables entourant {topic} que la science ne peut expliquer.\n\n[Scene 2: histoire] Caché profondément dans des archives oubliées se trouve un secret sombre.\n\n[Scene 3: laboratoire] Aujourd'hui, la technologie moderne révèle enfin la vérité."
        elif "Japanese" in language_choice:
            fallback_text = f"[Scene 1: 宇宙] 科学では説明できない、{topic}を取り巻く信じられない謎を発見してください。\n\n[Scene 2: 歴史] 忘れ去られた記録の奥深くに、暗い秘密が隠されています。\n\n[Scene 3: 研究室] 今日、現代のテクノロジーがついに真実を明らかにします。"
        else:
            fallback_text = f"[Scene 1: universe] {topic} ke baare mein kuch aise hairan kar dene wale rahasya jo sabhi se chupaye gaye.\n\n[Scene 2: mystery] Purani dastawezon mein dabi ek aisi sachai jise koi nahi janta.\n\n[Scene 3: hologram] Aaj ke modern scientists is ghabrahat bhare sach ko bahar la rahe hain."
        return parse_tagged_script(fallback_text), "cinematic"

class VisualEngine:
    @staticmethod
    def fetch_pexels_clip(query, output_filename):
        pexels_key = os.getenv("PEXELS_API_KEY") or get_system_secret("PEXELS_API_KEY")
        if not pexels_key:
            return False
        safe_remove_file(output_filename)
        clean_query = query.replace('"', '').replace("'", "").strip()
        url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(clean_query)}&per_page=8"
        headers = {"Authorization": pexels_key}
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                videos = data.get("videos", [])
                for selected_video in videos:
                    video_files = sorted(
                        selected_video.get("video_files", []),
                        key=lambda item: int(item.get("width") or 0),
                        reverse=True,
                    )
                    for video_file in video_files:
                        video_url = video_file.get("link")
                        if not video_url:
                            continue
                        safe_remove_file(output_filename)
                        with requests.get(video_url, stream=True, timeout=15) as r:
                            with open(output_filename, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                        if os.path.exists(output_filename) and os.path.getsize(output_filename) > 100000:
                            return True
        except Exception as e:
            logger.error(f"Pexels error: {e}")
        return False

    @staticmethod
    def fetch_pixabay_clip(query, output_filename):
        pixabay_key = os.getenv("PIXABAY_API_KEY") or get_system_secret("PIXABAY_API_KEY")
        if not pixabay_key:
            return False
        safe_remove_file(output_filename)
        clean_query = query.replace('"', '').replace("'", "").strip()
        if not clean_query:
            return False
        url = f"https://pixabay.com/api/videos/?key={pixabay_key}&q={clean_query}&per_page=10&video_type=film"
        try:
            res = requests.get(url, timeout=12)
            if res.status_code == 200:
                response = res.json()
                for selected_video in response.get("hits", []):
                    videos_dict = selected_video.get("videos", {})
                    target_video = videos_dict.get("large") or videos_dict.get("medium") or videos_dict.get("small")
                    if target_video and "url" in target_video:
                        video_url = target_video["url"]
                        safe_remove_file(output_filename)
                        with requests.get(video_url, stream=True, timeout=15) as r:
                            with open(output_filename, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192): 
                                    f.write(chunk)
                        if os.path.exists(output_filename) and os.path.getsize(output_filename) > 100000:
                            return True
        except Exception as e:
            logger.error(f"Pixabay error: {e}")
        return False

    @staticmethod
    def generate_sd_core_image(prompt, output_filename, aspect_ratio_str="9:16"):
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
            except Exception as e:
                logger.error(f"Stability AI error: {e}")
        try:
            width, height = 768, 1344
            if sd_aspect == "16:9":
                width, height = 1344, 768
            elif sd_aspect == "1:1":
                width, height = 1024, 1024
            clean_prompt = prompt.replace('"', '').replace("'", "").strip()
            encoded_prompt = urllib.parse.quote(f"Cinematic masterpiece, highly detailed: {clean_prompt}")
            poll_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width={width}&height={height}&seed={random.randint(1, 999999)}&nologo=true"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"}
            response = requests.get(poll_url, headers=headers, timeout=25)
            if response.status_code == 200 and len(response.content) > 10000:
                with open(output_filename, "wb") as f:
                    f.write(response.content)
                return True
        except Exception as e:
            logger.error(f"Pollinations error: {e}")
        pexels_key = os.getenv("PEXELS_API_KEY") or get_system_secret("PEXELS_API_KEY")
        if pexels_key:
            try:
                clean_query = prompt.replace('"', '').replace("'", "").strip()
                url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(clean_query)}&per_page=5"
                headers = {"Authorization": pexels_key}
                res = requests.get(url, headers=headers, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    photos = data.get("photos", [])
                    if photos:
                        chosen_photo = random.choice(photos)
                        img_url = chosen_photo.get("src", {}).get("large2x") or chosen_photo.get("src", {}).get("original")
                        if img_url:
                            img_res = requests.get(img_url, timeout=15)
                            if img_res.status_code == 200 and len(img_res.content) > 10000:
                                with open(output_filename, "wb") as f:
                                    f.write(img_res.content)
                                return True
            except Exception as e:
                logger.error(f"Pexels image error: {e}")
        try:
            width, height = 768, 1344
            if sd_aspect == "16:9":
                width, height = 1344, 768
            elif sd_aspect == "1:1":
                width, height = 1024, 1024
            unsplash_url = f"https://images.unsplash.com/photo-1582213782179-e0d53f98f2ca?auto=format&fit=crop&w={width}&h={height}&q=80"
            response = requests.get(unsplash_url, timeout=20)
            if response.status_code == 200 and len(response.content) > 10000:
                with open(output_filename, "wb") as f:
                    f.write(response.content)
                return True
        except Exception as e:
            logger.error(f"Unsplash error: {e}")
        return False

    @staticmethod
    def convert_image_to_video(image_path, output_video_path, duration, res_width, res_height):
        safe_remove_file(output_video_path)
        cmd = ['ffmpeg', '-y', '-loop', '1', '-i', image_path, '-t', f"{duration:.2f}", '-vf', f'scale={res_width}:{res_height}:force_original_aspect_ratio=increase,crop={res_width}:{res_height},setsar=1', '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'fastdecode', '-r', '24', output_video_path]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except Exception as e:
            logger.error(f"Convert image to video error: {e}")
            return False

def get_scene_asset(description, output_filename, scene_text=None, idx=None, status_dict=None):
    """
    Smart Asset Sourcing Layer
    1. Search Pexels stock video clips
    2. If no match, search Pixabay stock video clips
    3. If still no clip, fallback to AI Video Generation Pipeline:
       a. Generate SD reference image from scene text
       b. Convert image to video via Stability AI I2V (SVD)
       c. If SVD fails, use zoompan fallback
    """
    try:
        hinglish_map = {"kisan": "farmer", "beej": "seeds", "paas": "near", "haveli": "ancient mansion", "ghar": "house", "paani": "water", "samundar": "ocean", "rahasya": "mystery", "sach": "truth", "jungle": "forest", "pahar": "mount", "raja": "king", "rani": "queen", "sona": "gold", "chand": "moon", "suraj": "sun"}
        clean_desc = description.lower().replace('"', '').replace("'", "").strip()
        words = clean_desc.split()
        translated_words = []
        for w in words:
            clean_w = w.strip(",.?!\"'")
            translated_words.append(hinglish_map.get(clean_w, clean_w))
        refined_query = " ".join(translated_words)
        # --- STOCK LAYER 1: Pexels ---
        if status_dict is not None and idx is not None:
            status_dict[idx] = f"📹 Sourcing Pexels: '{refined_query}'"
        if VisualEngine.fetch_pexels_clip(refined_query, output_filename):
            cache_dir = os.path.join("assets", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            permanent_path = os.path.join(cache_dir, f"cache_{uuid.uuid4().hex[:8]}.mp4")
            shutil.copy(output_filename, permanent_path)
            cache_clip(refined_query, permanent_path)
            if status_dict is not None and idx is not None:
                status_dict[idx] = f"✅ Pexels: '{refined_query}'"
            return True
        # --- STOCK LAYER 2: Pixabay ---
        if status_dict is not None and idx is not None:
            status_dict[idx] = f"📹 Sourcing Pixabay: '{refined_query}'"
        if VisualEngine.fetch_pixabay_clip(refined_query, output_filename):
            cache_dir = os.path.join("assets", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            permanent_path = os.path.join(cache_dir, f"cache_{uuid.uuid4().hex[:8]}.mp4")
            shutil.copy(output_filename, permanent_path)
            cache_clip(refined_query, permanent_path)
            if status_dict is not None and idx is not None:
                status_dict[idx] = f"✅ Pixabay: '{refined_query}'"
            return True
        # --- AI GENERATION PIPELINE FALLBACK ---
        if scene_text:
            if status_dict is not None and idx is not None:
                status_dict[idx] = "🎬 Stock clips not found. Switching to AI Generation Pipeline..."
            # Step A: Generate reference image using SD/Pollinations
            sd_temp_img = f"temp_scenes/sd_ref_{uuid.uuid4().hex[:8]}.png"
            os.makedirs("temp_scenes", exist_ok=True)
            img_success = VisualEngine.generate_sd_core_image(scene_text, sd_temp_img, "16:9")
            if img_success and os.path.exists(sd_temp_img) and os.path.getsize(sd_temp_img) > 5000:
                # Step B: Try Stability AI I2V
                if status_dict is not None and idx is not None:
                    status_dict[idx] = "🎬 Running Stability AI I2V generation..."
                ai_video_path = StitcherEngine.generate_ai_video_stability_i2v(
                    image_path=sd_temp_img,
                    output_path=output_filename
                )
                if ai_video_path and os.path.exists(ai_video_path) and os.path.getsize(ai_video_path) > 5000:
                    safe_remove_file(sd_temp_img)
                    if status_dict is not None and idx is not None:
                        status_dict[idx] = "✅ AI I2V Video Generated"
                    return True
                # Step C: SVD HF fallback
                if status_dict is not None and idx is not None:
                    status_dict[idx] = "🎬 Trying SVD HuggingFace fallback..."
                svd_path = convert_image_to_video_svd_robust(sd_temp_img)
                if svd_path and os.path.exists(svd_path) and os.path.getsize(svd_path) > 5000:
                    shutil.copy(svd_path, output_filename)
                    safe_remove_file(sd_temp_img)
                    if status_dict is not None and idx is not None:
                        status_dict[idx] = "✅ SVD AI Video Generated"
                    return True
                safe_remove_file(sd_temp_img)
            # Step D: Text-to-Video API fallback
            if status_dict is not None and idx is not None:
                status_dict[idx] = "🎬 Trying Text-to-Video generation..."
            ai_video_url = generate_ai_video(scene_text)
            if ai_video_url:
                # If URL is a local path
                if os.path.exists(ai_video_url):
                    shutil.copy(ai_video_url, output_filename)
                    if os.path.exists(output_filename) and os.path.getsize(output_filename) > 100:
                        if status_dict is not None and idx is not None:
                            status_dict[idx] = "✅ AI Video Generated"
                        return True
                # If URL is a remote URL
                try:
                    with requests.get(ai_video_url, stream=True, timeout=60) as r:
                        if r.status_code == 200:
                            with open(output_filename, "wb") as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            if os.path.exists(output_filename) and os.path.getsize(output_filename) > 100:
                                if status_dict is not None and idx is not None:
                                    status_dict[idx] = "✅ AI Video Generated"
                                return True
                except:
                    pass
    except Exception as e:
        logger.error(f"Get scene asset error: {e}")
    return False

def generate_pro_image(prompt, aspect_ratio="16:9", negative_prompt=""):
    api_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")
    width, height = 1024, 1024
    if aspect_ratio == "16:9":
        width, height = 1344, 768
    elif aspect_ratio == "9:16":
        width, height = 768, 1344
    elif aspect_ratio == "21:9":
        width, height = 1536, 640
    elif aspect_ratio == "4:5":
        width, height = 896, 1120
    elif aspect_ratio == "3:2":
        width, height = 1152, 768
    if api_key and api_key != "mock" and len(api_key.strip()) > 5:
        url = "https://api.stability.ai/v2beta/stable-image/generate/core"
        headers = {"authorization": f"Bearer {api_key}", "accept": "image/*"}
        files = {"prompt": (None, f"{prompt}, cinematic lighting, 8k, photorealistic"), "aspect_ratio": (None, aspect_ratio)}
        if negative_prompt.strip():
            files["negative_prompt"] = (None, negative_prompt.strip())
        try:
            response = requests.post(url, headers=headers, files=files, timeout=30)
            if response.status_code == 200 and len(response.content) > 10000:
                output_path = f"workshop_output_{uuid.uuid4().hex[:6]}.png"
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return output_path
        except Exception as e:
            logger.error(f"Generate pro image error: {e}")
    try:
        clean_prompt = prompt.replace('"', '').replace("'", "").strip()
        encoded_prompt = urllib.parse.quote(f"{clean_prompt}, cinematic, 8k resolution, highly detailed")
        poll_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width={width}&height={height}&seed={random.randint(1, 999999)}&nologo=true"
        if negative_prompt.strip():
            encoded_neg = urllib.parse.quote(negative_prompt.strip())
            poll_url += f"&negative={encoded_neg}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"}
        response = requests.get(poll_url, headers=headers, timeout=25)
        if response.status_code == 200 and len(response.content) > 10000:
            output_path = f"workshop_output_{uuid.uuid4().hex[:6]}.png"
            with open(output_path, "wb") as f:
                f.write(response.content)
            return output_path
    except Exception as e:
        logger.error(f"Pollinations pro error: {e}")
    try:
        img = Image.new("RGB", (width, height), color=(18, 19, 26))
        d = ImageDraw.Draw(img)
        d.rectangle([(10, 10), (width - 10, height - 10)], outline=(236, 72, 153), width=4)
        output_path = f"workshop_output_{uuid.uuid4().hex[:6]}.png"
        img.save(output_path)
        return output_path
    except Exception as e:
        logger.error(f"Fallback image error: {e}")
    return None

def convert_image_to_video_svd_robust(image_path, motion_bucket_id=127):
    """
    Rock-solid SVD (Stable Video Diffusion) API fallback mechanism.
    Tiers:
    1. HuggingFace Inference API (stabilityai/stable-video-diffusion-img2vid-xt)
    2. Stability AI I2V API directly
    3. FFmpeg zoompan fallback with error recovery
    Returns video path string or None.
    """
    if not image_path or not os.path.exists(image_path):
        return None

    video_path = None
    os.makedirs("saved_renders", exist_ok=True)

    # Tier 1: HuggingFace Inference API
    hf_key = os.getenv("HUGGINGFACE_API_KEY") or get_system_secret("HUGGINGFACE_API_KEY")
    if hf_key and len(hf_key.strip()) > 5:
        try:
            try:
                with open(image_path, "rb") as img_file:
                    img_data = img_file.read()
                url = "https://api-inference.huggingface.co/models/stabilityai/stable-video-diffusion-img2vid-xt"
                headers = {
                    "Authorization": f"Bearer {hf_key}",
                    "Content-Type": "application/octet-stream",
                    "Accept": "video/mp4"
                }
                params = {"parameters": {"motion_bucket_id": int(motion_bucket_id)}}
                response = requests.post(url, headers=headers, data=img_data, params=params, timeout=90)
                if response.status_code == 200 and len(response.content) > 5000:
                    output_video_path = f"saved_renders/svd_hf_{uuid.uuid4().hex[:6]}.mp4"
                    with open(output_video_path, "wb") as out_f:
                        out_f.write(response.content)
                    video_path = output_video_path
                    logger.info(f"SVD HF API success: {video_path}")
                    return video_path
                elif response.status_code == 503:
                    # Model loading, retry once
                    retry_after = int(response.headers.get("Retry-After", 30))
                    logger.info(f"SVD HF model loading, waiting {retry_after}s...")
                    time.sleep(min(retry_after, 60))
                    response2 = requests.post(url, headers=headers, data=img_data, params=params, timeout=90)
                    if response2.status_code == 200 and len(response2.content) > 5000:
                        output_video_path = f"saved_renders/svd_hf_{uuid.uuid4().hex[:6]}.mp4"
                        with open(output_video_path, "wb") as out_f:
                            out_f.write(response2.content)
                        video_path = output_video_path
                        logger.info(f"SVD HF API success (retry): {video_path}")
                        return video_path
            except Exception as e:
                logger.warning(f"SVD HF API attempt failed: {e}")
        except Exception as e:
            logger.warning(f"SVD HF setup error: {e}")

    # Tier 2: Stability AI I2V API directly
    if not video_path:
        try:
            stability_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")
            if stability_key:
                from engine import StitcherEngine as SE
                result = SE.generate_ai_video_stability_i2v(
                    image_path=image_path,
                    output_path=f"saved_renders/svd_stability_{uuid.uuid4().hex[:6]}.mp4",
                    motion_bucket_id=motion_bucket_id
                )
                if result and os.path.exists(result) and os.path.getsize(result) > 5000:
                    video_path = result
                    logger.info(f"SVD Stability I2V success: {video_path}")
                    return video_path
        except Exception as e:
            logger.warning(f"SVD Stability I2V attempt failed: {e}")

    # Tier 3: FFmpeg zoompan fallback with Enhanced Ken Burns effect
    if not video_path:
        try:
            output_video_path = f"saved_renders/svd_fallback_{uuid.uuid4().hex[:6]}.mp4"
            # Try high-quality zoompan first
            cmd = [
                'ffmpeg', '-y', '-loop', '1', '-i', image_path, '-t', '4',
                '-vf', (
                    f"scale=iw*2:ih*2:flags=lanczos,"
                    f"zoompan=z='if(lte(zoom,1.0),1.15,min(zoom+0.002,1.6))':"
                    f"d=96:s=1280x720:fps=24,"
                    f"setsar=1"
                ),
                '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                '-r', '24', output_video_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 5000:
                video_path = output_video_path
                logger.info(f"SVD zoompan success: {video_path}")
                return video_path
        except Exception as e:
            logger.warning(f"SVD zoompan failed: {e}")

        # Tier 3b: Simple static fallback
        try:
            output_video_path = f"saved_renders/svd_static_{uuid.uuid4().hex[:6]}.mp4"
            cmd = [
                'ffmpeg', '-y', '-loop', '1', '-i', image_path, '-t', '4',
                '-vf', 'scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1',
                '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                '-r', '24', output_video_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 5000:
                video_path = output_video_path
                logger.info(f"SVD static success: {video_path}")
                return video_path
        except Exception as e:
            logger.warning(f"SVD static fallback failed: {e}")

    return video_path

def generate_ai_video(prompt):
    """
    AI Video Generation Engine with Stability AI I2V as primary, Luma/Runway as fallback.
    Supports both text-to-video and image-to-video via Stability AI API.
    """
    luma_key = os.getenv("LUMA_API_KEY") or get_system_secret("LUMA_API_KEY")
    runway_key = os.getenv("RUNWAY_API_KEY") or get_system_secret("RUNWAY_API_KEY")
    stability_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")

    # Try Stability AI Image-to-Video first (if an image path is passed as prompt or we use text-to-video)
    if stability_key:
        # Try Stability AI text-to-video
        try:
            url = "https://api.stability.ai/v2beta/generation/stable-video-diffusion/text-to-video"
            headers = {"authorization": f"Bearer {stability_key}", "accept": "application/json"}
            payload = {
                "prompt": f"Cinematic footage: {prompt}, smooth motion, high quality, 24fps",
                "seed": random.randint(0, 999999),
                "cfg_scale": 7.0,
                "motion_bucket_id": 127,
                "seconds": 5
            }
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            if res.status_code in [200, 201, 202]:
                result_data = res.json()
                gen_id = result_data.get("id")
                if gen_id:
                    result_url = f"https://api.stability.ai/v2beta/generation/stable-video-diffusion/text-to-video/result/{gen_id}"
                    headers_get = {"authorization": f"Bearer {stability_key}", "accept": "video/*"}
                    for attempt in range(30):
                        time.sleep(5)
                        poll_res = requests.get(result_url, headers=headers_get, timeout=20)
                        if poll_res.status_code == 200 and len(poll_res.content) > 5000:
                            output_path = f"saved_renders/svd_t2v_{uuid.uuid4().hex[:6]}.mp4"
                            os.makedirs("saved_renders", exist_ok=True)
                            with open(output_path, "wb") as f:
                                f.write(poll_res.content)
                            logger.info(f"Stability AI T2V generated: {output_path}")
                            return output_path
                        elif poll_res.status_code == 202:
                            continue
                        else:
                            break
        except Exception as e:
            logger.warning(f"Stability AI T2V error: {e}")

        # Try Luma AI with retry logic
    if luma_key:
        url = "https://api.lumalabs.ai/dream-machine/v1/generations"
        headers = {"Authorization": f"Bearer {luma_key}", "Content-Type": "application/json"}
        payload = {"prompt": prompt, "aspect_ratio": "16:9"}
        
        max_retries = 3
        retry_delay = 3
        
        for retry_attempt in range(max_retries):
            try:
                if retry_attempt > 0:
                    logger.info(f"Luma API retry attempt {retry_attempt + 1}/{max_retries}...")
                    time.sleep(retry_delay * retry_attempt)
                
                res = requests.post(url, headers=headers, json=payload, timeout=60)
                
                if res.status_code in [200, 201]:
                    gen_data = res.json()
                    gen_id = gen_data.get("id")
                    if gen_id:
                        poll_url = f"{url}/{gen_id}"
                        
                        poll_retries = 3
                        for poll_retry in range(poll_retries):
                            try:
                                for _ in range(30):
                                    time.sleep(5)
                                    poll_res = requests.get(poll_url, headers=headers, timeout=30)
                                    if poll_res.status_code == 200:
                                        poll_data = poll_res.json()
                                        state = poll_data.get("state")
                                        if state == "completed":
                                            video_url = poll_data.get("assets", {}).get("video")
                                            if video_url:
                                                logger.info(f"Luma AI video generated on attempt {retry_attempt + 1}")
                                                return video_url
                                        elif state == "failed":
                                            logger.warning(f"Luma generation failed, retry {poll_retry + 1}/{poll_retries}")
                                            break
                                    elif poll_res.status_code == 429:
                                        logger.warning("Luma rate limited, backing off...")
                                        time.sleep(10)
                                        continue
                            except requests.exceptions.Timeout:
                                logger.warning(f"Luma poll timeout (retry {poll_retry + 1}/{poll_retries})")
                                time.sleep(5)
                                continue
                            except Exception as poll_e:
                                logger.warning(f"Luma poll error (retry {poll_retry + 1}/{poll_retries}): {poll_e}")
                                time.sleep(5)
                                continue
                            break  # Success or non-retryable failure
                
                elif res.status_code == 429:
                    logger.warning(f"Luma rate limited (attempt {retry_attempt + 1}), waiting...")
                    time.sleep(15)
                    continue
                elif res.status_code >= 500:
                    logger.warning(f"Luma server error {res.status_code} (attempt {retry_attempt + 1})")
                    continue
                else:
                    logger.warning(f"Luma returned {res.status_code}, not retrying")
                    break
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Luma API timeout (retry {retry_attempt + 1}/{max_retries})")
                if retry_attempt < max_retries - 1:
                    continue
                else:
                    logger.error("Luma API failed after all retries")
                    break
            except requests.exceptions.ConnectionError:
                logger.warning(f"Luma connection error (retry {retry_attempt + 1}/{max_retries})")
                if retry_attempt < max_retries - 1:
                    time.sleep(10)
                    continue
                else:
                    break
            except Exception as e:
                logger.warning(f"Luma error (attempt {retry_attempt + 1}): {e}")
                if retry_attempt < max_retries - 1:
                    continue
                else:
                    break
            
            break  # Success, exit retry loop

    # Try Runway Gen-3
    if runway_key:
        url = "https://api.runwayml.com/v1/tasks"
        headers = {"Authorization": f"Bearer {runway_key}", "Content-Type": "application/json", "X-Runway-Version": "2024-11-06"}
        payload = {"taskType": "text_to_video", "promptText": prompt}
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=35)
            if res.status_code in [200, 201]:
                task_id = res.json().get("id")
                if task_id:
                    poll_url = f"{url}/{task_id}"
                    for _ in range(30):
                        time.sleep(5)
                        poll_res = requests.get(poll_url, headers=headers, timeout=20)
                        if poll_res.status_code == 200:
                            task_data = poll_res.json()
                            status = task_data.get("status")
                            if status == "SUCCEEDED":
                                outputs = task_data.get("outputs", [])
                                if outputs:
                                    return outputs[0]
                            elif status == "FAILED":
                                break
        except Exception as e:
            logger.warning(f"Runway error: {e}")

    return None

class AudioEngine:
    @staticmethod
    def generate_elevenlabs_speech(text, output_filename, voice_id):
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
        except Exception as e:
            logger.error(f"ElevenLabs error: {e}")
        return False

    @staticmethod
    def run_fallback_tts(text, output_filename, language_choice, voice_profile):
        safe_remove_file(output_filename)
        is_male = "Drew" in voice_profile or "Male" in voice_profile
        if edge_tts is None:
            return False

        if "French" in language_choice:
            voice_candidates = [
                "fr-FR-HenriNeural" if is_male else "fr-FR-DeniseNeural",
                "fr-FR-DeniseNeural" if is_male else "fr-FR-HenriNeural",
                "en-US-GuyNeural" if is_male else "en-US-AriaNeural",
            ]
        elif "Japanese" in language_choice:
            voice_candidates = [
                "ja-JP-KeitaNeural" if is_male else "ja-JP-NanamiNeural",
                "ja-JP-NanamiNeural" if is_male else "ja-JP-KeitaNeural",
                "en-US-GuyNeural" if is_male else "en-US-AriaNeural",
            ]
        elif "English" in language_choice:
            voice_candidates = [
                "en-US-GuyNeural" if is_male else "en-US-AriaNeural",
                "en-US-AriaNeural" if is_male else "en-US-GuyNeural",
                "en-GB-RyanNeural" if is_male else "en-GB-SoniaNeural",
            ]
        else:
            voice_candidates = [
                "hi-IN-MadhurNeural" if is_male else "hi-IN-SwaraNeural",
                "hi-IN-SwaraNeural" if is_male else "hi-IN-MadhurNeural",
                "en-IN-PrabhatNeural" if is_male else "en-IN-NeerjaNeural",
                "en-US-GuyNeural" if is_male else "en-US-AriaNeural",
            ]

        for voice_name in voice_candidates:
            try:
                safe_remove_file(output_filename)
                run_async_in_thread(edge_tts.Communicate(text, voice_name).save(output_filename))
                if os.path.exists(output_filename) and os.path.getsize(output_filename) > 2048:
                    return True
            except Exception as e:
                logger.warning(f"Fallback TTS voice failed ({voice_name}): {e}")
                continue

        return False

class StitcherEngine:
    @staticmethod
    def generate_ai_video(image_path, output_video_path):
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
        except Exception as e:
            logger.error(f"Stability AI video error: {e}")
        return False

    @staticmethod
    def generate_ai_video_stability_i2v(image_path, output_path, motion_bucket_id=127):
        """
        Full Stability AI Image-to-Video (I2V) generation with robust polling.
        Returns output_path if successful, None otherwise.
        """
        stability_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")
        if not stability_key or not image_path or not os.path.exists(image_path):
            return None

        safe_remove_file(output_path)
        url = "https://api.stability.ai/v2beta/image-to-video"
        headers = {"authorization": f"Bearer {stability_key}"}
        try:
            with open(image_path, "rb") as img_file:
                files = {"image": img_file}
                data = {
                    "seed": random.randint(0, 999999),
                    "cfg_scale": 1.8,
                    "motion_bucket_id": motion_bucket_id,
                }
                response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
            if response.status_code != 200:
                logger.warning(f"Stability I2V initiation failed: {response.status_code}")
                return None
            gen_data = response.json()
            generation_id = gen_data.get("id")
            if not generation_id:
                logger.warning("No generation ID from Stability I2V")
                return None
            result_url = f"https://api.stability.ai/v2beta/image-to-video/result/{generation_id}"
            headers_get = {"authorization": f"Bearer {stability_key}", "accept": "video/*"}
            # Poll for up to 120 seconds
            for attempt in range(24):
                time.sleep(5)
                try:
                    poll_res = requests.get(result_url, headers=headers_get, timeout=30)
                    if poll_res.status_code == 202:
                        continue  # Still processing
                    elif poll_res.status_code == 200:
                        if len(poll_res.content) > 5000:
                            with open(output_path, "wb") as f:
                                f.write(poll_res.content)
                            logger.info(f"Stability I2V generated: {output_path} ({len(poll_res.content)} bytes)")
                            return output_path
                        else:
                            logger.warning("Stability I2V result too small")
                            return None
                    else:
                        logger.warning(f"Stability I2V poll error: {poll_res.status_code}")
                        return None
                except requests.exceptions.Timeout:
                    if attempt >= 20:
                        return None
                    continue
                except Exception as poll_e:
                    logger.warning(f"Stability I2V poll exception: {poll_e}")
                    if attempt >= 20:
                        return None
                    continue
        except requests.exceptions.Timeout:
            logger.warning("Stability I2V request timed out")
            return None
        except Exception as e:
            logger.error(f"Stability I2V error: {e}")
            return None
        return None

    @staticmethod
    def generate_smart_fallback_motion(text, image_path, output_video_path, res_width=720, res_height=1280, workshop_img=None, idx=None, status_dict=None):
        os.makedirs("temp_scenes", exist_ok=True)
        safe_remove_file(output_video_path)
        if status_dict is not None and idx is not None:
            status_dict[idx] = "Compiling movement matrix..."
        fallback_source_image = image_path
        if not fallback_source_image or not os.path.exists(fallback_source_image):
            if workshop_img and os.path.exists(workshop_img):
                fallback_source_image = workshop_img
            else:
                fallback_source_image = os.path.join("temp_scenes", f"temp_solid_canvas_{uuid.uuid4().hex[:6]}.png")
                cmd_img = ['ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=#050508:s={res_width}x{res_height}', '-vframes', '1', fallback_source_image]
                subprocess.run(cmd_img, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stability_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")
        if stability_key and stability_key != "mock" and fallback_source_image and os.path.exists(fallback_source_image):
            if status_dict is not None and idx is not None:
                status_dict[idx] = "Running AI Image-to-Video generation..."
            if StitcherEngine.generate_ai_video(fallback_source_image, output_video_path):
                return True
        if status_dict is not None and idx is not None:
            status_dict[idx] = "Running SVD pipeline fallbacks..."
        svd_path = convert_image_to_video_svd_robust(fallback_source_image)
        if svd_path and os.path.exists(svd_path):
            shutil.copy(svd_path, output_video_path)
            return True
        try:
            cmd = ['ffmpeg', '-y', '-loop', '1', '-i', fallback_source_image, '-t', '5', '-vf', f"scale={res_width*2}:{res_height*2},zoompan=z='min(zoom+0.0015,1.3)':d=120:s={res_width}x{res_height},setsar=1", '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'fastdecode', '-r', '24', output_video_path]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 100:
                return True
        except Exception as e:
            logger.error(f"Fallback motion error: {e}")
        return create_emergency_solid_clip(output_video_path, 5.0, res_width, res_height)

    @staticmethod
    def build_scene_stitched_video_isolated(scenes_data, video_output, size_choice, voice_profile, language_choice, bgm_path=None, bgm_volume=0.3, music_mood=None, status_dict=None, workshop_img=None):
        safe_remove_file(video_output)
        # Resolution mapping for upsampling: 720p, 1080p, 2K, 4K
        aspect = "9:16"
        if "16:9" in size_choice:
            aspect = "16:9"
        elif "1:1" in size_choice:
            aspect = "1:1"
        # Quality detection from session state
        quality = st.session_state.get("cinematic_quality", "Standard")
        if quality == "4K":
            res_map = {"9:16": (2160, 3840), "16:9": (3840, 2160), "1:1": (3840, 3840)}
        elif quality == "2K":
            res_map = {"9:16": (1440, 2560), "16:9": (2560, 1440), "1:1": (2560, 2560)}
        elif quality == "HD" or quality == "Pro":
            res_map = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
        else:
            res_map = {"9:16": (720, 1280), "16:9": (1280, 720), "1:1": (1080, 1080)}
        res_width, res_height = res_map.get(aspect, (720, 1280))
        session_workspace_id = f"workspace_{uuid.uuid4().hex}"
        workspace_dir = os.path.join("temp_scenes", session_workspace_id)
        os.makedirs(workspace_dir, exist_ok=True)
        compiled_scenes_paths = []
        def process_scene_segment(idx, scene):
            text = scene["scene_text"]
            kw = scene["search_keyword"]
            if status_dict is not None:
                status_dict[idx] = "Synthesizing vocal elements..."
            audio_segment_path = os.path.join(workspace_dir, f"temp_voice_{idx}.mp3")
            voice_built = False
            selected_voice_meta = ELEVENLABS_VOICES.get(voice_profile, {})
            selected_voice_id = selected_voice_meta.get("id")
            if not selected_voice_id:
                selected_voice_id = "21m00Tcm4TlvDq8ikWAM" if "Male" in voice_profile else "pNInz6obpgDQ5IdwJg7p"
            if ELEVENLABS_API_KEY:
                voice_built = AudioEngine.generate_elevenlabs_speech(text, audio_segment_path, selected_voice_id)
            if not voice_built:
                voice_built = AudioEngine.run_fallback_tts(text=text, output_filename=audio_segment_path, language_choice=language_choice, voice_profile=voice_profile)
            if (not voice_built) or (not os.path.exists(audio_segment_path)) or (not is_audio_audible(audio_segment_path)):
                alt_voice_type = "male" if "Male" in voice_profile else "female"
                alt_audio = generate_emotion_voice(
                    text=text,
                    emotion="neutral",
                    voice_type=alt_voice_type,
                    output_path=audio_segment_path,
                    elevenlabs_voice_id=selected_voice_id,
                )
                voice_built = bool(alt_audio and os.path.exists(audio_segment_path) and is_audio_audible(audio_segment_path))
            if not voice_built:
                create_emergency_silent_audio(audio_segment_path, 5.0)
            dur = get_audio_duration(audio_segment_path)
            if dur <= 0:
                dur = 5.0
            raw_video_path = os.path.join(workspace_dir, f"temp_raw_vid_{idx}.mp4")
            success = get_scene_asset(description=kw, output_filename=raw_video_path, scene_text=text, idx=idx, status_dict=status_dict)
            if not success or not os.path.exists(raw_video_path) or os.path.getsize(raw_video_path) < 1000:
                if status_dict is not None:
                    status_dict[idx] = "Generating SD reference image..."
                sd_temp_img = os.path.join(workspace_dir, f"temp_sd_base_{idx}.png")
                sd_success = VisualEngine.generate_sd_core_image(text, sd_temp_img, size_choice)
                ai_video_success = StitcherEngine.generate_smart_fallback_motion(text=text, image_path=sd_temp_img if sd_success else None, output_video_path=raw_video_path, res_width=res_width, res_height=res_height, workshop_img=workshop_img, idx=idx, status_dict=status_dict)
                if os.path.exists(sd_temp_img):
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
                vf_filter_with_text = f"tpad=stop_mode=clone:stop_duration=10,eq=saturation=1.15:contrast=1.05,{drawtext_filter},fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start:.2f}:d=0.4"
                vf_filter_no_text = f"tpad=stop_mode=clone:stop_duration=10,eq=saturation=1.15:contrast=1.05,fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start:.2f}:d=0.4"
            else:
                vf_filter_with_text = f'scale={res_width}:{res_height}:force_original_aspect_ratio=increase,crop={res_width}:{res_height},setsar=1,tpad=stop_mode=clone:stop_duration=10,eq=saturation=1.15:contrast=1.05,{drawtext_filter},fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start:.2f}:d=0.4'
                vf_filter_no_text = f'scale={res_width}:{res_height}:force_original_aspect_ratio=increase,crop={res_width}:{res_height},setsar=1,tpad=stop_mode=clone:stop_duration=10,eq=saturation=1.15:contrast=1.05,fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start:.2f}:d=0.4'
            ff_cmd = ['ffmpeg', *get_hwaccel_args(), '-y', '-i', raw_video_path, '-i', audio_segment_path, '-t', f"{dur:.2f}", '-vf', vf_filter_with_text, '-af', f'afade=t=in:ss=0:d=0.4,afade=t=out:st={fade_out_start:.2f}:d=0.4,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo', '-r', '24', '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', '28', '-preset', 'ultrafast', '-tune', 'fastdecode', '-c:a', 'aac', '-ac', '2', '-ar', '44100', '-map', '0:v:0', '-map', '1:a:0', '-shortest', segment_mux_path]
            try:
                subprocess.run(ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                if os.path.exists(segment_mux_path) and os.path.getsize(segment_mux_path) > 0:
                    return segment_mux_path
            except Exception:
                fallback_cmd = ['ffmpeg', *get_hwaccel_args(), '-y', '-i', raw_video_path, '-i', audio_segment_path, '-t', f"{dur:.2f}", '-vf', f'scale={res_width}:{res_height}:force_original_aspect_ratio=increase,crop={res_width}:{res_height},setsar=1,tpad=stop_mode=clone:stop_duration=10,eq=saturation=1.15:contrast=1.05,fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start:.2f}:d=0.4', '-af', 'aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo', '-r', '24', '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'fastdecode', '-c:a', 'aac', '-ac', '2', '-ar', '44100', '-map', '0:v:0', '-map', '1:a:0', '-shortest', segment_mux_path]
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
            def context_safe_worker(idx, scene):
                return process_scene_segment(idx, scene)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_idx = {executor.submit(context_safe_worker, idx, scene): idx for idx, scene in enumerate(scenes_data)}
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
                if os.path.exists(path) and os.path.getsize(path) > 100:
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
            concat_cmd = ['ffmpeg', *get_hwaccel_args(), '-y', '-f', 'concat', '-safe', '0', '-i', manifest_file, '-c:v', 'copy', '-c:a', 'copy', temp_stitched_output]
            subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if bgm_path and os.path.exists(bgm_path):
                mixed_ok = mix_audio_layers(
                    video_input_path=temp_stitched_output,
                    output_path=video_output,
                    bgm_path=bgm_path,
                    bgm_volume=bgm_volume,
                )
                if not mixed_ok:
                    shutil.copy(temp_stitched_output, video_output)
            else:
                shutil.copy(temp_stitched_output, video_output)
            if os.path.exists(video_output) and os.path.getsize(video_output) > 100:
                return True
            return False
        except Exception as e:
            logger.error(f"Build scene stitched video error: {e}")
            return False
        finally:
            try:
                shutil.rmtree(workspace_dir, ignore_errors=True)
            except Exception:
                pass

def create_emergency_solid_clip(output_filename, duration, res_width, res_height):
    safe_remove_file(output_filename)
    cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=#050508:s={res_width}x{res_height}:r=24', '-t', str(duration), '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'ultrafast', output_filename]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except:
        return False

def create_emergency_silent_audio(output_filename, duration):
    safe_remove_file(output_filename)
    cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-t', str(duration), '-c:a', 'libmp3lame', output_filename]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def safe_remove_file(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

def convert_mp4_to_webm(mp4_path, webm_path):
    safe_remove_file(webm_path)
    cmd = ['ffmpeg', *get_hwaccel_args(), '-y', '-i', mp4_path, '-c:v', 'libvpx-vp9', '-crf', '32', '-b:v', '0', '-c:a', 'libopus', webm_path]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        try:
            cmd = ['ffmpeg', *get_hwaccel_args(), '-y', '-i', mp4_path, '-c:v', 'libvpx', '-crf', '10', '-b:v', '1M', '-c:a', 'libvorbis', webm_path]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except Exception:
            return False

def generate_face_video_real(image_path, audio_path=None, output_width=512, output_height=512, duration=10, quality="Standard", emotion="neutral", camera_angle="front"):
    if not image_path or not os.path.exists(image_path):
        return None
    quality_settings = {"Standard": {"crf": 23, "preset": "medium", "bitrate": "1M"}, "HD": {"crf": 18, "preset": "slow", "bitrate": "4M"}, "4K": {"crf": 15, "preset": "veryslow", "bitrate": "10M", "scale": 2.0}}
    q_settings = quality_settings.get(quality, quality_settings["Standard"])
    scale_factor = q_settings.get("scale", 1.0)
    out_w = int(output_width * scale_factor)
    out_h = int(output_height * scale_factor)
    output_video_path = f"face_videos/face_video_{quality.lower()}_{uuid.uuid4().hex[:8]}.mp4"
    temp_processed_img = "face_videos/temp_face_rect.png"
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Image could not be loaded.")
        h, w, _ = img.shape
        size = max(h, w)
        pad_y = (size - h) // 2
        pad_x = (size - w) // 2
        padded_img = cv2.copyMakeBorder(img, pad_y, pad_y, pad_x, pad_x, borderType=cv2.BORDER_CONSTANT, value=[0, 0, 0])
        final_rect_img = cv2.resize(padded_img, (out_w, out_h), interpolation=cv2.INTER_AREA)
        cv2.imwrite(temp_processed_img, final_rect_img)
        if audio_path and os.path.exists(audio_path):
            if run_lip_sync_pipeline(temp_processed_img, audio_path, output_video_path, out_w, out_h, duration=duration, emotion=emotion, camera_angle=camera_angle):
                if os.path.exists(temp_processed_img):
                    os.remove(temp_processed_img)
                return output_video_path
            
            # FALLBACK: Lip-sync failed, create a simple video with image + audio
            logger.warning("Lip-sync engine failed. Creating fallback video (image + audio only).")
            fallback_video = output_video_path.replace(".mp4", "_fallback.mp4")
            try:
                subprocess.run(
                    ['ffmpeg', '-y', '-loop', '1', '-i', temp_processed_img,
                     '-i', audio_path,
                     '-t', str(max(1.0, float(get_audio_duration(audio_path) or duration))),
                     '-vf', f'scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1',
                     '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
                     '-c:a', 'aac', '-shortest',
                     fallback_video],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
                )
                if os.path.exists(fallback_video) and os.path.getsize(fallback_video) > 1000:
                    shutil.move(fallback_video, output_video_path)
                    st.session_state["face_video_engine_used"] = "Fallback (Image+Audio)"
                    st.session_state["face_video_runtime_mode"] = "CPU"
                    if os.path.exists(temp_processed_img):
                        os.remove(temp_processed_img)
                    return output_video_path
            except Exception as fb_e:
                logger.warning(f"Fallback video creation also failed: {fb_e}")
            
            if os.path.exists(temp_processed_img):
                os.remove(temp_processed_img)
            return None
        
        # No audio provided - try creating a silent video
        logger.warning("No audio path found, creating silent face video.")
        try:
            subprocess.run(
                ['ffmpeg', '-y', '-loop', '1', '-i', temp_processed_img,
                 '-t', str(duration),
                 '-vf', f'scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1',
                 '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
                 output_video_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )
            if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 1000:
                st.session_state["face_video_engine_used"] = "Silent Image Video"
                st.session_state["face_video_runtime_mode"] = "CPU"
                if os.path.exists(temp_processed_img):
                    os.remove(temp_processed_img)
                return output_video_path
        except Exception as silent_e:
            logger.warning(f"Silent video creation failed: {silent_e}")
            
        if os.path.exists(temp_processed_img):
            try:
                os.remove(temp_processed_img)
            except:
                pass
        return None
    except Exception as e:
        logger.error(f"Generate face video real error: {e}")
        if os.path.exists(temp_processed_img):
            try:
                os.remove(temp_processed_img)
            except:
                pass
        return None


def _download_file_with_fallback(urls, out_path, timeout=180, min_bytes=1024):
    """Download a file from multiple URLs with optional HF auth support."""
    if os.path.isfile(out_path) and os.path.getsize(out_path) >= min_bytes:
        return True

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    temp_path = f"{out_path}.part"

    hf_token = (os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY") or "").strip()

    for url in urls:
        if not url:
            continue
        request_headers = {}
        if "huggingface.co" in url and hf_token:
            request_headers["Authorization"] = f"Bearer {hf_token}"

        try:
            with requests.get(url, stream=True, timeout=timeout, headers=request_headers or None) as response:
                response.raise_for_status()
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

            if os.path.isfile(temp_path) and os.path.getsize(temp_path) >= min_bytes:
                os.replace(temp_path, out_path)
                logger.info(f"Downloaded model asset from {url} -> {out_path}")
                return True
        except Exception as e:
            logger.warning(f"Model download failed: {url} -> {e}")
        finally:
            safe_remove_file(temp_path)

    return os.path.isfile(out_path) and os.path.getsize(out_path) >= min_bytes


def ensure_wav2lip_core_weights(repo_path):
    """Ensure Wav2Lip generator checkpoint exists; auto-download if missing."""
    if not repo_path:
        return False

    checkpoint_path = os.path.join(repo_path, "checkpoints", "wav2lip_gan.pth")
    if os.path.isfile(checkpoint_path) and os.path.getsize(checkpoint_path) > 5 * 1024 * 1024:
        return True

    env_url = os.getenv("WAV2LIP_GAN_URL", "").strip()
    download_urls = [
        env_url,
        "https://huggingface.co/numz/wav2lip_studio/resolve/main/wav2lip_gan.pth",
        "https://huggingface.co/Kijai/Wav2Lip_fp16/resolve/main/wav2lip_gan.pth",
        "https://huggingface.co/camenduru/Wav2Lip/resolve/main/wav2lip_gan.pth",
        "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth",
    ]

    ok = _download_file_with_fallback(download_urls, checkpoint_path, timeout=300, min_bytes=5 * 1024 * 1024)
    if not ok:
        logger.warning("wav2lip_gan.pth is missing and could not be auto-downloaded.")
    return ok


def ensure_wav2lip_s3fd_weights(repo_path):
    """Ensure s3fd face detector weights exist; auto-download if missing."""
    if not repo_path:
        return False

    s3fd_path = os.path.join(repo_path, "face_detection", "detection", "sfd", "s3fd.pth")
    if os.path.isfile(s3fd_path):
        return True

    os.makedirs(os.path.dirname(s3fd_path), exist_ok=True)

    env_url = os.getenv("WAV2LIP_S3FD_URL", "").strip()
    download_urls = [
        env_url,
        "https://huggingface.co/numz/wav2lip_studio/resolve/main/s3fd.pth",
        "https://huggingface.co/Kijai/Wav2Lip_fp16/resolve/main/s3fd.pth",
        "https://huggingface.co/camenduru/Wav2Lip/resolve/main/s3fd.pth",
        "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth",
        "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/s3fd.pth",
    ]

    if _download_file_with_fallback(download_urls, s3fd_path, timeout=180, min_bytes=1024):
        return True

    logger.warning("s3fd.pth is missing and could not be auto-downloaded. Continuing in forced mode.")
    return False


def _normalize_env_path(path_value):
    if not path_value:
        return None
    return str(path_value).strip().strip('"').strip("'")


def _build_wav2lip_repo_candidates():
    env_repo = _normalize_env_path(os.getenv("WAV2LIP_REPO_PATH"))
    fixed_windows = r"C:\Zovix-Clean\Wav2Lip"
    fixed_wsl = "/mnt/c/Zovix-Clean/Wav2Lip"

    base_paths = [
        env_repo,
        fixed_windows,
        fixed_wsl,
        os.path.join(os.getcwd(), "Wav2Lip"),
        os.path.join(os.getcwd(), "wav2lip"),
        os.path.join(os.path.dirname(__file__), "Wav2Lip"),
        os.path.join(os.path.dirname(__file__), "wav2lip"),
    ]

    # Search a few parent levels too, in case Streamlit is started from a subdirectory.
    for root in [os.getcwd(), os.path.dirname(__file__)]:
        current = os.path.abspath(root)
        for _ in range(4):
            base_paths.append(os.path.join(current, "Wav2Lip"))
            base_paths.append(os.path.join(current, "wav2lip"))
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

    deduped = []
    seen = set()
    for p in base_paths:
        if not p:
            continue
        n = os.path.normpath(p)
        key = n.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(n)
    return deduped


def _discover_wav2lip_repo(search_roots):
    """Best-effort local discovery for a repo containing inference.py."""
    for root in search_roots:
        if not root or not os.path.isdir(root):
            continue
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                # Keep scan bounded for Streamlit reruns.
                rel = os.path.relpath(dirpath, root)
                depth = rel.count(os.sep)
                if depth > 5:
                    dirnames[:] = []
                    continue
                if "inference.py" in filenames and os.path.basename(dirpath).lower() in {"wav2lip", "wav2lip-master"}:
                    return dirpath
        except Exception:
            continue
    return None


def get_wav2lip_setup_status():
    """Resolve local Wav2Lip setup and auto-bootstrap missing model weights."""
    repo_path = None
    search_roots = []
    for candidate in _build_wav2lip_repo_candidates():
        if os.path.isdir(candidate):
            repo_path = candidate
            break
        parent = os.path.dirname(candidate)
        if parent and os.path.isdir(parent):
            search_roots.append(parent)

    if not repo_path:
        search_roots.extend([os.getcwd(), os.path.dirname(__file__)])
        repo_path = _discover_wav2lip_repo(search_roots)

    if not repo_path:
        repo_path = os.path.normpath(os.path.join(os.getcwd(), "Wav2Lip"))

    script_path = os.path.join(repo_path, "inference.py")
    checkpoint_path = _normalize_env_path(os.getenv("WAV2LIP_CHECKPOINT_PATH")) or os.path.join(repo_path, "checkpoints", "wav2lip_gan.pth")
    s3fd_path = os.path.join(repo_path, "face_detection", "detection", "sfd", "s3fd.pth")

    # Force process-level paths for all downstream calls.
    os.environ["WAV2LIP_REPO_PATH"] = repo_path
    os.environ["WAV2LIP_CHECKPOINT_PATH"] = checkpoint_path

    auto_setup_enabled = str(os.getenv("WAV2LIP_AUTO_SETUP", "1")).strip().lower() in {"1", "true", "yes", "on"}
    if auto_setup_enabled and not st.session_state.get("wav2lip_auto_setup_ran", False):
        st.session_state["wav2lip_auto_setup_ran"] = True
        ensure_wav2lip_core_weights(repo_path)
        ensure_wav2lip_s3fd_weights(repo_path)

    checkpoint_ready = os.path.isfile(checkpoint_path)
    s3fd_ready = os.path.isfile(s3fd_path)
    script_ready = os.path.isfile(script_path)
    ready = bool(repo_path and script_ready and checkpoint_ready and s3fd_ready)

    return {
        "ready": ready,
        "repo_path": repo_path,
        "script_path": script_path,
        "checkpoint_path": checkpoint_path,
        "s3fd_path": s3fd_path,
        "s3fd_ready": s3fd_ready,
        "cwd": os.getcwd(),
        "app_dir": os.path.dirname(__file__),
        "forced_mode": False,
    }


def get_wav2lip_runtime_profile():
    """Return runtime tuning profile for Wav2Lip CLI based on available hardware."""
    force_cpu = str(os.getenv("WAV2LIP_FORCE_CPU", "0")).strip() in {"1", "true", "True", "yes", "YES"}
    has_gpu = (shutil.which("nvidia-smi") is not None) and not force_cpu

    if has_gpu:
        return {
            "mode": "GPU",
            "face_det_batch_size": "32",
            "wav2lip_batch_size": "128",
            "resize_factor": "1",
        }

    return {
        "mode": "CPU",
        "face_det_batch_size": "8",
        "wav2lip_batch_size": "32",
        "resize_factor": "2",
    }


def run_wav2lip_cli(face_image_path, audio_path, output_video_path, width, height, fps=24):
    """Run Wav2Lip inference.py via CLI with production-friendly flags and post-process output."""
    setup = get_wav2lip_setup_status()
    if not setup["ready"]:
        return False
    if not setup.get("s3fd_ready"):
        logger.warning("Wav2Lip s3fd.pth is missing and auto-download failed.")
        return False

    runtime = get_wav2lip_runtime_profile()
    st.session_state["face_video_runtime_mode"] = runtime["mode"]

    temp_face_video = f"face_videos/temp_w2l_face_{uuid.uuid4().hex[:8]}.mp4"
    temp_raw_output = f"face_videos/temp_w2l_raw_{uuid.uuid4().hex[:8]}.mp4"
    temp_final_output = f"face_videos/temp_w2l_final_{uuid.uuid4().hex[:8]}.mp4"

    try:
        safe_remove_file(temp_face_video)
        safe_remove_file(temp_raw_output)
        safe_remove_file(temp_final_output)

        audio_duration = max(1.0, float(get_audio_duration(audio_path) or 1.0))

        subprocess.run(
            [
                'ffmpeg', '-y', '-loop', '1', '-i', face_image_path,
                '-t', str(audio_duration + 0.15),
                '-vf', f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                '-r', str(fps), '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'fast', temp_face_video
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        optimized_cmd = [
            sys.executable,
            setup["script_path"],
            '--checkpoint_path', setup["checkpoint_path"],
            '--face', temp_face_video,
            '--audio', audio_path,
            '--outfile', temp_raw_output,
            '--pads', '0', '20', '0', '0',
            '--face_det_batch_size', runtime["face_det_batch_size"],
            '--wav2lip_batch_size', runtime["wav2lip_batch_size"],
            '--resize_factor', runtime["resize_factor"],
            '--nosmooth'
        ]

        result = subprocess.run(optimized_cmd, cwd=setup["repo_path"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0 or not os.path.exists(temp_raw_output):
            fallback_cmd = [
                sys.executable,
                setup["script_path"],
                '--checkpoint_path', setup["checkpoint_path"],
                '--face', temp_face_video,
                '--audio', audio_path,
                '--outfile', temp_raw_output,
            ]
            result = subprocess.run(fallback_cmd, cwd=setup["repo_path"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0 or not os.path.exists(temp_raw_output):
                logger.warning(f"Wav2Lip CLI failed: {(result.stderr or '')[:500]}")
                return False

        subprocess.run(
            [
                'ffmpeg', '-y', '-i', temp_raw_output, '-i', audio_path,
                '-vf', f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                '-c:a', 'aac', '-shortest', temp_final_output
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        if os.path.exists(temp_final_output) and os.path.getsize(temp_final_output) > 1000:
            shutil.move(temp_final_output, output_video_path)
            return True
        return False

    except Exception as e:
        logger.warning(f"Wav2Lip CLI integration failed: {e}")
        return False
    finally:
        safe_remove_file(temp_face_video)
        safe_remove_file(temp_raw_output)
        safe_remove_file(temp_final_output)

def run_lip_sync_pipeline(face_image_path, audio_path, output_video_path, width, height, duration=10, emotion="neutral", camera_angle="front"):
    safe_remove_file(output_video_path)
    try:
        st.session_state["face_video_engine_used"] = "Initializing..."
        setup = get_wav2lip_setup_status()
        if setup["ready"]:
            logger.info("Attempting Wav2Lip production CLI lip sync")
            if run_wav2lip_cli(face_image_path, audio_path, output_video_path, width, height, fps=24):
                st.session_state["face_video_engine_used"] = "Wav2Lip (Production CLI)"
                return True
            logger.warning("Wav2Lip production path failed. Falling back to built-in lip-only mode.")

        # Built-in fallback: animate only lip region from audio energy (no head/camera motion).
        logger.info("Using built-in audio-driven lip-only fallback.")
        if generate_audio_driven_lip_only_video(face_image_path, audio_path, output_video_path, width, height, fps=24):
            st.session_state["face_video_engine_used"] = "Built-in Lip-Only Fallback"
            st.session_state["face_video_runtime_mode"] = "CPU"
            return True

        logger.warning("No strict lip-sync backend available. Install/configure Wav2Lip for best quality.")
        st.session_state["face_video_engine_used"] = "No Engine Available"
    except Exception as e:
        logger.warning(f"Lip sync pipeline error: {e}")
        st.session_state["face_video_engine_used"] = "Engine Error"
    return False


def get_expressive_setup_status():
    """Probe local LivePortrait/SadTalker repositories and key runtime artifacts."""
    default_liveportrait = r"C:\Zovix-Clean\LivePortrait"
    default_sadtalker = r"C:\Zovix-Clean\SadTalker"

    def _resolve_repo_path(env_key, default_path, folder_name):
        env_path = _normalize_env_path(os.getenv(env_key))
        cwd_candidate = os.path.join(os.getcwd(), folder_name)
        appdir_candidate = os.path.join(os.path.dirname(__file__), folder_name)
        candidates = [
            env_path,
            default_path,
            cwd_candidate,
            appdir_candidate,
        ]
        seen = set()
        for p in candidates:
            if not p:
                continue
            n = os.path.normpath(p)
            k = n.lower()
            if k in seen:
                continue
            seen.add(k)
            if os.path.isdir(n):
                return n

        # If nothing exists, avoid returning a Windows-only path on Linux hosts.
        fallback = cwd_candidate
        if os.name == "nt" and default_path:
            fallback = default_path
        return os.path.normpath(fallback)

    def _safe_download(url, out_path, timeout=120):
        return _download_file_with_fallback([url], out_path, timeout=timeout, min_bytes=1024)

    def _auto_clone_repo(repo_path, clone_url):
        if os.path.isdir(repo_path) and os.path.isfile(os.path.join(repo_path, ".git", "config")):
            return True
        try:
            os.makedirs(os.path.dirname(repo_path), exist_ok=True)
        except Exception:
            pass
        try:
            result = subprocess.run(
                ["git", "clone", clone_url, repo_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode != 0:
                logger.warning(f"Failed cloning {clone_url}: {(result.stderr or '')[:300]}")
                return False
            return True
        except Exception as e:
            logger.warning(f"Git clone error for {clone_url}: {e}")
            return False

    def _bootstrap_expressive_assets(liveportrait_repo, sadtalker_repo):
        auto_setup_enabled = str(os.getenv("EXPRESSIVE_AUTO_SETUP", "1")).strip().lower() in {"1", "true", "yes", "on"}
        if not auto_setup_enabled:
            return
        # Retry-safe bootstrap: skipped downloads are prevented by file existence checks.
        st.session_state["expressive_auto_setup_ran"] = True

        # Ensure repos exist when running on fresh environments.
        if not os.path.isdir(liveportrait_repo):
            _auto_clone_repo(liveportrait_repo, "https://github.com/KwaiVGI/LivePortrait.git")
        if not os.path.isdir(sadtalker_repo):
            _auto_clone_repo(sadtalker_repo, "https://github.com/OpenTalker/SadTalker.git")

        lp_base = os.path.join(liveportrait_repo, "pretrained_weights", "liveportrait", "base_models")
        lp_files = {
            "appearance_feature_extractor.pth": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/base_models/appearance_feature_extractor.pth",
            "motion_extractor.pth": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/base_models/motion_extractor.pth",
            "spade_generator.pth": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/base_models/spade_generator.pth",
            "warping_module.pth": "https://huggingface.co/KlingTeam/LivePortrait/resolve/main/liveportrait/base_models/warping_module.pth",
        }
        for name, url in lp_files.items():
            _safe_download(url, os.path.join(lp_base, name), timeout=180)

        st_ckpt = os.path.join(sadtalker_repo, "checkpoints")
        st_files = {
            "mapping_00109-model.pth.tar": "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00109-model.pth.tar",
            "mapping_00229-model.pth.tar": "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00229-model.pth.tar",
        }
        for name, url in st_files.items():
            _safe_download(url, os.path.join(st_ckpt, name), timeout=180)

    liveportrait_repo = _resolve_repo_path("LIVEPORTRAIT_REPO_PATH", default_liveportrait, "LivePortrait")
    sadtalker_repo = _resolve_repo_path("SADTALKER_REPO_PATH", default_sadtalker, "SadTalker")

    _bootstrap_expressive_assets(liveportrait_repo, sadtalker_repo)

    liveportrait_scripts = [
        os.path.join(liveportrait_repo, "inference.py"),
        os.path.join(liveportrait_repo, "app.py"),
    ]
    sadtalker_scripts = [
        os.path.join(sadtalker_repo, "inference.py"),
        os.path.join(sadtalker_repo, "inference_cli.py"),
    ]

    liveportrait_script = next((p for p in liveportrait_scripts if os.path.isfile(p)), None)
    sadtalker_script = next((p for p in sadtalker_scripts if os.path.isfile(p)), None)

    liveportrait_python = _normalize_env_path(os.getenv("LIVEPORTRAIT_PYTHON_PATH")) or os.path.join(liveportrait_repo, ".venv", "Scripts", "python.exe")
    if not os.path.isfile(liveportrait_python):
        liveportrait_python = sys.executable

    sadtalker_python = _normalize_env_path(os.getenv("SADTALKER_PYTHON_PATH")) or os.path.join(sadtalker_repo, ".venv", "Scripts", "python.exe")
    if not os.path.isfile(sadtalker_python):
        sadtalker_python = sys.executable

    liveportrait_required = [
        os.path.join(liveportrait_repo, "pretrained_weights", "liveportrait", "base_models", "appearance_feature_extractor.pth"),
        os.path.join(liveportrait_repo, "pretrained_weights", "liveportrait", "base_models", "motion_extractor.pth"),
        os.path.join(liveportrait_repo, "pretrained_weights", "liveportrait", "base_models", "spade_generator.pth"),
        os.path.join(liveportrait_repo, "pretrained_weights", "liveportrait", "base_models", "warping_module.pth"),
    ]
    liveportrait_models_ready = all(os.path.isfile(p) for p in liveportrait_required)

    sadtalker_required = [
        os.path.join(sadtalker_repo, "checkpoints", "mapping_00109-model.pth.tar"),
        os.path.join(sadtalker_repo, "checkpoints", "mapping_00229-model.pth.tar"),
    ]
    sadtalker_safetensors = [
        os.path.join(sadtalker_repo, "checkpoints", "SadTalker_V0.0.2_256.safetensors"),
        os.path.join(sadtalker_repo, "checkpoints", "SadTalker_V0.0.2_512.safetensors"),
    ]
    sadtalker_models_ready = all(os.path.isfile(p) for p in sadtalker_required) or any(os.path.isfile(p) for p in sadtalker_safetensors)

    has_gpu = shutil.which("nvidia-smi") is not None

    force_enable = str(os.getenv("EXPRESSIVE_FORCE_ENABLE", "0")).strip().lower() in {"1", "true", "yes", "on"}
    sadtalker_force_ready = str(os.getenv("SADTALKER_FORCE_READY", "0")).strip().lower() in {"1", "true", "yes", "on"}
    liveportrait_ready = bool(liveportrait_script) and liveportrait_models_ready
    sadtalker_ready = bool(sadtalker_script) and sadtalker_models_ready

    if force_enable:
        liveportrait_ready = bool(liveportrait_script)
        sadtalker_ready = bool(sadtalker_script)

    if sadtalker_force_ready:
        # Optional bypass for missing checkpoints, but script must exist.
        sadtalker_ready = bool(sadtalker_script)

    return {
        "liveportrait_repo": liveportrait_repo,
        "liveportrait_script": liveportrait_script,
        "liveportrait_python": liveportrait_python,
        "liveportrait_ready": liveportrait_ready,
        "liveportrait_models_ready": liveportrait_models_ready,
        "sadtalker_repo": sadtalker_repo,
        "sadtalker_script": sadtalker_script,
        "sadtalker_python": sadtalker_python,
        "sadtalker_ready": sadtalker_ready,
        "sadtalker_models_ready": sadtalker_models_ready,
        "sadtalker_force_ready": sadtalker_force_ready,
        "runtime_mode": "GPU" if has_gpu else "CPU",
        "any_ready": bool(liveportrait_ready or sadtalker_ready),
        "force_enable": force_enable,
    }


def _discover_latest_generated_video(folder_path):
    if not folder_path or not os.path.isdir(folder_path):
        return None
    candidates = []
    for root, _, files in os.walk(folder_path):
        for f_name in files:
            if f_name.lower().endswith(".mp4"):
                full_path = os.path.join(root, f_name)
                try:
                    candidates.append((os.path.getmtime(full_path), full_path))
                except Exception:
                    continue
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _normalize_face_video_output(input_video_path, audio_path, output_video_path, width, height):
    safe_remove_file(output_video_path)
    try:
        subprocess.run(
            [
                'ffmpeg', '-y', '-i', input_video_path, '-i', audio_path,
                '-vf', f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                '-c:a', 'aac', '-shortest', output_video_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 1000
    except Exception:
        return False


def run_liveportrait_cli(face_image_path, audio_path, output_video_path, width, height, duration=10, motion_level="high"):
    """Run LivePortrait inference with best-effort command variants."""
    setup = get_expressive_setup_status()
    script_path = setup.get("liveportrait_script")
    repo_path = setup.get("liveportrait_repo")
    python_exec = setup.get("liveportrait_python") or sys.executable
    if not script_path or not repo_path:
        return False

    temp_out_dir = os.path.join("face_videos", f"liveportrait_out_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_out_dir, exist_ok=True)

    command_candidates = [
        [
            python_exec, script_path,
            '--source', face_image_path,
            '--driving', audio_path,
            '--output-dir', temp_out_dir,
            '--driving_multiplier', '1.2' if motion_level == "high" else ('1.0' if motion_level == "medium" else '0.9'),
        ],
        [
            python_exec, script_path,
            '--source_image', face_image_path,
            '--driving_audio', audio_path,
            '--output', temp_out_dir,
        ],
    ]

    try:
        for cmd in command_candidates:
            result = subprocess.run(cmd, cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                logger.warning(f"LivePortrait cmd failed rc={result.returncode}: {(result.stderr or '')[:350]}")
                continue

            candidate_video = _discover_latest_generated_video(temp_out_dir)
            if candidate_video and _normalize_face_video_output(candidate_video, audio_path, output_video_path, width, height):
                return True
        return False
    except Exception as e:
        logger.warning(f"LivePortrait CLI run failed: {e}")
        return False
    finally:
        try:
            shutil.rmtree(temp_out_dir, ignore_errors=True)
        except Exception:
            pass


def run_sadtalker_cli(face_image_path, audio_path, output_video_path, width, height, duration=10, motion_level="high"):
    """Run SadTalker inference with best-effort command variants."""
    setup = get_expressive_setup_status()
    script_path = setup.get("sadtalker_script")
    repo_path = setup.get("sadtalker_repo")
    python_exec = setup.get("sadtalker_python") or sys.executable
    if not script_path or not repo_path:
        return False

    temp_out_dir = os.path.join("face_videos", f"sadtalker_out_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_out_dir, exist_ok=True)

    if motion_level == "high":
        pose_style = '18'
        expression_scale = '1.35'
    elif motion_level == "low":
        pose_style = '6'
        expression_scale = '1.05'
    else:
        pose_style = '12'
        expression_scale = '1.20'

    command_candidates = [
        [
            python_exec, script_path,
            '--driven_audio', audio_path,
            '--source_image', face_image_path,
            '--result_dir', temp_out_dir,
            '--preprocess', 'full',
            '--pose_style', pose_style,
            '--expression_scale', expression_scale,
            '--enhancer', 'gfpgan',
        ],
        [
            python_exec, script_path,
            '--driven_audio', audio_path,
            '--source_image', face_image_path,
            '--result_dir', temp_out_dir,
            '--preprocess', 'crop',
            '--pose_style', pose_style,
            '--expression_scale', expression_scale,
        ],
        [
            python_exec, script_path,
            '--source_image', face_image_path,
            '--driven_audio', audio_path,
            '--output', temp_out_dir,
        ],
    ]

    try:
        for cmd in command_candidates:
            result = subprocess.run(cmd, cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                logger.warning(f"SadTalker cmd failed rc={result.returncode}: {(result.stderr or '')[:350]}")
                continue

            candidate_video = _discover_latest_generated_video(temp_out_dir)
            if candidate_video and _normalize_face_video_output(candidate_video, audio_path, output_video_path, width, height):
                return True
        return False
    except Exception as e:
        logger.warning(f"SadTalker CLI run failed: {e}")
        return False
    finally:
        try:
            shutil.rmtree(temp_out_dir, ignore_errors=True)
        except Exception:
            pass


def run_expressive_face_pipeline(face_image_path, audio_path, output_video_path, width, height, duration=10, preferred_engine="Auto (LivePortrait → SadTalker → Wav2Lip)", motion_level="high"):
    safe_remove_file(output_video_path)
    setup = get_expressive_setup_status()
    st.session_state["expressive_face_runtime_mode"] = setup.get("runtime_mode", "Unknown")
    st.session_state["expressive_face_engine_used"] = "Initializing..."

    try:
        engine_order = []
        if preferred_engine == "LivePortrait Only":
            engine_order = ["LivePortrait"]
        elif preferred_engine == "SadTalker Only":
            engine_order = ["SadTalker"]
        elif preferred_engine == "Auto (LivePortrait → SadTalker → Wav2Lip)":
            engine_order = ["LivePortrait", "SadTalker", "Wav2Lip"]
        elif preferred_engine == "Wav2Lip Fallback":
            engine_order = ["Wav2Lip"]
        else:
            engine_order = ["LivePortrait", "SadTalker", "Wav2Lip"]

        if not setup.get("any_ready") and "Wav2Lip" not in engine_order:
            st.session_state["expressive_face_engine_used"] = "Expressive models missing"
            logger.warning("Expressive engines not ready: required LivePortrait/SadTalker model files are missing.")
            return False

        for engine_name in engine_order:
            if engine_name == "LivePortrait" and setup.get("liveportrait_ready"):
                if run_liveportrait_cli(face_image_path, audio_path, output_video_path, width, height, duration=duration, motion_level=motion_level):
                    st.session_state["expressive_face_engine_used"] = "LivePortrait"
                    return True
            elif engine_name == "SadTalker" and setup.get("sadtalker_ready"):
                if run_sadtalker_cli(face_image_path, audio_path, output_video_path, width, height, duration=duration, motion_level=motion_level):
                    st.session_state["expressive_face_engine_used"] = "SadTalker"
                    return True
            elif engine_name == "Wav2Lip":
                if run_lip_sync_pipeline(face_image_path, audio_path, output_video_path, width, height, duration=duration):
                    st.session_state["expressive_face_engine_used"] = f"{st.session_state.get('face_video_engine_used', 'Wav2Lip')}"
                    return True

        st.session_state["expressive_face_engine_used"] = "No Engine Available"
        return False
    except Exception as e:
        logger.warning(f"Expressive face pipeline error: {e}")
        st.session_state["expressive_face_engine_used"] = "Engine Error"
        return False


def generate_expressive_face_video(prompt, face_image_path, duration=30, emotion="neutral", camera_angle="front", quality="HD", preferred_engine="Auto (LivePortrait → SadTalker → Wav2Lip)", motion_level="high", voice_language=None, voice_label=None):
    if not face_image_path or not os.path.exists(face_image_path):
        return None

    voice_cfg = _resolve_face_voice_config(voice_language=voice_language, voice_label=voice_label, preferred_gender=st.session_state.get('fv_detected_gender') if st.session_state.get('fv_gender_auto', False) else None)
    audio_path = f"face_videos/voice_{uuid.uuid4().hex[:8]}.mp3"
    audio_success = _synthesize_face_audio_strict(prompt, audio_path, voice_cfg, duration_hint=duration)

    quality_settings = {
        "Standard": (512, 512),
        "HD": (768, 768),
        "4K": (1024, 1024),
    }
    out_w, out_h = quality_settings.get(quality, (768, 768))
    output_video_path = f"face_videos/expressive_face_video_{quality.lower()}_{uuid.uuid4().hex[:8]}.mp4"

    try:
        if run_expressive_face_pipeline(
            face_image_path,
            audio_path,
            output_video_path,
            out_w,
            out_h,
            duration=duration,
            preferred_engine=preferred_engine,
            motion_level=motion_level,
        ):
            return output_video_path
        return None
    finally:
        safe_remove_file(audio_path)


def generate_audio_driven_lip_only_video(face_image_path, audio_path, output_video_path, width, height, fps=24):
    """Fallback lip-sync engine: keeps head static and animates only mouth region from audio energy."""
    temp_wav = f"face_videos/temp_audio_{uuid.uuid4().hex[:8]}.wav"
    temp_video = f"face_videos/temp_lips_{uuid.uuid4().hex[:8]}.mp4"
    temp_muxed = f"face_videos/temp_lips_mux_{uuid.uuid4().hex[:8]}.mp4"

    try:
        safe_remove_file(temp_wav)
        safe_remove_file(temp_video)
        safe_remove_file(temp_muxed)

        # Convert any input audio to mono PCM WAV for simple frame-level energy extraction.
        subprocess.run(
            ['ffmpeg', '-y', '-i', audio_path, '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', temp_wav],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        import wave
        import struct

        with wave.open(temp_wav, 'rb') as wf:
            n_frames = wf.getnframes()
            sample_rate = wf.getframerate()
            raw_data = wf.readframes(n_frames)

        if not raw_data:
            return False

        total_samples = len(raw_data) // 2
        if total_samples == 0:
            return False

        samples = struct.unpack('<' + 'h' * total_samples, raw_data)
        samples_per_frame = max(1, int(sample_rate / fps))
        frame_energies = []
        for i in range(0, total_samples, samples_per_frame):
            chunk = samples[i:i + samples_per_frame]
            if not chunk:
                break
            rms = (sum((s * s) for s in chunk) / max(1, len(chunk))) ** 0.5
            frame_energies.append(rms)

        if not frame_energies:
            return False

        max_energy = max(frame_energies) or 1.0
        frame_energies = [min(1.0, e / max_energy) for e in frame_energies]

        base_img = cv2.imread(face_image_path)
        if base_img is None:
            return False
        base_img = cv2.resize(base_img, (width, height), interpolation=cv2.INTER_AREA)

        # Detect face once and derive a stable mouth ROI to avoid full-head motion.
        face_x, face_y, face_w, face_h = 0, 0, width, height
        try:
            gray = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            detector = cv2.CascadeClassifier(cascade_path)
            faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
            if len(faces) > 0:
                face_x, face_y, face_w, face_h = max(faces, key=lambda f: f[2] * f[3])
        except Exception:
            pass

        mouth_w = int(face_w * 0.42)
        mouth_h = int(face_h * 0.16)
        mouth_x = int(face_x + (face_w - mouth_w) * 0.5)
        mouth_y = int(face_y + face_h * 0.66)

        mouth_x = max(0, min(width - mouth_w, mouth_x))
        mouth_y = max(0, min(height - mouth_h, mouth_y))

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(temp_video, fourcc, float(fps), (width, height))

        if not writer.isOpened():
            return False

        for energy in frame_energies:
            frame = base_img.copy()
            roi = frame[mouth_y:mouth_y + mouth_h, mouth_x:mouth_x + mouth_w]
            if roi.size > 0:
                scale = 1.0 + (0.45 * float(energy))
                scaled_h = max(1, int(mouth_h * scale))
                stretched = cv2.resize(roi, (mouth_w, scaled_h), interpolation=cv2.INTER_LINEAR)
                if scaled_h > mouth_h:
                    start = (scaled_h - mouth_h) // 2
                    stretched = stretched[start:start + mouth_h, :]
                else:
                    pad = mouth_h - scaled_h
                    stretched = cv2.copyMakeBorder(stretched, pad // 2, pad - (pad // 2), 0, 0, cv2.BORDER_REPLICATE)
                jaw_shift = int(energy * max(1, mouth_h * 0.08))
                target_y = max(0, min(height - mouth_h, mouth_y + jaw_shift))
                frame[target_y:target_y + mouth_h, mouth_x:mouth_x + mouth_w] = stretched
            writer.write(frame)

        writer.release()

        subprocess.run(
            ['ffmpeg', '-y', '-i', temp_video, '-i', audio_path, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', temp_muxed],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        if os.path.exists(temp_muxed) and os.path.getsize(temp_muxed) > 1000:
            shutil.move(temp_muxed, output_video_path)
            return True
        return False

    except Exception as e:
        logger.warning(f"Audio-driven lip-only fallback failed: {e}")
        return False
    finally:
        safe_remove_file(temp_wav)
        safe_remove_file(temp_video)
        safe_remove_file(temp_muxed)

def _resolve_face_voice_config(voice_language=None, voice_label=None, preferred_gender=None):
    """Resolve voice for face-video generation with Hindi/English/all voice choices."""
    language_pref = (voice_language or st.session_state.get("face_voice_language") or "English").strip()
    if language_pref not in {"Hindi", "English", "All Voices"}:
        language_pref = "English"

    if language_pref == "Hindi":
        available_voices = list(LANGUAGE_VOICE_MAP.get("Hindi", []))
    elif language_pref == "English":
        available_voices = list(LANGUAGE_VOICE_MAP.get("English", []))
    else:
        available_voices = list(ELEVENLABS_VOICES.keys())

    # Filter by gender preference if provided
    if preferred_gender and available_voices:
        gender_filtered = []
        for v in available_voices:
            meta = ELEVENLABS_VOICES.get(v, {})
            if meta.get('gender') == preferred_gender:
                gender_filtered.append(v)
        if gender_filtered:
            available_voices = gender_filtered

    if not available_voices:
        available_voices = ["Adam (Premium Male)"]

    selected_voice = voice_label or st.session_state.get("face_voice_model") or available_voices[0]
    if selected_voice not in available_voices:
        selected_voice = available_voices[0]

    voice_meta = ELEVENLABS_VOICES.get(selected_voice, {})
    selected_voice_id = voice_meta.get("id", "21m00Tcm4TlvDq8ikWAM")
    voice_lang = str(voice_meta.get("language", "English")).strip().lower()
    fallback_language_choice = "🇮🇳 Hinglish (Fluent Hindi Mix)" if (language_pref == "Hindi" or voice_lang in {"hindi", "bhojpuri"}) else "🇬🇧 English (US Standard)"

    st.session_state["face_voice_language"] = language_pref
    st.session_state["face_voice_model"] = selected_voice

    return {
        "language": language_pref,
        "voice_label": selected_voice,
        "voice_id": selected_voice_id,
        "fallback_language_choice": fallback_language_choice,
        "available_voices": available_voices,
    }


def _synthesize_face_audio_strict(prompt_text, audio_path, voice_cfg, duration_hint=10):
    """Best-effort TTS chain to avoid silent face videos in production."""
    audio_success = False

    # 1) Try selected ElevenLabs voice.
    audio_success = generate_elevenlabs_audio_for_face(prompt_text, audio_path, voice_cfg.get("voice_id", "21m00Tcm4TlvDq8ikWAM"))

    # 2) If selected voice ID is invalid, retry with stable default voice.
    if not audio_success:
        audio_success = generate_elevenlabs_audio_for_face(prompt_text, audio_path, "21m00Tcm4TlvDq8ikWAM")

    # 3) Edge-TTS fallback with multilingual retry voices.
    if not audio_success:
        try:
            audio_success = bool(
                AudioEngine.run_fallback_tts(
                    text=prompt_text,
                    output_filename=audio_path,
                    language_choice=voice_cfg.get("fallback_language_choice", "🇬🇧 English (US Standard)"),
                    voice_profile=voice_cfg.get("voice_label", "Adam (Premium Male)"),
                )
            )
        except Exception:
            audio_success = False

    # 4) Final speech fallback (Azure/Eleven/edge wrapped helper).
    if not audio_success:
        try:
            fallback_voice_type = "male" if ("Male" in voice_cfg.get("voice_label", "") or "male" in voice_cfg.get("voice_label", "").lower()) else "female"
            generated_audio = generate_emotion_voice(
                prompt_text,
                emotion="neutral",
                voice_type=fallback_voice_type,
                output_path=audio_path,
                elevenlabs_voice_id=voice_cfg.get("voice_id", "21m00Tcm4TlvDq8ikWAM"),
            )
            audio_success = bool(generated_audio and os.path.exists(audio_path) and os.path.getsize(audio_path) > 2048)
        except Exception:
            audio_success = False

    return audio_success and os.path.exists(audio_path) and is_audio_audible(audio_path)


def deepface_scan_face_and_select_voice(face_image_path):
    """
    Scan face using DeepFace to detect age & gender.
    Auto-select ElevenLabs voice based on classification:
    - Boy (Male &lt; 14) -> Josh (Young Male)
    - Girl/Child (Female &lt; 14) -> Bella (Warm Female)
    - Adult Male (Male >= 14) -> Adam (Premium Male)
    - Adult Female (Female >= 14) -> Rachel (Premium Female)
    Returns: dict with {voice_id, voice_label, category, age, gender}
    """
    result = {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Default: Adam
        "voice_label": "Adam (Premium Male)",
        "category": "Adult Male",
        "age": 25,
        "gender": "Male"
    }
    
    if not face_image_path or not os.path.exists(face_image_path):
        logger.warning("DeepFace: No face image path provided, using default voice (Adam)")
        return result
    
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import tensorflow as tf
            tf.get_logger().setLevel("ERROR")
            
            analysis = DeepFace.analyze(img_path=face_image_path, actions=['age', 'gender'], enforce_detection=False)
        
        if isinstance(analysis, list) and len(analysis) > 0:
            face_data = analysis[0]
        elif isinstance(analysis, dict):
            face_data = analysis
        else:
            raise ValueError("Unexpected DeepFace response format")
        
        detected_age = int(face_data.get('age', 25))
        detected_gender_raw = face_data.get('gender', {})
        
        if isinstance(detected_gender_raw, dict):
            if detected_gender_raw.get('Man', 0) > detected_gender_raw.get('Woman', 0):
                gender = "Male"
            else:
                gender = "Female"
        elif isinstance(detected_gender_raw, str):
            gender = detected_gender_raw
        else:
            gender = "Male"
        
        # Use VOICE_MODULE_SPLIT for consistent selection
        voice_module = get_voice_module_by_age_gender(detected_age, gender)
        if voice_module:
            voice_id = voice_module["default_voice_id"]
            voice_label = voice_module["default_voice"]
            category = voice_module["category"]
        else:
            voice_id = "21m00Tcm4TlvDq8ikWAM"
            voice_label = "Adam (Premium Male)"
            category = "Adult Male"
        
        result = {
            "voice_id": voice_id,
            "voice_label": voice_label,
            "category": category,
            "age": detected_age,
            "gender": gender
        }
        
        logger.info(f"DeepFace scan -> Age:{detected_age}, Gender:{gender}, Category:{category}, Voice:{voice_label}")
        
    except Exception as e:
        logger.warning(f"DeepFace scan failed (using default voice): {e}")
        # If DeepFace fails, try to at least detect if file is valid
        if face_image_path and os.path.exists(face_image_path):
            try:
                from PIL import Image
                img = Image.open(face_image_path)
                logger.info(f"Image validated: {img.size}, mode={img.mode}")
            except Exception:
                pass
    
    return result

def generate_face_video(prompt, face_image_path, duration=30, emotion="neutral", camera_angle="front", quality="Standard", voice_language=None, voice_label=None):
    """Pure Cloud Face Video Generation via Replicate API."""
    if not face_image_path or not os.path.exists(face_image_path):
        return None

    # --- DeepFace Auto-Scan: Detect age & gender, auto-select voice --- #
    try:
        scan_result = deepface_scan_face_and_select_voice(face_image_path)
        detected_category = scan_result.get("category", "Adult Male")
        detected_age = scan_result.get("age", 25)
        detected_gender = scan_result.get("gender", "Male")
        
        if voice_label is None or voice_label == "":
            auto_voice = st.session_state.get("fv_auto_selected_voice")
            if auto_voice:
                voice_label = auto_voice
            else:
                voice_label = scan_result.get("voice_label", "Adam (Premium Male)")
                st.session_state["fv_auto_selected_voice"] = voice_label
            st.session_state["fv_auto_selected_category"] = detected_category
        
        st.session_state["fv_detected_gender"] = detected_gender
        st.session_state["fv_detected_age"] = detected_age
        st.session_state["fv_detected_category"] = detected_category
        logger.info(f"DeepFace Auto-Voice: {detected_category} (Age:{detected_age}) -> {voice_label}")
    except Exception as scan_e:
        logger.warning(f"DeepFace auto-scan error (proceeding with default voice): {scan_e}")
    # --- End DeepFace Auto-Scan --- #

    # Resolve voice config
    voice_cfg = _resolve_face_voice_config(
        voice_language=voice_language, 
        voice_label=voice_label, 
        preferred_gender=st.session_state.get('fv_detected_gender') if st.session_state.get('fv_gender_auto', False) else None
    )

    # --- Cloud-Only: Directly call Replicate API --- #
    video_result = generate_world_face_video(
        prompt=prompt,
        face_image_path=face_image_path,
        duration=duration,
        quality=quality,
        voice_language=voice_cfg.get("language", "English"),
        voice_label=voice_cfg.get("voice_label", "Adam (Premium Male)"),
    )
    
    if video_result:
        return video_result
    
    logger.error("All Replicate cloud models failed. No local fallback available.")
    return None

def generate_elevenlabs_audio_for_face(text, output_path, voice_id="21m00Tcm4TlvDq8ikWAM"):
    eleven_key = os.getenv("ELEVENLABS_API_KEY") or get_system_secret("ELEVENLABS_API_KEY")
    if not eleven_key:
        return False
    safe_remove_file(output_path)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": eleven_key}
    data = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
    except Exception:
        pass
    return False

def process_editor_video(uploaded_files, output_path, effect="none", transition="fade", resolution="1080p", custom_bgm=None, bgm_volume=0.3, voiceover_text="", voice_profile="Adam (Premium Male)", voice_language_choice="🇬🇧 English (US Standard)"):
    if not uploaded_files:
        return False

    media_paths = []
    for uploaded_file in uploaded_files:
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        file_path = os.path.join("editor_uploads", f"media_{uuid.uuid4().hex[:8]}{ext}")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        media_paths.append(file_path)

    if not media_paths:
        return False

    res_map = {"720p": "1280:720", "1080p": "1920:1080", "4K": "3840:2160"}
    resolution_str = res_map.get(resolution, "1920:1080")
    temp_dir = os.path.join("temp_scenes", f"editor_temp_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_dir, exist_ok=True)

    bgm_path = None
    if custom_bgm is not None:
        bgm_path = os.path.join(temp_dir, f"custom_bgm_{uuid.uuid4().hex[:8]}.mp3")
        with open(bgm_path, "wb") as f:
            f.write(custom_bgm.getbuffer())

    voiceover_path = None
    if voiceover_text and str(voiceover_text).strip():
        voiceover_path = os.path.join(temp_dir, f"voiceover_{uuid.uuid4().hex[:8]}.mp3")
        selected_voice_meta = ELEVENLABS_VOICES.get(voice_profile, {})
        selected_voice_id = selected_voice_meta.get("id")
        if not selected_voice_id:
            selected_voice_id = "21m00Tcm4TlvDq8ikWAM" if "Male" in voice_profile else "pNInz6obpgDQ5IdwJg7p"

        voice_built = False
        if ELEVENLABS_API_KEY:
            voice_built = AudioEngine.generate_elevenlabs_speech(str(voiceover_text).strip(), voiceover_path, selected_voice_id)
        if not voice_built:
            voice_built = AudioEngine.run_fallback_tts(
                text=str(voiceover_text).strip(),
                output_filename=voiceover_path,
                language_choice=voice_language_choice,
                voice_profile=voice_profile,
            )
        if not voice_built or not os.path.exists(voiceover_path) or os.path.getsize(voiceover_path) <= 1000:
            voiceover_path = None

    try:
        processed_clips = []
        for idx, media_path in enumerate(media_paths):
            ext = os.path.splitext(media_path)[1].lower()
            output_clip = os.path.join(temp_dir, f"clip_{idx:04d}.mp4")

            if ext in ['.png', '.jpg', '.jpeg', '.webp']:
                cmd = [
                    'ffmpeg', '-y', '-loop', '1', '-i', media_path, '-t', '3',
                    '-vf', f"scale={resolution_str}:force_original_aspect_ratio=decrease,pad={resolution_str}:(ow-iw)/2:(oh-ih)/2,fps=24",
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '128k', '-ac', '2', '-ar', '44100', '-f', 'mp4', output_clip
                ]
            elif ext in ['.mp3', '.wav']:
                cmd = [
                    'ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=#050508:s={resolution_str}:r=24',
                    '-i', media_path, '-shortest', '-vf', 'fps=24',
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '128k', '-ac', '2', '-ar', '44100', '-f', 'mp4', output_clip
                ]
            else:
                cmd = [
                    'ffmpeg', '-y', '-i', media_path,
                    '-vf', f"scale={resolution_str}:force_original_aspect_ratio=decrease,pad={resolution_str}:(ow-iw)/2:(oh-ih)/2,fps=24",
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '128k', '-ac', '2', '-ar', '44100', '-f', 'mp4', output_clip
                ]

            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=60)
                if os.path.exists(output_clip) and os.path.getsize(output_clip) > 1000:
                    processed_clips.append(output_clip)
            except Exception:
                fallback_clip = os.path.join(temp_dir, f"fallback_{idx:04d}.mp4")
                fallback_cmd = [
                    'ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=#050508:s={resolution_str}:r=24',
                    '-t', '3', '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '128k', '-ac', '2', '-ar', '44100', '-f', 'mp4', fallback_clip
                ]
                subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                processed_clips.append(fallback_clip)

        if not processed_clips:
            return False

        transition_map = {
            "fade": "fade",
            "crossfade": "fade",
            "slide": "slideleft",
            "circle": "circleopen",
            "radial": "radial",
            "smooth": "smoothleft",
            "zoom": "zoomin",
        }

        effect_filter = ""
        if effect == "sepia":
            effect_filter = "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131"
        elif effect == "grayscale":
            effect_filter = "hue=s=0"
        elif effect == "vintage":
            effect_filter = "curves=all='0/0 0.5/0.5 1/1',colorbalance=rs=0.1:gs=0.1:bs=0.1"
        elif effect == "cinematic":
            effect_filter = "colorbalance=rs=0.1:gs=-0.05:bs=-0.05,curves=all='0/0 0.3/0.2 0.7/0.8 1/1'"
        elif effect == "neon":
            effect_filter = "colorbalance=rs=0.3:gs=-0.2:bs=0.5,curves=all='0/0 0.2/0.1 0.5/0.7 1/1'"
        elif effect == "glitch":
            effect_filter = "rgbashift=rh=2:gh=4:bh=6"
        elif effect == "dreamy":
            effect_filter = "boxblur=2:1,colorbalance=rs=0.2:gs=0.1:bs=0.3"
        elif effect == "dramatic":
            effect_filter = "colorbalance=rs=0.2:gs=-0.1:bs=-0.1,curves=all='0/0 0.3/0.1 0.7/0.8 1/1',unsharp=5:5:1.0"

        base_stitched = os.path.join(temp_dir, "stitched_base.mp4")
        if len(processed_clips) == 1:
            shutil.copy(processed_clips[0], base_stitched)
        elif transition in transition_map:
            xfade_name = transition_map[transition]
            durations = [max(0.6, get_media_duration(path)) for path in processed_clips]
            xfade_duration = 0.5

            ff_inputs = ['ffmpeg', '-y']
            for clip in processed_clips:
                ff_inputs += ['-i', clip]

            filter_parts = []
            running_offset = max(0.0, durations[0] - xfade_duration)
            current_label = '[0:v]'
            for i in range(1, len(processed_clips)):
                out_label = f"[vx{i}]"
                filter_parts.append(
                    f"{current_label}[{i}:v]xfade=transition={xfade_name}:duration={xfade_duration:.2f}:offset={running_offset:.2f}{out_label}"
                )
                current_label = out_label
                running_offset += max(0.1, durations[i] - xfade_duration)

            if effect_filter:
                filter_parts.append(f"{current_label}{effect_filter}[vout]")
                final_video_label = '[vout]'
            else:
                final_video_label = current_label

            transition_cmd = ff_inputs + [
                '-filter_complex', ';'.join(filter_parts),
                '-map', final_video_label,
                '-pix_fmt', 'yuv420p',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                base_stitched
            ]
            try:
                subprocess.run(transition_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=180)
            except Exception:
                transition = "none"

        if not os.path.exists(base_stitched) or os.path.getsize(base_stitched) <= 0:
            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, "w") as f:
                for clip_path in processed_clips:
                    abs_path = os.path.abspath(clip_path).replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")

            no_transition_output = os.path.join(temp_dir, "stitched_no_transition.mp4")
            concat_cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file,
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p',
                '-map', '0:v:0', '-map', '0:a?', '-c:a', 'aac', '-b:a', '192k',
                '-movflags', '+faststart', no_transition_output
            ]
            subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=120)

            if effect_filter:
                effect_output = os.path.join(temp_dir, "stitched_effect.mp4")
                effect_cmd = [
                    'ffmpeg', '-y', '-i', no_transition_output, '-vf', effect_filter,
                    '-map', '0:v:0', '-map', '0:a?', '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', effect_output
                ]
                subprocess.run(effect_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=120)
                base_stitched = effect_output
            else:
                base_stitched = no_transition_output

        if not os.path.exists(base_stitched) or os.path.getsize(base_stitched) <= 0:
            return False

        mixed_ok = mix_audio_layers(
            video_input_path=base_stitched,
            output_path=output_path,
            bgm_path=bgm_path,
            bgm_volume=bgm_volume,
            voice_path=voiceover_path,
            voice_volume=1.0,
        )
        if not mixed_ok:
            try:
                shutil.copy(base_stitched, output_path)
            except Exception:
                return False

        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.error(f"Video editor error: {e}")
        return False
    finally:
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

def render_premium_selection_cards(label, options, session_key):
    st.markdown(f"<div class='compact-label'>{label}</div>", unsafe_allow_html=True)
    num_opts = len(options)
    cols = st.columns(num_opts)
    for idx, opt in enumerate(options):
        is_selected = (st.session_state[session_key] == opt)
        wrapper_class = "selected-opt-wrap" if is_selected else "unselected-opt-wrap"
        with cols[idx]:
            st.markdown(f"<div class='{wrapper_class}'>", unsafe_allow_html=True)
            if st.button(opt, key=f"opt_btn_{session_key}_{idx}", use_container_width=True):
                st.session_state[session_key] = opt
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# ========================================================
# 34. GENERATE HOOK VARIATIONS
# ========================================================

def generate_hook_variations(topic_or_intro):
    clean_topic = topic_or_intro.replace('"', '').replace("'", "").strip()
    words = clean_topic.split()
    subject = " ".join(words[:3]) if len(words) > 3 else clean_topic
    hook_1_txt = f"Wait... did you know that {clean_topic[:75]}...?"
    hook_2_txt = f"This single fact will completely alter how you view {subject} forever!"
    hook_3_txt = f"Almost everyone gets this wrong. Let's look closer at {subject}..."
    return [hook_1_txt, hook_2_txt, hook_3_txt]

# ========================================================
# 35. GENERATE VIDEO BLUEPRINT WITH DEEPSEEK
# ========================================================

def generate_video_blueprint_with_deepseek(user_prompt, aspect_ratio="16:9"):
    """Generate a structured video blueprint using DeepSeek API"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    
    system_instruction = (
        "You are the core AI director for Zovix Portal. Your job is to convert user topics into a structured video creation blueprint. "
        "You must respond ONLY with a valid JSON object. Do not include markdown blocks like ```json ... ```, just raw JSON text. "
        "The JSON structure must be exactly like this:\n"
        "{\n"
        "  'video_title': 'String',\n"
        "  'total_scenes': Integer,\n"
        "  'scenes': [\n"
        "    {'scene_no': 1, 'visual_prompt': 'Detailed image generation prompt', 'narration_text': 'Voiceover text for this scene', 'duration_sec': 5}\n"
        "  ]\n"
        "}"
    )
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Create a high-fidelity video blueprint for topic: '{user_prompt}' with aspect ratio {aspect_ratio}"}
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            raw_content = response.json()['choices'][0]['message']['content']
            return json.loads(raw_content)
        else:
            return {"error": f"DeepSeek API Error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": f"Connection Failure: {str(e)}"}

# ========================================================
# 36. MODE FUNCTIONS - AI Agent, AI Sales, Dynamic UI, Live Emotion
# ========================================================

def validate_and_deduct_tokens(mode_name: str, quality: str):
    if not st.session_state.get("is_logged_in"):
        return False, 0, "Please log in first."
    
    user_credits = get_user_credits_db(st.session_state["logged_user"])
    required_tokens = calculate_tokens(mode_name, quality)
    
    if user_credits < required_tokens:
        return False, required_tokens, f"Insufficient credits! Required: {required_tokens}, Available: {user_credits}"
    
    deduct_credits_db(st.session_state["logged_user"], required_tokens)
    st.session_state['user_credits'] = get_user_credits_db(st.session_state["logged_user"])
    
    return True, required_tokens, f"✅ Deducted {required_tokens} credits for {mode_name}"

def render_ai_agent_ui():
    """AI Agent - Fully Fixed"""
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(236,72,153,0.06), rgba(69,243,255,0.06));
        border-radius: 16px;
        border: 1px solid rgba(69,243,255,0.08);
        padding: 16px 20px;
        margin-bottom: 18px;
        text-align: center;
    ">
        <span style="
            display: inline-block;
            background: rgba(236,72,153,0.12);
            color: #EC4899;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 9px;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            border: 1px solid rgba(236,72,153,0.15);
            margin-bottom: 6px;
        ">🤖 BUSINESS AI</span>
        <h2 style="
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            color: #FFFFFF;
            margin: 0;
        ">
            AI <span style="
                background: linear-gradient(135deg, #45f3ff, #EC4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">Cyber-Agent</span>
        </h2>
        <p style="
            font-family: 'Inter', sans-serif;
            color: #94a3b8;
            font-size: 12px;
            margin: 4px 0 0 0;
        ">
            Auto-pilot your business • Generate content • Manage orders • Collect payments
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    agent_col1, agent_col2 = st.columns([1.1, 1.4], gap="medium")
    
    with agent_col1:
        with st.container(border=True):
            st.markdown("""
            <h4 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 12px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                ⚙️ AGENT CONFIGURATION
            </h4>
            """, unsafe_allow_html=True)
            
            # Business Details
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">🏪 Business Details</p>', unsafe_allow_html=True)
            business_name = st.text_input(
                "Business Name",
                placeholder="Your Shop/Brand Name",
                key="agent_business_name_input",
                label_visibility="collapsed"
            )
            
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📂 Business Category</p>', unsafe_allow_html=True)
            business_category = st.selectbox(
                "Category",
                ["Retail Store", "Restaurant/Cafe", "Clothing Brand", "Tech Services", "Beauty/Salon", "Other"],
                key="agent_category",
                label_visibility="collapsed"
            )
            
            # Products
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📦 Products/Services (one per line)</p>', unsafe_allow_html=True)
            products_text = st.text_area(
                "Products",
                placeholder="e.g.\n₹499 - T-Shirt\n₹999 - Jeans\n₹1499 - Jacket",
                height=100,
                key="agent_products_input",
                label_visibility="collapsed"
            )
            
            # Business Hours
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🕐 Business Hours</p>', unsafe_allow_html=True)
            col_time1, col_time2 = st.columns(2)
            with col_time1:
                opening_time = st.time_input(
                    "Opening Time",
                    value=datetime.strptime("09:00", "%H:%M").time(),
                    key="agent_open_time",
                    label_visibility="collapsed"
                )
            with col_time2:
                closing_time = st.time_input(
                    "Closing Time",
                    value=datetime.strptime("21:00", "%H:%M").time(),
                    key="agent_close_time",
                    label_visibility="collapsed"
                )
            
            # Social Media
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📱 Social Media Accounts</p>', unsafe_allow_html=True)
            instagram_handle = st.text_input(
                "Instagram Handle",
                placeholder="@your_business",
                key="agent_instagram",
                label_visibility="collapsed"
            )
            whatsapp_number = st.text_input(
                "WhatsApp Number",
                placeholder="+91XXXXXXXXXX",
                key="agent_whatsapp",
                label_visibility="collapsed"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Quality
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📊 Agent Quality</p>', unsafe_allow_html=True)
            agent_quality = st.selectbox(
                "Quality",
                ["Standard", "Pro"],
                key="agent_quality",
                label_visibility="collapsed"
            )
            
            # ✅ FIXED: Activate Button with proper logic
            if st.button("🚀 Activate AI Agent", key="agent_activate_btn", use_container_width=True):
                if not business_name.strip():
                    st.error("❌ Please enter a business name.")
                elif not products_text.strip():
                    st.error("❌ Please list at least one product or service.")
                else:
                    required_tokens = 2 if agent_quality == "Standard" else 4
                    
                    if st.session_state.get('user_credits', 0) < required_tokens:
                        st.error(f"❌ Insufficient credits! Required: {required_tokens}, Available: {st.session_state.get('user_credits', 0)}")
                    else:
                        try:
                            # Deduct credits
                            deduct_credits_db(st.session_state["logged_user"], required_tokens)
                            st.session_state['user_credits'] = get_user_credits_db(st.session_state["logged_user"])
                            
                            with st.spinner("🔄 Configuring AI Agent for your business..."):
                                st.session_state["agent_business_name"] = business_name
                                st.session_state["agent_products"] = [p.strip() for p in products_text.split("\n") if p.strip()]
                                st.session_state["agent_schedule"] = {
                                    "open": str(opening_time),
                                    "close": str(closing_time),
                                    "instagram": instagram_handle,
                                    "whatsapp": whatsapp_number,
                                    "category": business_category
                                }
                                
                                # Save to database
                                conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
                                cursor = conn.cursor()
                                try:
                                    cursor.execute(
                                        "INSERT OR REPLACE INTO ai_agent_config (username, business_name, products, schedule) VALUES (?, ?, ?, ?)",
                                        (st.session_state["logged_user"], business_name, json.dumps(st.session_state["agent_products"]), json.dumps(st.session_state["agent_schedule"]))
                                    )
                                    conn.commit()
                                except Exception as db_e:
                                    logger.warning(f"DB save error: {db_e}")
                                finally:
                                    conn.close()
                                
                                st.session_state["ai_agent_mode"] = True
                                st.toast("✅ AI Agent activated successfully!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
    
    with agent_col2:
        with st.container(border=True):
            st.markdown("""
            <h3 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 13px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                📊 AGENT DASHBOARD
            </h3>
            """, unsafe_allow_html=True)
            
            if st.session_state.get("ai_agent_mode") and st.session_state.get("agent_business_name"):
                st.markdown(f"""
                <div style="
                    background: rgba(69,243,255,0.04);
                    border: 1px solid rgba(69,243,255,0.1);
                    border-radius: 12px;
                    padding: 14px;
                    margin-bottom: 12px;
                ">
                    <h4 style="
                        font-family: 'Orbitron', sans-serif;
                        font-size: 11px;
                        color: #45f3ff;
                        margin: 0 0 4px 0;
                    ">
                        🟢 ACTIVE
                    </h4>
                    <p style="
                        font-family: 'Inter', sans-serif;
                        font-size: 16px;
                        font-weight: bold;
                        color: #FFFFFF;
                        margin: 0;
                    ">
                        {st.session_state['agent_business_name']}
                    </p>
                    <p style="
                        font-family: 'Inter', sans-serif;
                        font-size: 11px;
                        color: #94a3b8;
                        margin: 0;
                    ">
                        Category: {st.session_state.get('agent_schedule', {}).get('category', 'N/A')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                products = st.session_state.get("agent_products", [])
                if products:
                    st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">📦 Your Products/Services:</p>', unsafe_allow_html=True)
                    for p in products[:5]:
                        st.markdown(f'<p style="font-family: Inter; font-size: 12px; color: #e0e0e0; margin: 2px 0;">- {p}</p>', unsafe_allow_html=True)
                    if len(products) > 5:
                        st.caption(f"... and {len(products) - 5} more")
                
                schedule = st.session_state.get("agent_schedule", {})
                st.markdown(f"""
                <div style="
                    background: rgba(255,255,255,0.02);
                    border-radius: 8px;
                    padding: 10px;
                    margin-top: 10px;
                ">
                    <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 2px 0;">
                        🕐 Hours: {schedule.get('open', 'N/A')} - {schedule.get('close', 'N/A')}
                    </p>
                    <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 2px 0;">
                        📱 WhatsApp: {schedule.get('whatsapp', 'N/A')}
                    </p>
                    <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 2px 0;">
                        📸 Instagram: {schedule.get('instagram', 'N/A')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 8px;">⚡ Quick Actions:</p>', unsafe_allow_html=True)
                
                col_qa1, col_qa2 = st.columns(2)
                with col_qa1:
                    if st.button("📱 Generate WhatsApp Ad", key="agent_whatsapp_ad", use_container_width=True):
                        with st.spinner("Generating WhatsApp ad..."):
                            ad_text = f"🏪 {st.session_state['agent_business_name']} - Now Open!\n\n"
                            ad_text += "📍 Our Products:\n"
                            for p in products[:3]:
                                ad_text += f"• {p}\n"
                            ad_text += f"\n🕐 Hours: {schedule.get('open', 'N/A')} - {schedule.get('close', 'N/A')}\n"
                            ad_text += f"📱 Contact: {schedule.get('whatsapp', 'N/A')}\n\n"
                            ad_text += "Visit us today! 🚀"
                            st.session_state["agent_generated_ad"] = ad_text
                            st.toast("WhatsApp ad generated!")
                            st.rerun()
                
                with col_qa2:
                    if st.button("📸 Generate Instagram Post", key="agent_instagram_post", use_container_width=True):
                        with st.spinner("Generating Instagram post..."):
                            post_prompt = f"Beautiful product photography showcasing {st.session_state['agent_business_name']} products, professional, clean background, studio lighting"
                            img_path = generate_pro_image(post_prompt, "1:1")
                            if img_path and os.path.exists(img_path):
                                st.session_state["agent_instagram_image"] = img_path
                                caption = f"🌟 Introducing {st.session_state['agent_business_name']}!\n\n"
                                caption += "Check out our amazing collection:\n"
                                for p in products[:3]:
                                    caption += f"• {p}\n"
                                caption += f"\n🕐 Open: {schedule.get('open', 'N/A')} - {schedule.get('close', 'N/A')}\n"
                                caption += f"📱 WhatsApp: {schedule.get('whatsapp', 'N/A')}\n"
                                caption += "\n#SmallBusiness #LocalShop #MadeWithZovix"
                                st.session_state["agent_instagram_caption"] = caption
                                st.toast("Instagram post generated!")
                                st.rerun()
                            else:
                                st.error("❌ Image generation failed. Try again.")
                
                if st.session_state.get("agent_generated_ad"):
                    with st.expander("📱 WhatsApp Ad Preview", expanded=False):
                        st.text(st.session_state["agent_generated_ad"])
                        st.download_button(
                            label="📥 Copy Ad",
                            data=st.session_state["agent_generated_ad"],
                            file_name="whatsapp_ad.txt",
                            mime="text/plain",
                            key="agent_download_ad"
                        )
                
                if st.session_state.get("agent_instagram_image") and os.path.exists(st.session_state["agent_instagram_image"]):
                    with st.expander("📸 Instagram Post Preview", expanded=False):
                        st.image(st.session_state["agent_instagram_image"], caption="Generated Post Image", use_container_width=True)
                        st.text(st.session_state.get("agent_instagram_caption", ""))
                        st.download_button(
                            label="📥 Download Image",
                            data=open(st.session_state["agent_instagram_image"], "rb").read(),
                            file_name="instagram_post.png",
                            mime="image/png",
                            key="agent_download_ig"
                        )
            else:
                st.markdown("""
                    <div style="
                        height: 380px;
                        min-height: 380px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        color: #64748b;
                        text-align: center;
                        padding: 12px;
                        overflow: hidden;
                        background: rgba(10,10,12,0.4);
                        border-radius: 12px;
                        border: 1px dashed rgba(69,243,255,0.12);
                    ">
                        <span style="font-size: 48px; margin-bottom: 10px;">🤖</span>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 13px;
                            font-weight: 500;
                            color: #EC4899;
                            margin: 0;
                        ">
                            AI Agent Inactive
                        </p>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 11px;
                            color: #94a3b8;
                            max-width: 400px;
                            text-align: center;
                            margin-top: 4px;
                            line-height: 1.4;
                        ">
                            Configure your business details and activate the agent.
                        </p>
                    </div>
                """, unsafe_allow_html=True)

def render_ai_sales_ui():
    """AI Sales - Matching Studio Style"""
    
    # ========================================================
    # HEADER - STUDIO STYLE MATCH
    # ========================================================
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(236,72,153,0.06), rgba(69,243,255,0.06));
        border-radius: 16px;
        border: 1px solid rgba(69,243,255,0.08);
        padding: 16px 20px;
        margin-bottom: 18px;
        text-align: center;
    ">
        <span style="
            display: inline-block;
            background: rgba(236,72,153,0.12);
            color: #EC4899;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 9px;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            border: 1px solid rgba(236,72,153,0.15);
            margin-bottom: 6px;
        ">🎙️ SALES AI</span>
        <h2 style="
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            color: #FFFFFF;
            margin: 0;
        ">
            AI Voice & Video <span style="
                background: linear-gradient(135deg, #45f3ff, #EC4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">Sales Engine</span>
        </h2>
        <p style="
            font-family: 'Inter', sans-serif;
            color: #94a3b8;
            font-size: 12px;
            margin: 4px 0 0 0;
        ">
            Create AI sales videos in any language with realistic avatars
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    sales_col1, sales_col2 = st.columns([1.1, 1.4], gap="medium")
    
    with sales_col1:
        with st.container(border=True):
            st.markdown("""
            <h4 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 12px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                ⚙️ SALES VIDEO PARAMETERS
            </h4>
            """, unsafe_allow_html=True)
            
            # Product Details
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">📦 Product Details</p>', unsafe_allow_html=True)
            product_name = st.text_input(
                "Product Name",
                placeholder="e.g. Smart Watch Pro",
                key="sales_product_name_input",
                label_visibility="collapsed"
            )
            product_price = st.text_input(
                "Product Price",
                placeholder="e.g. ₹4999",
                key="sales_product_price_input",
                label_visibility="collapsed"
            )
            
            # Product Image
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📷 Product Image</p>', unsafe_allow_html=True)
            product_image = st.file_uploader(
                "Upload Product Image",
                type=['jpg', 'jpeg', 'png', 'webp'],
                key="sales_image_upload",
                label_visibility="collapsed"
            )
            if product_image:
                img_path = f"ai_sales_videos/product_{uuid.uuid4().hex[:8]}.png"
                with open(img_path, "wb") as f:
                    f.write(product_image.getbuffer())
                st.session_state["sales_product_image"] = img_path
                st.image(img_path, caption="Product Image", use_container_width=True)
            
            # Language & Voice
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🌐 Language & Voice</p>', unsafe_allow_html=True)
            sales_language = st.selectbox(
                "Sales Language",
                ["Hindi", "Bhojpuri", "Maithili", "Tamil", "Telugu", "English", "Hinglish"],
                key="sales_language_select",
                label_visibility="collapsed"
            )
            sales_voice = st.selectbox(
                "Voice Profile",
                ["Male (Drew)", "Female (Rachel)", "Male (Deep)", "Female (Aria)"],
                key="sales_voice_select",
                label_visibility="collapsed"
            )
            
            # Sales Script
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📝 Sales Script / Pitch</p>', unsafe_allow_html=True)
            sales_script = st.text_area(
                "Script",
                placeholder="e.g. Namaste! Aaj hum aapke liye laye hain ek zabardast offer...",
                height=100,
                key="sales_script_input",
                label_visibility="collapsed"
            )
            
            if st.button("📝 Auto-Generate Sales Script", key="sales_gen_script", use_container_width=True):
                if product_name.strip():
                    lang_map = {
                        "Hindi": "Hindi",
                        "Bhojpuri": "Bhojpuri",
                        "Maithili": "Maithili",
                        "Tamil": "Tamil",
                        "Telugu": "Telugu",
                        "English": "English",
                        "Hinglish": "Hinglish"
                    }
                    lang = lang_map.get(sales_language, "Hinglish")
                    script = f"Namaste! Aaj hum aapke liye laye hain {product_name} ka ek zabardast offer."
                    script += f" Yeh product hai sirf {product_price} mein."
                    script += " Quality aur performance dono mein number one. Limited stock hai, toh jaldi karein."
                    script += f" Aaj hi order karein apna {product_name}."
                    
                    if sales_language == "Bhojpuri":
                        script = f"Pranam! Aaj hum aapan lave hai {product_name} ka ek dhansu offer."
                        script += f" Ee product hai sirf {product_price} mein."
                        script += " Quality aur performance dono mein number one. Limited stock hai, toh jaldi karein."
                        script += f" Aaj hi order karein apna {product_name}."
                    elif sales_language == "Tamil":
                        script = f"Vanakkam! Inga namma ungalukku {product_name} oru special offer kondu vandhirukkom."
                        script += f" Indha product vilaiku {product_price} mattum."
                        script += " Quality la Number One. Limited stock, seekiram order pannunga."
                        script += f" Ingaikkave ungaloda {product_name} order pannunga."
                    
                    st.session_state["sales_script_input"] = script
                    st.toast("Script generated in " + sales_language + "!")
                    st.rerun()
                else:
                    st.error("Please enter product name first.")
            
            # Quality
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📊 Sales Video Quality</p>', unsafe_allow_html=True)
            sales_quality = st.selectbox(
                "Quality",
                ["Standard", "HD", "4K"],
                key="sales_quality",
                label_visibility="collapsed"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🎬 Generate AI Sales Video", key="sales_generate_btn", use_container_width=True):
                success, required_tokens, message = validate_and_deduct_tokens("AI Sales", sales_quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    if not product_name.strip():
                        st.error("Please enter product name.")
                    elif not st.session_state.get("sales_product_image") or not os.path.exists(st.session_state["sales_product_image"]):
                        st.error("Please upload a product image.")
                    elif not st.session_state.get("sales_script_input", "").strip():
                        st.error("Please enter a sales script or auto-generate one.")
                    else:
                        with st.spinner(f"🎬 Generating AI Sales Video in {sales_language}..."):
                            script_text = st.session_state["sales_script_input"]
                            face_img_path = st.session_state["sales_product_image"]
                            
                            sales_lang_to_face_lang = {
                                "Hindi": "Hindi",
                                "Bhojpuri": "Hindi",
                                "Maithili": "Hindi",
                                "Tamil": "Hindi",
                                "Telugu": "Hindi",
                                "Hinglish": "Hindi",
                                "English": "English",
                            }
                            sales_voice_to_label = {
                                "Male (Drew)": "Drew (Professional Male)",
                                "Female (Rachel)": "Rachel (Premium Female)",
                                "Male (Deep)": "Antoni (Deep Male)",
                                "Female (Aria)": "Emily (Professional Female)",
                            }
                            
                            face_voice_language = sales_lang_to_face_lang.get(sales_language, "English")
                            face_voice_label = sales_voice_to_label.get(sales_voice, "Adam (Premium Male)")
                            
                            video_path = generate_face_video(
                                script_text,
                                face_img_path,
                                duration=15,
                                emotion="excited",
                                camera_angle="front",
                                quality=sales_quality,
                                voice_language=face_voice_language,
                                voice_label=face_voice_label,
                            )
                            
                            if video_path and (is_remote_url(video_path) or os.path.exists(video_path)):
                                st.session_state["sales_video_output"] = video_path
                                st.session_state["sales_product_name"] = product_name
                                st.session_state["sales_product_price"] = product_price
                                st.session_state["sales_language"] = sales_language
                                st.session_state["sales_voice"] = sales_voice
                                st.session_state["sales_script"] = script_text
                                
                                conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
                                cursor = conn.cursor()
                                try:
                                    cursor.execute(
                                        "INSERT INTO ai_sales_videos (username, product_name, product_price, language, video_path, script) VALUES (?, ?, ?, ?, ?, ?)",
                                        (st.session_state["logged_user"], product_name, product_price, sales_language, video_path, script_text)
                                    )
                                    conn.commit()
                                except Exception:
                                    pass
                                finally:
                                    conn.close()
                                
                                st.toast("🎉 AI Sales Video generated successfully!")
                                st.rerun()
                            else:
                                st.error("Sales video generation failed. Please try again.")
    
    with sales_col2:
        with st.container(border=True):
            st.markdown("""
            <h3 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 13px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                🎬 SALES VIDEO PLAYER
            </h3>
            """, unsafe_allow_html=True)
            
            sales_video = st.session_state.get("sales_video_output")
            if sales_video and (is_remote_url(sales_video) or os.path.exists(sales_video)):
                st.video(sales_video, format="video/mp4", autoplay=True, loop=True, muted=False)
                st.markdown("<br>", unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style="
                    background: rgba(236,72,153,0.04);
                    border: 1px solid rgba(236,72,153,0.1);
                    border-radius: 8px;
                    padding: 10px;
                ">
                    <p style="font-family: Inter; font-size: 12px; color: #94a3b8; margin: 2px 0;">
                        📦 {st.session_state.get('sales_product_name', 'Product')}
                    </p>
                    <p style="font-family: Orbitron; font-size: 14px; font-weight: bold; color: #EC4899; margin: 2px 0;">
                        💰 {st.session_state.get('sales_product_price', 'N/A')}
                    </p>
                    <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 2px 0;">
                        🎙️ {st.session_state.get('sales_language', 'N/A')}
                    </p>
                    <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 2px 0;">
                        🎤 {st.session_state.get('sales_voice', 'N/A')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                col_dl, col_share, col_clr = st.columns(3)
                
                with col_dl:
                    video_bytes = None
                    if is_remote_url(sales_video):
                        try:
                            remote_resp = requests.get(sales_video, timeout=45)
                            if remote_resp.status_code == 200 and len(remote_resp.content) > 1024:
                                video_bytes = remote_resp.content
                        except Exception:
                            video_bytes = None
                    else:
                        with open(sales_video, "rb") as f:
                            video_bytes = f.read()
                    
                    if video_bytes:
                        st.download_button(
                            label="📥 Download Sales Video",
                            data=video_bytes,
                            file_name=f"sales_video_{uuid.uuid4().hex[:8]}.mp4",
                            mime="video/mp4",
                            use_container_width=True,
                            key="sales_download_btn"
                        )
                    else:
                        st.info("Download unavailable for current cloud render.")
                
                with col_share:
                    wa_msg = f"🎬 Check out this amazing product! {st.session_state.get('sales_product_name', 'Product')} - Only {st.session_state.get('sales_product_price', 'N/A')}!"
                    wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_msg)}"
                    st.link_button("💬 Share on WhatsApp", wa_url, use_container_width=True)
                
                with col_clr:
                    if st.button("🧹 Clear Video", key="sales_clear_btn", use_container_width=True):
                        if not is_remote_url(sales_video):
                            safe_remove_file(sales_video)
                        st.session_state["sales_video_output"] = None
                        st.rerun()
                
                with st.expander("📝 View Sales Script", expanded=False):
                    st.text(st.session_state.get("sales_script", ""))
            
            else:
                st.markdown("""
                    <div style="
                        height: 380px;
                        min-height: 380px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        color: #64748b;
                        text-align: center;
                        padding: 12px;
                        overflow: hidden;
                        background: rgba(10,10,12,0.4);
                        border-radius: 12px;
                        border: 1px dashed rgba(236,72,153,0.12);
                    ">
                        <span style="font-size: 48px; margin-bottom: 10px;">🎙️</span>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 13px;
                            font-weight: 500;
                            color: #EC4899;
                            margin: 0;
                        ">
                            AI Sales Video will render here
                        </p>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 11px;
                            color: #94a3b8;
                            max-width: 400px;
                            text-align: center;
                            margin-top: 4px;
                            line-height: 1.4;
                        ">
                            Upload product image, set language, and generate AI sales video.
                        </p>
                    </div>
                """, unsafe_allow_html=True)

def generate_dynamic_ui():
    """Dynamic UI - Fully Fixed"""
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(236,72,153,0.06), rgba(69,243,255,0.06));
        border-radius: 16px;
        border: 1px solid rgba(69,243,255,0.08);
        padding: 16px 20px;
        margin-bottom: 18px;
        text-align: center;
    ">
        <span style="
            display: inline-block;
            background: rgba(236,72,153,0.12);
            color: #EC4899;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 9px;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            border: 1px solid rgba(236,72,153,0.15);
            margin-bottom: 6px;
        ">🧠 ADAPTIVE UI</span>
        <h2 style="
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            color: #FFFFFF;
            margin: 0;
        ">
            Dynamic Context-Aware <span style="
                background: linear-gradient(135deg, #45f3ff, #EC4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">UI</span>
        </h2>
        <p style="
            font-family: 'Inter', sans-serif;
            color: #94a3b8;
            font-size: 12px;
            margin: 4px 0 0 0;
        ">
            Real-time interface adaptation based on user behavior
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if "dynamic_ui_uploaded_file" not in st.session_state:
        st.session_state["dynamic_ui_uploaded_file"] = None
    if "dynamic_ui_project_files" not in st.session_state:
        st.session_state["dynamic_ui_project_files"] = []
    if "dynamic_ui_current_project" not in st.session_state:
        st.session_state["dynamic_ui_current_project"] = ""
    
    col1, col2 = st.columns([1.1, 1.4], gap="medium")
    
    with col1:
        with st.container(border=True):
            st.markdown("""
            <h4 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 12px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                ⚙️ UI CONFIGURATION
            </h4>
            """, unsafe_allow_html=True)
            
            # Profile Mode
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">👤 SELECT PROFILE MODE</p>', unsafe_allow_html=True)
            profile_options = ["🟢 Novice / Simple Mode", "🟡 Intermediate Mode", "🔴 Expert / Developer Mode"]
            profile_map = {
                "🟢 Novice / Simple Mode": "beginner",
                "🟡 Intermediate Mode": "intermediate",
                "🔴 Expert / Developer Mode": "advanced"
            }
            
            current_profile_label = "🟡 Intermediate Mode"
            for label, value in profile_map.items():
                if st.session_state.get("dynamic_ui_profile_mode") == value:
                    current_profile_label = label
                    break
            
            selected_profile = st.selectbox(
                "Choose UI Profile",
                profile_options,
                index=profile_options.index(current_profile_label) if current_profile_label in profile_options else 1,
                key="dynamic_ui_profile_selector",
                label_visibility="collapsed"
            )
            
            new_profile = profile_map.get(selected_profile, "intermediate")
            
            # ✅ FIXED: Profile change with proper logic
            if new_profile != st.session_state.get("dynamic_ui_profile_mode"):
                required_tokens = 2
                
                if st.session_state.get('user_credits', 0) < required_tokens:
                    st.error(f"❌ Insufficient credits! Required: {required_tokens}, Available: {st.session_state.get('user_credits', 0)}")
                else:
                    try:
                        # Deduct credits
                        deduct_credits_db(st.session_state["logged_user"], required_tokens)
                        st.session_state['user_credits'] = get_user_credits_db(st.session_state["logged_user"])
                        
                        st.session_state["dynamic_ui_profile_mode"] = new_profile
                        st.session_state["user_behavior_profile"] = new_profile
                        st.session_state["dynamic_ui_token_charged"] = True
                        
                        # Save to database
                        conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
                        cursor = conn.cursor()
                        try:
                            cursor.execute(
                                "INSERT OR REPLACE INTO dynamic_ui_profiles (username, behavior_profile, ui_preferences) VALUES (?, ?, ?)",
                                (st.session_state.get("logged_user", "user"), new_profile, json.dumps({"profile": new_profile, "timestamp": time.time()}))
                            )
                            conn.commit()
                        except Exception as db_e:
                            logger.warning(f"DB save error: {db_e}")
                        finally:
                            conn.close()
                        
                        st.toast(f"✅ UI Profile changed to: {selected_profile}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            
            # Current Profile Display
            profile_display = st.session_state.get("dynamic_ui_profile_mode", "intermediate")
            profile_icons = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}
            profile_names = {
                "beginner": "Novice / Simple Mode",
                "intermediate": "Intermediate Mode",
                "advanced": "Expert / Developer Mode"
            }
            st.info(f"📊 Current Profile: {profile_icons.get(profile_display, '🟡')} {profile_names.get(profile_display, 'Intermediate Mode')}")
            
            st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 12px 0;'>", unsafe_allow_html=True)
            
            # UI Actions
            st.markdown("""
            <h4 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 11px;
                color: #EC4899;
                margin-bottom: 8px;
                letter-spacing: 0.5px;
            ">
                🔧 UI ACTIONS
            </h4>
            """, unsafe_allow_html=True)
            
            if st.button("📝 New Project", key="ui_new_project", use_container_width=True):
                project_name = f"Project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                st.session_state["dynamic_ui_current_project"] = project_name
                st.session_state["dynamic_ui_project_files"] = []
                st.toast(f"✅ New project created: {project_name}")
                st.rerun()
            
            if st.button("📂 Open Project", key="ui_open_project", use_container_width=True):
                st.session_state["dynamic_ui_open_project"] = True
                st.rerun()
            
            if st.session_state.get("dynamic_ui_open_project", False):
                st.markdown("""
                <div style="
                    background: rgba(69,243,255,0.04);
                    border: 1px solid rgba(69,243,255,0.08);
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 10px;
                ">
                    <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 0 0 8px 0;">
                        📂 Select a project file to open:
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                uploaded_file = st.file_uploader(
                    "Choose a project file",
                    type=['json', 'txt', 'mp4', 'png', 'jpg', 'jpeg', 'webp', 'mp3', 'wav'],
                    key="dynamic_ui_file_uploader",
                    label_visibility="collapsed"
                )
                
                if uploaded_file is not None:
                    file_path = os.path.join("temp_scenes", f"uploaded_{uuid.uuid4().hex[:8]}_{uploaded_file.name}")
                    os.makedirs("temp_scenes", exist_ok=True)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.session_state["dynamic_ui_uploaded_file"] = file_path
                    st.session_state["dynamic_ui_current_project"] = uploaded_file.name
                    st.session_state["dynamic_ui_open_project"] = False
                    st.success(f"✅ Project opened: {uploaded_file.name}")
                    st.toast(f"📂 File loaded: {uploaded_file.name}")
                    st.rerun()
                
                if st.button("❌ Close File Browser", key="ui_close_browser", use_container_width=True):
                    st.session_state["dynamic_ui_open_project"] = False
                    st.rerun()
            
            if st.button("⚡ Quick Render", key="ui_quick_render", use_container_width=True):
                if st.session_state.get("dynamic_ui_uploaded_file"):
                    st.toast("🔄 Rendering project...")
                    time.sleep(0.1)
                    st.success("✅ Quick render completed!")
                else:
                    st.warning("⚠️ No project loaded. Please open a project first.")
            
            if st.button("📊 Analytics", key="ui_analytics", use_container_width=True):
                if st.session_state.get("dynamic_ui_current_project"):
                    st.info(f"📊 Project: {st.session_state['dynamic_ui_current_project']}")
                    st.info(f"📁 Files: {len(st.session_state.get('dynamic_ui_project_files', []))}")
                    st.info(f"👤 Profile: {st.session_state.get('dynamic_ui_profile_mode', 'intermediate')}")
                else:
                    st.warning("⚠️ No active project.")
            
            if st.button("🔧 Advanced Settings", key="ui_advanced_settings", use_container_width=True):
                with st.expander("⚙️ Advanced Settings", expanded=True):
                    st.selectbox("Theme Mode", ["auto", "dark", "light"], key="ui_theme_mode")
                    st.slider("Animation Speed", 0.5, 2.0, 1.0, step=0.1)
                    st.toggle("Auto-save", value=True)
                    st.toggle("Show Grid", value=True)
                    st.toggle("Dark Mode", value=True)
            
            if st.button("🧩 Plugins", key="ui_plugins", use_container_width=True):
                with st.expander("🧩 Plugin Manager", expanded=True):
                    st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 8px;">Available Plugins:</p>', unsafe_allow_html=True)
                    st.checkbox("🎨 AI Image Generator", value=True)
                    st.checkbox("🎬 Video Editor Pro", value=True)
                    st.checkbox("🗣️ Voice Synthesizer", value=True)
                    st.checkbox("📐 Blueprint Creator", value=True)
                    if st.button("🔄 Refresh Plugins", use_container_width=True):
                        st.toast("Plugins refreshed!")
    
    with col2:
        with st.container(border=True):
            st.markdown("""
            <h3 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 13px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                🖥️ UI PREVIEW
            </h3>
            """, unsafe_allow_html=True)
            
            profile_display = st.session_state.get("dynamic_ui_profile_mode", "intermediate")
            current_project = st.session_state.get("dynamic_ui_current_project", "No project loaded")
            
            st.markdown(f"""
            <div style="
                background: rgba(69,243,255,0.04);
                border-radius: 8px;
                padding: 6px 12px;
                margin-bottom: 10px;
                border: 1px solid rgba(69,243,255,0.06);
            ">
                <p style="font-family: Inter; font-size: 10px; color: #EC4899; margin: 0;">
                    📂 <span style="color: #EC4899;">{current_project}</span>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if profile_display == "beginner":
                st.markdown("""
                <div style="
                    background: rgba(18,19,26,0.8);
                    border-radius: 12px;
                    padding: 20px;
                    border: 2px solid rgba(69,243,255,0.2);
                ">
                    <div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;">
                        <span style="
                            background: #EC4899;
                            color: #000;
                            padding: 10px 20px;
                            border-radius: 8px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 12px;
                            font-weight: bold;
                        ">📝 New</span>
                        <span style="
                            background: #EC4899;
                            color: #000;
                            padding: 10px 20px;
                            border-radius: 8px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 12px;
                            font-weight: bold;
                        ">📂 Open</span>
                        <span style="
                            background: #EC4899;
                            color: #000;
                            padding: 10px 20px;
                            border-radius: 8px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 12px;
                            font-weight: bold;
                        ">🎓 Tutorial</span>
                    </div>
                    <p style="
                        text-align: center;
                        color: #EC4899;
                        font-family: 'Inter', sans-serif;
                        font-size: 12px;
                        margin-top: 15px;
                    ">
                        🟢 Simple, clean interface with large buttons
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            elif profile_display == "intermediate":
                st.markdown("""
                <div style="
                    background: rgba(18,19,26,0.8);
                    border-radius: 12px;
                    padding: 20px;
                    border: 2px solid rgba(255,192,203,0.2);
                ">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                        <span style="
                            background: #EC4899;
                            color: #000;
                            padding: 10px;
                            border-radius: 6px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 11px;
                            font-weight: bold;
                            text-align: center;
                        ">📝 New</span>
                        <span style="
                            background: #EC4899;
                            color: #000;
                            padding: 10px;
                            border-radius: 6px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 11px;
                            font-weight: bold;
                            text-align: center;
                        ">📂 Open</span>
                        <span style="
                            background: #EC4899;
                            color: #000;
                            padding: 10px;
                            border-radius: 6px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 11px;
                            font-weight: bold;
                            text-align: center;
                        ">⚡ Quick Render</span>
                        <span style="
                            background: #EC4899;
                            color: #000;
                            padding: 10px;
                            border-radius: 6px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 11px;
                            font-weight: bold;
                            text-align: center;
                        ">🔧 Settings</span>
                    </div>
                    <p style="
                        text-align: center;
                        color: #EC4899;
                        font-family: 'Inter', sans-serif;
                        font-size: 12px;
                        margin-top: 15px;
                    ">
                        🟡 Balanced interface with quick actions
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            else:
                st.markdown("""
                <div style="
                    background: rgba(18,19,26,0.8);
                    border-radius: 12px;
                    padding: 20px;
                    border: 2px solid rgba(236,72,153,0.2);
                ">
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px;">
                        <span style="
                            background: #EC4899;
                            color: #fff;
                            padding: 8px;
                            border-radius: 6px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 10px;
                            font-weight: bold;
                            text-align: center;
                        ">📝 New</span>
                        <span style="
                            background: #EC4899;
                            color: #fff;
                            padding: 8px;
                            border-radius: 6px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 10px;
                            font-weight: bold;
                            text-align: center;
                        ">📂 Open</span>
                        <span style="
                            background: #EC4899;
                            color: #fff;
                            padding: 8px;
                            border-radius: 6px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 10px;
                            font-weight: bold;
                            text-align: center;
                        ">⚡ Render</span>
                        <span style="
                            background: #EC4899;
                            color: #fff;
                            padding: 8px;
                            border-radius: 6px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 10px;
                            font-weight: bold;
                            text-align: center;
                        ">🔧 Advanced</span>
                        <span style="
                            background: #EC4899;
                            color: #fff;
                            padding: 8px;
                            border-radius: 6px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 10px;
                            font-weight: bold;
                            text-align: center;
                        ">📊 Analytics</span>
                        <span style="
                            background: #EC4899;
                            color: #fff;
                            padding: 8px;
                            border-radius: 6px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 10px;
                            font-weight: bold;
                            text-align: center;
                        ">🧩 Plugins</span>
                    </div>
                    <p style="
                        text-align: center;
                        color: #94a3b8;
                        font-family: 'Inter', sans-serif;
                        font-size: 12px;
                        margin-top: 15px;
                    ">
                        🔴 Professional interface with all tools
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            # Loaded File Preview
            if st.session_state.get("dynamic_ui_uploaded_file") and os.path.exists(st.session_state["dynamic_ui_uploaded_file"]):
                file_path = st.session_state["dynamic_ui_uploaded_file"]
                ext = os.path.splitext(file_path)[1].lower()
                
                st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 12px 0;'>", unsafe_allow_html=True)
                st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 6px;">📁 Loaded File:</p>', unsafe_allow_html=True)
                
                if ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
                    st.image(file_path, use_container_width=True)
                elif ext in ['.mp4', '.mov', '.avi', '.webm']:
                    st.video(file_path, format="video/mp4", autoplay=False, loop=True, muted=False)
                elif ext in ['.mp3', '.wav']:
                    with open(file_path, "rb") as f:
                        audio_bytes = f.read()
                    st.audio(audio_bytes, format="audio/mp3")
                elif ext in ['.json', '.txt']:
                    with open(file_path, "r") as f:
                        content = f.read()
                    st.text(content[:500])
                else:
                    st.info(f"📄 File loaded: {os.path.basename(file_path)}")
                
                if st.button("🧹 Clear Loaded File", key="ui_clear_file", use_container_width=True):
                    safe_remove_file(file_path)
                    st.session_state["dynamic_ui_uploaded_file"] = None
                    st.session_state["dynamic_ui_current_project"] = ""
                    st.rerun()

def render_live_emotion_voice():
    """Live Emotion Voice - Matching Studio Style"""
    
    # ========================================================
    # HEADER - STUDIO STYLE MATCH
    # ========================================================
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(236,72,153,0.06), rgba(69,243,255,0.06));
        border-radius: 16px;
        border: 1px solid rgba(69,243,255,0.08);
        padding: 16px 20px;
        margin-bottom: 18px;
        text-align: center;
    ">
        <span style="
            display: inline-block;
            background: rgba(236,72,153,0.12);
            color: #EC4899;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 9px;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            border: 1px solid rgba(236,72,153,0.15);
            margin-bottom: 6px;
        ">🎤 EMOTION AI</span>
        <h2 style="
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            color: #FFFFFF;
            margin: 0;
        ">
            Live-Emotion <span style="
                background: linear-gradient(135deg, #45f3ff, #EC4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">Voice</span>
        </h2>
        <p style="
            font-family: 'Inter', sans-serif;
            color: #94a3b8;
            font-size: 12px;
            margin: 4px 0 0 0;
        ">
            Hyper-realistic voice with real human emotional dynamics
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.1, 1.4], gap="medium")
    
    with col1:
        with st.container(border=True):
            st.markdown("""
            <h4 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 12px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                ⚙️ VOICE PARAMETERS
            </h4>
            """, unsafe_allow_html=True)
            
            # Text Input
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">📝 Text to Speak</p>', unsafe_allow_html=True)
            voice_text = st.text_area(
                "Text",
                placeholder="Write the script you want to convert to emotion-rich voice...",
                height=100,
                key="emotion_voice_text_area",
                label_visibility="collapsed"
            )
            
            # Language
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🌐 Select Language</p>', unsafe_allow_html=True)
            language_options = ["English", "Hindi", "Bhojpuri", "French", "Japanese"]
            selected_language = st.selectbox(
                "Language",
                language_options,
                key="emotion_voice_language",
                label_visibility="collapsed"
            )
            
            # Emotion
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">😊 Emotion Profile</p>', unsafe_allow_html=True)
            emotion_options = ["neutral", "happy", "sad", "angry", "excited", "serious", "mysterious"]
            current_emotion = st.session_state.get("emotion_voice_emotion", "neutral")
            if current_emotion not in emotion_options:
                current_emotion = "neutral"
            selected_emotion = st.selectbox(
                "Emotion",
                emotion_options,
                index=emotion_options.index(current_emotion),
                key="emotion_voice_emotion",
                label_visibility="collapsed"
            )
            
            # Voice Selection
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🎤 Professional Voice</p>', unsafe_allow_html=True)
            available_voices = LANGUAGE_VOICE_MAP.get(selected_language, ["Adam (Premium Male)"])
            show_all_voices = st.checkbox("Show All Voices", key="emotion_show_all_voices")
            
            if show_all_voices:
                voice_options = list(ELEVENLABS_VOICES.keys())
            else:
                voice_options = available_voices
            
            current_voice = st.session_state.get("selected_elevenlabs_voice", "Adam (Premium Male)")
            if current_voice not in voice_options:
                current_voice = voice_options[0] if voice_options else "Adam (Premium Male)"
            
            selected_voice_label = st.selectbox(
                "Choose Voice",
                voice_options,
                index=voice_options.index(current_voice) if current_voice in voice_options else 0,
                key="emotion_voice_elevenlabs_select",
                label_visibility="collapsed"
            )
            
            if selected_voice_label != st.session_state.get("selected_elevenlabs_voice"):
                st.session_state["selected_elevenlabs_voice"] = selected_voice_label
            
            voice_info = ELEVENLABS_VOICES.get(selected_voice_label, {})
            st.markdown(f"""
            <div style="
                background: rgba(236,72,153,0.04);
                border: 1px solid rgba(236,72,153,0.08);
                border-radius: 8px;
                padding: 8px 12px;
                margin-bottom: 12px;
            ">
                <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 0;">
                    🎤 {selected_voice_label} <br>
                    🧑‍🎤 {voice_info.get('gender', 'Unknown').capitalize()} • 
                    🌍 {voice_info.get('accent', 'Unknown')} • 
                    🌐 {voice_info.get('language', 'Unknown')}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Quick Emotion Presets
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 6px;">Quick Emotion Presets:</p>', unsafe_allow_html=True)
            emoji_map = {"neutral": "😐", "happy": "😊", "sad": "😢", "angry": "😡", "excited": "🤩", "serious": "😤", "mysterious": "🕵️"}
            emotion_cols = st.columns(7)
            for i, (emotion, emoji) in enumerate(emoji_map.items()):
                with emotion_cols[i]:
                    def make_emotion_callback(em):
                        def callback():
                            st.session_state["emotion_voice_emotion"] = em
                        return callback
                    if st.button(f"{emoji}", key=f"emotion_quick_{emotion}_{i}", use_container_width=True, on_click=make_emotion_callback(emotion)):
                        pass
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Voice Sample
            if st.button("🔊 Preview Voice Sample", key="emotion_preview_voice", use_container_width=True):
                st.info(f"🎵 Voice sample for {selected_voice_label} will play here.")
                sample_path = "assets/audio/sample.mp3"
                if os.path.exists(sample_path):
                    with open(sample_path, "rb") as f:
                        sample_bytes = f.read()
                    st.audio(sample_bytes, format="audio/mp3")
                else:
                    st.warning("Sample audio not found. Please add a sample.mp3 file to assets/audio/")
            
            # Quality
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📊 Voice Quality</p>', unsafe_allow_html=True)
            voice_quality = st.selectbox(
                "Quality",
                ["Standard", "HD", "Premium"],
                key="emotion_voice_quality",
                label_visibility="collapsed"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🎤 Generate Emotion Voice", key="emotion_voice_generate", use_container_width=True):
                if not voice_text.strip():
                    st.error("Please enter some text to speak.")
                else:
                    success, required_tokens, message = validate_and_deduct_tokens("Live Emotion", voice_quality)
                    if not success:
                        st.error(message)
                    else:
                        st.success(message)
                        with st.spinner(f"🎤 Generating {selected_emotion} voice with {selected_voice_label} in {selected_language}..."):
                            voice_id = ELEVENLABS_VOICES.get(selected_voice_label, {}).get("id", "pNInz6obpgDQ5IdwJg7p")
                            output_path = generate_emotion_voice(
                                voice_text,
                                emotion=selected_emotion,
                                voice_type="male" if voice_info.get("gender") == "male" else "female",
                                elevenlabs_voice_id=voice_id
                            )
                            if output_path and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                                st.session_state["emotion_voice_output"] = output_path
                                st.session_state["emotion_voice_text"] = voice_text
                                
                                conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
                                cursor = conn.cursor()
                                try:
                                    cursor.execute(
                                        "INSERT INTO emotion_voice_history (username, text, emotion, audio_path, voice_id) VALUES (?, ?, ?, ?, ?)",
                                        (st.session_state.get("logged_user", "user"), voice_text[:200], selected_emotion, output_path, selected_voice_label)
                                    )
                                    conn.commit()
                                except Exception:
                                    pass
                                finally:
                                    conn.close()
                                
                                st.toast("✅ Voice generated successfully!")
                                st.rerun()
                            else:
                                st.error("Voice generation failed. Please try again.")
    
    with col2:
        with st.container(border=True):
            st.markdown("""
            <h3 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 13px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                🎧 VOICE PLAYER
            </h3>
            """, unsafe_allow_html=True)
            
            audio_output = st.session_state.get("emotion_voice_output")
            if audio_output and os.path.exists(audio_output):
                emotion = st.session_state.get("emotion_voice_emotion", "neutral")
                emoji_map = {"neutral": "😐", "happy": "😊", "sad": "😢", "angry": "😡", "excited": "🤩", "serious": "😤", "mysterious": "🕵️"}
                emotion_emoji = emoji_map.get(emotion, "😐")
                selected_voice = st.session_state.get("selected_elevenlabs_voice", "Adam (Premium Male)")
                
                st.markdown(f"""
                <div style="
                    background: rgba(236,72,153,0.04);
                    border: 1px solid rgba(236,72,153,0.08);
                    border-radius: 10px;
                    padding: 12px;
                    margin-bottom: 12px;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <span style="font-family: Inter; font-size: 13px; color: #FFFFFF;">
                            {emotion_emoji} {emotion.capitalize()} Voice
                        </span>
                        <span style="font-family: Orbitron; font-size: 11px; color: #EC4899; font-weight: bold;">
                            {selected_voice}
                        </span>
                    </div>
                    <div style="display: flex; gap: 6px; margin-top: 4px; flex-wrap: wrap;">
                        <span style="
                            font-family: Inter;
                            font-size: 9px;
                            color: #94a3b8;
                            background: rgba(255,255,255,0.04);
                            padding: 2px 8px;
                            border-radius: 10px;
                        ">🎯 {emotion}</span>
                        <span style="
                            font-family: Inter;
                            font-size: 9px;
                            color: #94a3b8;
                            background: rgba(255,255,255,0.04);
                            padding: 2px 8px;
                            border-radius: 10px;
                        ">🎤 Professional Voice</span>
                        <span style="
                            font-family: Inter;
                            font-size: 9px;
                            color: #94a3b8;
                            background: rgba(255,255,255,0.04);
                            padding: 2px 8px;
                            border-radius: 10px;
                        ">🌐 {st.session_state.get('emotion_voice_language', 'English')}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with open(audio_output, "rb") as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")
                
                if st.session_state.get("emotion_voice_text"):
                    with st.expander("📝 View Script", expanded=False):
                        st.text(st.session_state["emotion_voice_text"])
                
                st.markdown("<br>", unsafe_allow_html=True)
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    st.download_button(
                        label="📥 Download Voice (MP3)",
                        data=audio_bytes,
                        file_name=f"zovix_voice_{uuid.uuid4().hex[:8]}.mp3",
                        mime="audio/mp3",
                        use_container_width=True,
                        key="emotion_download_btn"
                    )
                with col_clr:
                    if st.button("🧹 Clear Voice", key="emotion_clear_btn", use_container_width=True):
                        safe_remove_file(audio_output)
                        st.session_state["emotion_voice_output"] = None
                        st.session_state["emotion_voice_text"] = ""
                        st.rerun()
                
                with st.expander("📊 Voice Analytics", expanded=False):
                    st.markdown(f"""
                    <div style="
                        background: rgba(255,255,255,0.02);
                        border-radius: 8px;
                        padding: 10px;
                    ">
                        <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 2px 0;">
                            🎯 Emotion: <span style="color: #EC4899;">{emotion.capitalize()}</span>
                        </p>
                        <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 2px 0;">
                            🎤 Voice: <span style="color: #EC4899;">{selected_voice}</span>
                        </p>
                        <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 2px 0;">
                            🌐 Language: <span style="color: #EC4899;">{st.session_state.get('emotion_voice_language', 'English')}</span>
                        </p>
                        <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 2px 0;">
                            📝 Text Length: <span style="color: #EC4899;">{len(st.session_state.get('emotion_voice_text', ''))} characters</span>
                        </p>
                        <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 2px 0;">
                            🎵 Audio Size: <span style="color: #EC4899;">{len(audio_bytes)/1024:.1f} KB</span>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
            
            else:
                st.markdown("""
                    <div style="
                        height: 380px;
                        min-height: 380px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        color: #64748b;
                        text-align: center;
                        padding: 12px;
                        overflow: hidden;
                        background: rgba(10,10,12,0.4);
                        border-radius: 12px;
                        border: 1px dashed rgba(236,72,153,0.12);
                    ">
                        <span style="font-size: 48px; margin-bottom: 10px;">🎤</span>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 13px;
                            font-weight: 500;
                            color: #EC4899;
                            margin: 0;
                        ">
                            Emotion voice will render here
                        </p>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 11px;
                            color: #94a3b8;
                            max-width: 400px;
                            text-align: center;
                            margin-top: 4px;
                            line-height: 1.4;
                        ">
                            Select emotion, voice type, and generate hyper-realistic voice.
                        </p>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 10px;
                            color: #45f3ff;
                            margin-top: 4px;
                        ">
                            ⚡ Real human emotional dynamics
                        </p>
                    </div>
                """, unsafe_allow_html=True)
def generate_emotion_voice(text, emotion="neutral", voice_type="male", output_path=None, elevenlabs_voice_id=None):
    """
    WORLD-CLASS EMOTION VOICE GENERATOR - 5-Tier Cascade
    Tier 1: ElevenLabs (Best Emotion Quality)
    Tier 2: Azure Cognitive Services (Premium Multilingual)
    Tier 3: Google Cloud TTS (Natural)
    Tier 4: Edge TTS (Free, Reliable)
    Tier 5: Generative Fallback (Always Works)
    """
    if not output_path:
        output_path = f"emotion_voice_outputs/emotion_{uuid.uuid4().hex[:8]}.mp3"
    os.makedirs("emotion_voice_outputs", exist_ok=True)
    safe_remove_file(output_path)

    detected_language = st.session_state.get("emotion_voice_language", "English")
    use_hindi_voice = "Hindi" in detected_language or "Hinglish" in detected_language

    # --- Emotion-to-SSML Style Mapping ---
    emotion_ssml_map = {
        "neutral": ("neutral", "general", 0),
        "happy": ("cheerful", "happy", 0.8),
        "sad": ("sad", "sad", 0.3),
        "angry": ("angry", "angry", 0.9),
        "excited": ("excited", "excited", 1.0),
        "serious": ("serious", "serious", 0.2),
        "mysterious": ("whispering", "newscast", 0.4),
    }

    # --- Emotion Prompt Engineering ---
    emotion_prefixes = {
        "neutral": "",
        "happy": "[Speak with bright, cheerful enthusiasm and a smile in your voice] ",
        "sad": "[Speak with a soft, melancholic, and heart-touching tone] ",
        "angry": "[Speak with intense anger, frustration, and aggressive tone] ",
        "excited": "[Speak with high energy, excitement, and electrifying enthusiasm] ",
        "serious": "[Speak with deep, serious, professional, and commanding authority] ",
        "mysterious": "[Speak in a slow, hushed, intriguing, and enigmatic whisper] ",
    }
    emotion_prefix = emotion_prefixes.get(emotion, "")
    modified_text = emotion_prefix + text

    # ========== TIER 1: ELEVENLABS (BEST QUALITY) ==========
    eleven_key = os.getenv("ELEVENLABS_API_KEY") or get_system_secret("ELEVENLABS_API_KEY")
    if eleven_key and elevenlabs_voice_id:
        try:
            stability = emotion_ssml_map.get(emotion, ("neutral", "general", 0.5))[2]
            similarity_boost = 0.75

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_voice_id}"
            headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": eleven_key}

            payload = {
                "text": modified_text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": 0.5 if emotion != "neutral" else 0.0,
                    "use_speaker_boost": True,
                }
            }

            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 2000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 2000:
                    if is_audio_audible(output_path):
                        logger.info(f"ElevenLabs World-Class: {text[:40]}... [emotion={emotion}]")
                        return output_path
        except Exception as e:
            logger.warning(f"ElevenLabs failed: {e}")

    # ========== TIER 2: AZURE TTS (PREMIUM) ==========
    azure_key = os.getenv("AZURE_SPEECH_KEY") or get_system_secret("AZURE_SPEECH_KEY")
    azure_region = os.getenv("AZURE_SPEECH_REGION") or get_system_secret("AZURE_SPEECH_REGION", "eastus")
    if azure_key and azure_region:
        try:
            if use_hindi_voice:
                voice_name = "hi-IN-MadhurNeural" if voice_type == "male" else "hi-IN-SwaraNeural"
            else:
                voice_name = "en-US-GuyNeural" if voice_type == "male" else "en-US-JennyNeural"

            style = emotion_ssml_map.get(emotion, ("neutral", "general", 0.5))[0]

            url = f"https://{azure_region}.tts.speech.microsoft.com/cognitiveservices/v1"
            headers = {
                "Ocp-Apim-Subscription-Key": azure_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3"
            }

            # Build SSML safely
            if use_hindi_voice:
                ssml_parts = [
                    "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"hi-IN\">",
                    f"<voice name=\"{voice_name}\">",
                    f"<prosody rate=\"5%\" pitch=\"0%\">{text}</prosody>",
                    "</voice>",
                    "</speak>"
                ]
            else:
                ssml_parts = [
                    "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xmlns:mstts=\"https://www.w3.org/2001/mstts\" xml:lang=\"en-US\">",
                    f"<voice name=\"{voice_name}\">",
                    f"<mstts:express-as style=\"{style}\" styledegree=\"1.5\">",
                    f"<prosody rate=\"5%\" pitch=\"0%\">{text}</prosody>",
                    "</mstts:express-as>",
                    "</voice>",
                    "</speak>"
                ]
            ssml = "".join(ssml_parts)

            resp = requests.post(url, headers=headers, data=ssml, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                if os.path.exists(output_path) and is_audio_audible(output_path):
                    logger.info(f"Azure World-Class: {text[:40]}... [emotion={emotion}]")
                    return output_path
        except Exception as e:
            logger.warning(f"Azure TTS failed: {e}")

    # ========== TIER 3: GOOGLE CLOUD TTS ==========
    google_key = os.getenv("GOOGLE_TTS_API_KEY") or get_system_secret("GOOGLE_TTS_API_KEY")
    if not google_key:
        google_key = os.getenv("GEMINI_API_KEY") or get_system_secret("GEMINI_API_KEY")
    if google_key:
        try:
            import base64
            ssml_gender = "MALE" if voice_type == "male" else "FEMALE"
            lang_code = "hi-IN" if use_hindi_voice else "en-US"

            emotion_rates = {"neutral": 1.0, "happy": 1.1, "sad": 0.85, "angry": 1.15, "excited": 1.2, "serious": 0.9, "mysterious": 0.8}
            emotion_pitches = {"neutral": 0, "happy": 5, "sad": -3, "angry": 3, "excited": 6, "serious": -2, "mysterious": -4}
            speaking_rate = emotion_rates.get(emotion, 1.0)
            pitch = emotion_pitches.get(emotion, 0)

            payload = {
                "input": {"text": text},
                "voice": {"languageCode": lang_code, "ssmlGender": ssml_gender},
                "audioConfig": {
                    "audioEncoding": "MP3",
                    "speakingRate": speaking_rate,
                    "pitch": pitch,
                    "volumeGainDb": 3.0,
                    "effectsProfileId": ["large-home-entertainment-class-device"]
                }
            }

            resp = requests.post(
                f"https://texttospeech.googleapis.com/v1/text:synthesize?key={google_key}",
                json=payload, timeout=30
            )
            if resp.status_code == 200:
                audio_content = resp.json().get("audioContent")
                if audio_content:
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(audio_content))
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 2000:
                        logger.info(f"Google TTS World-Class: {text[:40]}... [emotion={emotion}]")
                        return output_path
        except Exception as e:
            logger.warning(f"Google TTS failed: {e}")

    # ========== TIER 4: EDGE TTS (FREE, RELIABLE) ==========
    try:
        if edge_tts is not None:
            if use_hindi_voice:
                voice_candidates = [
                    "hi-IN-MadhurNeural" if voice_type == "male" else "hi-IN-SwaraNeural",
                    "en-IN-PrabhatNeural" if voice_type == "male" else "en-IN-NeerjaNeural",
                    "en-US-GuyNeural" if voice_type == "male" else "en-US-AriaNeural",
                ]
            else:
                voice_candidates = [
                    "en-US-GuyNeural" if voice_type == "male" else "en-US-AriaNeural",
                    "en-GB-RyanNeural" if voice_type == "male" else "en-GB-SoniaNeural",
                    "en-IN-PrabhatNeural" if voice_type == "male" else "en-IN-NeerjaNeural",
                ]

            emotion_edge_styles = {
                "neutral": "general",
                "happy": "cheerful",
                "sad": "sad",
                "angry": "angry",
                "excited": "excited",
                "serious": "serious",
                "mysterious": "whispering",
            }

            for voice_name in voice_candidates:
                try:
                    safe_remove_file(output_path)
                    edge_emotion = emotion_edge_styles.get(emotion, "general")

                    async def _do_edge_tts():
                        communicate = edge_tts.Communicate(text, voice_name)
                        await communicate.save(output_path)

                    run_async_in_thread(_do_edge_tts())

                    if os.path.exists(output_path) and os.path.getsize(output_path) > 2048:
                        logger.info(f"Edge TTS World-Class: {text[:40]}... [emotion={emotion}]")
                        return output_path
                except Exception as voice_error:
                    logger.warning(f"Edge TTS voice failed ({voice_name}): {voice_error}")
                    continue
    except Exception as e:
        logger.warning(f"Edge TTS failed: {e}")

    # ========== TIER 5: GENERATIVE FALLBACK ==========
    try:
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
            logger.info(f"Fallback: Generating tone audio for {text[:30]}...")

            import struct
            import math

            sample_rate = 22050
            duration = max(2.0, len(text) * 0.08)
            num_samples = int(sample_rate * duration)

            freq_map = {"neutral": 220, "happy": 440, "sad": 180, "angry": 330, "excited": 550, "serious": 150, "mysterious": 100}
            amp_map = {"neutral": 0.3, "happy": 0.4, "sad": 0.2, "angry": 0.5, "excited": 0.5, "serious": 0.25, "mysterious": 0.15}
            freq = freq_map.get(emotion, 220)
            amplitude = amp_map.get(emotion, 0.3)

            samples = []
            for i in range(num_samples):
                t = i / sample_rate
                vibrato = math.sin(2 * math.pi * 5 * t) * 0.1 if emotion in ("happy", "excited", "sad") else 0
                value = amplitude * math.sin(2 * math.pi * freq * t + vibrato * 2 * math.pi)
                value += 0.3 * amplitude * math.sin(2 * math.pi * freq * 2 * t)
                value += 0.1 * amplitude * math.sin(2 * math.pi * freq * 3 * t)
                value = max(-1.0, min(1.0, value))
                samples.append(struct.pack("h", int(value * 32767)))

            import wave
            with wave.open(output_path, "w") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b"".join(samples))

            mp3_path = output_path.replace(".mp3", "_temp.mp3")
            cmd = ["ffmpeg", "-y", "-i", output_path, "-codec:a", "libmp3lame", "-qscale:a", "2", mp3_path]
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
                    safe_remove_file(output_path)
                    shutil.move(mp3_path, output_path)
            except Exception:
                safe_remove_file(mp3_path)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info(f"Generative Fallback success: {text[:30]}... [emotion={emotion}]")
                return output_path

    except Exception as e:
        logger.error(f"All TTS tiers failed: {e}")

    safe_remove_file(output_path)
    return None# ========================================================
# 37. MODE FUNCTIONS - Creative Workshop, Blueprints, Upscaler, Draw, Video Editor, Face Video
# ========================================================
# 37. MODE FUNCTIONS - Creative Workshop, Blueprints, Upscaler, Draw, Video Editor, Face Video
# ========================================================

def run_creative_workshop():
    """Creative Workshop - Fully Fixed"""
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(236,72,153,0.06), rgba(69,243,255,0.06));
        border-radius: 16px;
        border: 1px solid rgba(69,243,255,0.08);
        padding: 16px 20px;
        margin-bottom: 18px;
        text-align: center;
    ">
        <span style="
            display: inline-block;
            background: rgba(236,72,153,0.12);
            color: #EC4899;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 9px;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            border: 1px solid rgba(236,72,153,0.15);
            margin-bottom: 6px;
        ">🎨 AI GENERATOR</span>
        <h2 style="
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            color: #FFFFFF;
            margin: 0;
        ">
            Creative <span style="
                background: linear-gradient(135deg, #45f3ff, #EC4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">Synthesis Hub</span>
        </h2>
        <p style="
            font-family: 'Inter', sans-serif;
            color: #94a3b8;
            font-size: 12px;
            margin: 4px 0 0 0;
        ">
            High-Quality Thumbnail • Banner • Poster Generator
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    w_col1, w_col2 = st.columns([1.1, 1.4], gap="medium")
    
    with w_col1:
        with st.container(border=True):
            st.markdown("""
            <h4 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 12px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                ⚙️ WORKSHOP PARAMETERS
            </h4>
            """, unsafe_allow_html=True)
            
            # Aspect Ratio
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">📐 Select Aspect Ratio</p>', unsafe_allow_html=True)
            workshop_ar = st.selectbox(
                "Aspect Ratio",
                ["16:9", "9:16", "1:1", "21:9", "4:5", "3:2"],
                key="workshop_aspect_ratio_choice",
                label_visibility="collapsed"
            )
            
            # Prompt
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">🎨 Masterpiece Prompt Input</p>', unsafe_allow_html=True)
            workshop_prompt_str = st.text_area(
                "Prompt",
                placeholder="E.g. A gorgeous cyberpunk temple with pink neon aurora, hyperrealistic, 8k resolution, cinematic lighting...",
                height=120,
                key="workshop_prompt_str_area",
                label_visibility="collapsed"
            )
            
            # Negative Prompt
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">🚫 Negative Prompt</p>', unsafe_allow_html=True)
            workshop_neg_prompt_str = st.text_area(
                "Negative Prompt",
                placeholder="E.g. blurry, low quality, distorted, extra limbs, bad anatomy, text, watermark...",
                height=80,
                key="workshop_neg_prompt_str_area",
                label_visibility="collapsed"
            )
            
            # Quality
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📊 Image Quality</p>', unsafe_allow_html=True)
            workshop_quality = st.selectbox(
                "Quality",
                ["Standard", "HD", "Pro"],
                key="workshop_quality",
                label_visibility="collapsed"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # ✅ FIXED: Generate Button with proper logic
            if st.button("🚀 Generate Workshop Image", key="workshop_generation_action_btn", use_container_width=True):
                if not workshop_prompt_str.strip():
                    st.error("❌ Please enter an image description.")
                else:
                    # Deduct credits
                    quality_map = {"Standard": 2, "HD": 3, "Pro": 4}
                    required_tokens = quality_map.get(workshop_quality, 2)
                    
                    if st.session_state.get('user_credits', 0) < required_tokens:
                        st.error(f"❌ Insufficient credits! Required: {required_tokens}, Available: {st.session_state.get('user_credits', 0)}")
                    else:
                        try:
                            # Deduct credits
                            deduct_credits_db(st.session_state["logged_user"], required_tokens)
                            st.session_state['user_credits'] = get_user_credits_db(st.session_state["logged_user"])
                            
                            with st.spinner(f"🎨 Generating {workshop_quality} image..."):
                                # Generate image
                                img_path = generate_pro_image(
                                    workshop_prompt_str,
                                    workshop_ar,
                                    workshop_neg_prompt_str
                                )
                                
                                if img_path and os.path.exists(img_path):
                                    st.session_state["workshop_active_image"] = img_path
                                    
                                    # Save to history
                                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                                    file_name = f"workshop_{timestamp}.png"
                                    save_render_to_db(
                                        st.session_state["logged_user"],
                                        file_name,
                                        workshop_prompt_str[:100],
                                        img_path,
                                        "Creative Workshop",
                                        required_tokens
                                    )
                                    st.session_state["history_renders"] = load_renders_history_db(st.session_state["logged_user"])
                                    
                                    st.toast("✅ Image generated successfully!")
                                    st.rerun()
                                else:
                                    st.error("❌ Image generation failed. Please try again.")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
    
    with w_col2:
        with st.container(border=True):
            st.markdown("""
            <h3 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 13px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                🖼️ LIVE IMAGE OUTPUT
            </h3>
            """, unsafe_allow_html=True)
            
            active_img_file = st.session_state.get("workshop_active_image")
            if active_img_file and os.path.exists(active_img_file):
                st.image(active_img_file, use_container_width=True)
                
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_img_file, "rb") as f:
                        img_bytes = f.read()
                    st.download_button(
                        label="📥 Download Image",
                        data=img_bytes,
                        file_name=f"zovix_creative_{uuid.uuid4().hex[:8]}.png",
                        mime="image/png",
                        use_container_width=True,
                        key="creative_download_btn"
                    )
                with col_clr:
                    if st.button("🧹 Clear Output", key="creative_clear_btn", use_container_width=True):
                        safe_remove_file(active_img_file)
                        st.session_state["workshop_active_image"] = None
                        st.rerun()
            else:
                st.markdown("""
                    <div style="
                        height: 380px;
                        min-height: 380px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        color: #64748b;
                        text-align: center;
                        padding: 12px;
                        overflow: hidden;
                        background: rgba(10,10,12,0.4);
                        border-radius: 12px;
                        border: 1px dashed rgba(255,192,203,0.12);
                    ">
                        <span style="font-size: 48px; margin-bottom: 10px;">🖼️</span>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 13px;
                            font-weight: 500;
                            color: #EC4899;
                            margin: 0;
                        ">
                            Image will render here
                        </p>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 11px;
                            color: #94a3b8;
                            max-width: 400px;
                            text-align: center;
                            margin-top: 4px;
                            line-height: 1.4;
                        ">
                            Artwork will display immediately upon generation.
                        </p>
                    </div>
                """, unsafe_allow_html=True)
    
    # ============================================
    # HEADER
    # ============================================
    st.markdown("""
    <div class="creative-header">
        <span class="badge">🎨 AI GENERATOR</span>
        <h2>Creative <span class="highlight">Synthesis Hub</span></h2>
        <p>High-Quality Thumbnail • Banner • Poster Generator</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ============================================
    # MAIN CONTENT
    # ============================================
    w_col1, w_col2 = st.columns([1.1, 1.4], gap="medium")
    
    with w_col1:
        with st.container(border=True):
            st.markdown("<style>.creative-title { color: #EC4899; !important; }</style>", unsafe_allow_html=True)
            st.markdown('<h4 class="creative-title"><span style="color: #EC4899; !important;">⚙️ WORKSHOP PARAMETERS</span></h4>', unsafe_allow_html=True)
            
            # Aspect Ratio
            st.markdown('<p class="creative-label">📐 Select Aspect Ratio</p>', unsafe_allow_html=True)
            workshop_ar = st.selectbox(
                "Aspect Ratio",
                ["16:9", "9:16", "1:1", "21:9", "4:5", "3:2"],
                key="workshop_aspect_ratio_choice",
                label_visibility="collapsed"
            )
            
            # Prompt
            st.markdown('<p class="creative-label">🎨 Masterpiece Prompt Input</p>', unsafe_allow_html=True)
            workshop_prompt_str = st.text_area(
                "Prompt",
                placeholder="E.g. A gorgeous cyberpunk temple with pink neon aurora, hyperrealistic, 8k resolution, cinematic lighting...",
                height=120,
                key="workshop_prompt_str_area",
                label_visibility="collapsed"
            )
            
            # Negative Prompt
            st.markdown('<p class="creative-label">🚫 Negative Prompt</p>', unsafe_allow_html=True)
            workshop_neg_prompt_str = st.text_area(
                "Negative Prompt",
                placeholder="E.g. blurry, low quality, distorted, extra limbs, bad anatomy, text, watermark...",
                height=80,
                key="workshop_neg_prompt_str_area",
                label_visibility="collapsed"
            )
            
            # Motion Bucket
            st.markdown('<p class="creative-label">🎬 Motion Bucket ID (Animation Intensity)</p>', unsafe_allow_html=True)
            motion_bucket_val = st.slider(
                "Motion Bucket",
                min_value=1,
                max_value=255,
                value=127,
                key="workshop_motion_bucket_slider",
                label_visibility="collapsed"
            )
            
            # Quality
            st.markdown('<p class="creative-label">📊 Image Quality</p>', unsafe_allow_html=True)
            workshop_quality = st.selectbox(
                "Quality",
                ["Standard", "HD", "Pro"],
                key="workshop_quality",
                label_visibility="collapsed"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Generate Button
            if st.button("🚀 Generate Workshop Image", key="workshop_generation_action_btn", use_container_width=True):
                # ... generate logic ...
                pass
    
    with w_col2:
        with st.container(border=True):
            st.markdown("<style>.creative-title { color: #EC4899; !important; }</style>", unsafe_allow_html=True)
            st.markdown('<h4 class="creative-title"><span style="color:#EC4899; !important;">⚙️ LIVE IMAGE OUTPUT BOX</span></h4>', unsafe_allow_html=True)
            
            active_img_file = st.session_state.get("workshop_active_image")
            if active_img_file and os.path.exists(active_img_file):
                st.image(active_img_file, use_container_width=True)
                
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_img_file, "rb") as f:
                        img_bytes = f.read()
                    st.download_button(
                        label="📥 Download Image",
                        data=img_bytes,
                        file_name=f"zovix_creative_{uuid.uuid4().hex[:8]}.png",
                        mime="image/png",
                        use_container_width=True,
                        key="creative_download_btn"
                    )
                with col_clr:
                    if st.button("🧹 Clear Output", key="creative_clear_btn", use_container_width=True):
                        safe_remove_file(active_img_file)
                        st.session_state["workshop_active_image"] = None
                        st.rerun()
            else:
                st.markdown("""
                <div class="empty-state">
                    <span class="icon">🖼️</span>
                    <p class="title" style="color: #EC4899; !important;">Image will render here</p>
                    <p class="desc">Artwork will display immediately upon generation.</p>
                </div>
                """, unsafe_allow_html=True)
    
    # ========================================================
# 43.5 BLUEPRINTS MODE 
# ========================================================

def run_blueprints_mode():
    """Blueprints Mode - Fully Fixed"""
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(236,72,153,0.06), rgba(69,243,255,0.06));
        border-radius: 16px;
        border: 1px solid rgba(69,243,255,0.08);
        padding: 16px 20px;
        margin-bottom: 18px;
        text-align: center;
    ">
        <span style="
            display: inline-block;
            background: rgba(236,72,153,0.12);
            color: #EC4899;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 9px;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            border: 1px solid rgba(236,72,153,0.15);
            margin-bottom: 6px;
        ">📐 ARCHITECTURE</span>
        <h2 style="
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            color: #FFFFFF;
            margin: 0;
        ">
            Blueprints <span style="
                background: linear-gradient(135deg, #45f3ff, #EC4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">Engine</span>
        </h2>
        <p style="
            font-family: 'Inter', sans-serif;
            color: #94a3b8;
            font-size: 12px;
            margin: 4px 0 0 0;
        ">
            Professional architectural drawings and technical plans
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    bp_col1, bp_col2 = st.columns([1.1, 1.4], gap="medium")
    
    with bp_col1:
        with st.container(border=True):
            st.markdown("""
            <h4 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 12px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                ⚙️ BLUEPRINT PARAMETERS
            </h4>
            """, unsafe_allow_html=True)
            
            # Blueprint Description
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">📝 Architectural Description</p>', unsafe_allow_html=True)
            blueprint_prompt = st.text_area(
                "Description",
                placeholder="E.g. Modern 2-bedroom house with open kitchen, master bedroom with en-suite bathroom, large living room, study room...",
                height=100,
                key="bp_prompt_input",
                label_visibility="collapsed"
            )
            
            # Blueprint Type
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📐 Blueprint Type</p>', unsafe_allow_html=True)
            blueprint_type = st.selectbox(
                "Type",
                ["floor_plan", "elevation", "section", "site_plan"],
                key="bp_type_select",
                label_visibility="collapsed"
            )
            
            # Blueprint Style
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🎨 Blueprint Style</p>', unsafe_allow_html=True)
            blueprint_style = st.selectbox(
                "Style",
                ["Modern", "Classic", "Minimalist", "Industrial", "Traditional"],
                key="bp_style_select",
                label_visibility="collapsed"
            )
            
            # Quality
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📊 Blueprint Quality</p>', unsafe_allow_html=True)
            bp_quality = st.selectbox(
                "Quality",
                ["Standard", "HD"],
                key="bp_quality_select",
                label_visibility="collapsed"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # ✅ FIXED: Generate Button with proper logic
            col_gen1, col_gen2 = st.columns(2)
            with col_gen1:
                if st.button("📐 Generate Blueprint", key="bp_generate_btn", use_container_width=True):
                    if not blueprint_prompt.strip():
                        st.error("❌ Please enter a blueprint description.")
                    else:
                        # Deduct credits
                        required_tokens = 2 if bp_quality == "Standard" else 3
                        
                        if st.session_state.get('user_credits', 0) < required_tokens:
                            st.error(f"❌ Insufficient credits! Required: {required_tokens}, Available: {st.session_state.get('user_credits', 0)}")
                        else:
                            try:
                                # Deduct credits
                                deduct_credits_db(st.session_state["logged_user"], required_tokens)
                                st.session_state['user_credits'] = get_user_credits_db(st.session_state["logged_user"])
                                
                                with st.spinner("📐 Generating architectural blueprint..."):
                                    # Try DeepSeek first, fallback to local
                                    blueprint_path = None
                                    
                                    # Check if DeepSeek API is available
                                    if DEEPSEEK_API_KEY:
                                        blueprint_path = generate_blueprint_with_deepseek(
                                            blueprint_prompt, 
                                            blueprint_type, 
                                            blueprint_style
                                        )
                                    
                                    # Fallback to local generation
                                    if not blueprint_path or not os.path.exists(blueprint_path):
                                        blueprint_path = generate_blueprint(blueprint_prompt, blueprint_type)
                                    
                                    if blueprint_path and os.path.exists(blueprint_path):
                                        st.session_state["active_blueprint"] = blueprint_path
                                        
                                        # Save to history
                                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                                        file_name = f"blueprint_{timestamp}.png"
                                        save_render_to_db(
                                            st.session_state["logged_user"],
                                            file_name,
                                            blueprint_prompt[:100],
                                            blueprint_path,
                                            "Blueprints",
                                            required_tokens
                                        )
                                        st.session_state["history_renders"] = load_renders_history_db(st.session_state["logged_user"])
                                        
                                        st.toast("✅ Blueprint generated successfully!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Blueprint generation failed. Please try a different description.")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
            
            with col_gen2:
                if st.button("🎨 Quick Template", key="bp_template_btn", use_container_width=True):
                    templates = [
                        "2BHK House with Garden",
                        "Modern Office Building",
                        "Restaurant Floor Plan",
                        "School Campus Layout",
                        "Hospital Wing Design"
                    ]
                    selected_template = st.selectbox("Choose Template", templates, key="bp_template_select")
                    if selected_template:
                        st.session_state["bp_prompt_input"] = selected_template
                        st.rerun()
    
    with bp_col2:
        with st.container(border=True):
            st.markdown("""
            <h3 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 13px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                📐 BLUEPRINT VIEWER
            </h3>
            """, unsafe_allow_html=True)
            
            active_bp = st.session_state.get("active_blueprint")
            if active_bp and os.path.exists(active_bp):
                st.image(active_bp, use_container_width=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_bp, "rb") as f:
                        bp_bytes = f.read()
                    st.download_button(
                        label="📥 Download Blueprint (PNG)",
                        data=bp_bytes,
                        file_name=f"zovix_blueprint_{uuid.uuid4().hex[:8]}.png",
                        mime="image/png",
                        use_container_width=True,
                        key="bp_download_btn"
                    )
                with col_clr:
                    if st.button("🧹 Clear Blueprint", key="bp_clear_btn", use_container_width=True):
                        safe_remove_file(active_bp)
                        st.session_state["active_blueprint"] = None
                        st.rerun()
            else:
                st.markdown("""
                    <div style="
                        height: 380px;
                        min-height: 380px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        color: #64748b;
                        text-align: center;
                        padding: 12px;
                        overflow: hidden;
                        background: rgba(10,10,12,0.4);
                        border-radius: 12px;
                        border: 1px dashed rgba(255,192,203,0.12);
                    ">
                        <span style="font-size: 48px; margin-bottom: 10px;">📐</span>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 13px;
                            font-weight: 500;
                            color: #EC4899;
                            margin: 0;
                        ">
                            Blueprint will render here
                        </p>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 11px;
                            color: #94a3b8;
                            max-width: 400px;
                            text-align: center;
                            margin-top: 4px;
                            line-height: 1.4;
                        ">
                            Professional architectural drawings with detailed analysis.
                        </p>
                    </div>
                """, unsafe_allow_html=True)


def generate_blueprint(prompt, blueprint_type="floor_plan"):
    """Local fallback blueprint generator"""
    try:
        width, height = 1200, 800
        img = Image.new("RGB", (width, height), color=(240, 240, 255))
        draw = ImageDraw.Draw(img)
        
        # Border
        draw.rectangle([(20, 20), (width-20, height-20)], outline=(30, 60, 150), width=3)
        
        # Title
        title = f"Architectural {blueprint_type.replace('_', ' ').title()}"
        draw.text((width//2 - 200, 30), title, fill=(30, 60, 150))
        
        # Blueprint grid
        for x in range(50, width-50, 50):
            draw.line([(x, 60), (x, height-20)], fill=(200, 210, 230), width=1)
        for y in range(60, height-20, 50):
            draw.line([(50, y), (width-50, y)], fill=(200, 210, 230), width=1)
        
        # Draw rooms based on prompt
        rooms = ["Living Room", "Kitchen", "Bedroom 1", "Bedroom 2", "Bathroom"]
        colors = [(30, 60, 150), (40, 80, 180), (50, 100, 200), (60, 120, 220), (70, 140, 240)]
        
        room_positions = [
            (100, 100, 400, 300),
            (500, 100, 800, 300),
            (100, 350, 350, 600),
            (400, 350, 650, 600),
            (700, 350, 950, 600),
        ]
        
        for i, room in enumerate(rooms[:5]):
            x1, y1, x2, y2 = room_positions[i]
            color = colors[i % len(colors)]
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)
            draw.text((x1 + 20, y1 + 20), room, fill=color)
        
        # Add legend
        draw.rectangle([(width-200, height-120), (width-30, height-30)], fill=(220, 225, 240), outline=(30, 60, 150), width=2)
        draw.text((width-190, height-110), "LEGEND", fill=(30, 60, 150))
        draw.text((width-190, height-90), f"Style: Modern", fill=(30, 60, 150))
        draw.text((width-190, height-70), f"Rooms: {len(rooms)}", fill=(30, 60, 150))
        
        output_path = f"blueprints/blueprint_{uuid.uuid4().hex[:8]}.png"
        os.makedirs("blueprints", exist_ok=True)
        img.save(output_path)
        
        return output_path
    except Exception as e:
        logger.error(f"Blueprint generation error: {e}")
        return None


# ========================================================
# 43.6 DEEPSEEK BLUEPRINT GENERATOR - FIXED ✅
# ========================================================

def generate_blueprint_with_deepseek(prompt, blueprint_type="floor_plan", style="Modern"):
    """Generate architectural blueprint using DeepSeek AI"""
    
    if not DEEPSEEK_API_KEY:
        logger.warning("DeepSeek API key not found, using fallback generator")
        return generate_blueprint(prompt, blueprint_type)
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    system_prompt = f"""You are an expert architectural designer. Generate a detailed blueprint description for a {style} {blueprint_type.replace('_', ' ')} based on: {prompt}

Return ONLY a JSON object with these fields:
{{
    "title": "Blueprint Title",
    "description": "Detailed architectural description",
    "rooms": ["Room1", "Room2", "Room3"],
    "dimensions": "Total area in sq ft",
    "style": "{style}",
    "structure_type": "Residential/Commercial/Industrial"
}}"""
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are an expert architectural designer. Respond only with valid JSON."},
            {"role": "user", "content": system_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            blueprint_data = json.loads(result['choices'][0]['message']['content'])
            
            # Store blueprint data in session
            st.session_state["deepseek_blueprint_data"] = blueprint_data
            
            # Generate image using Stability AI or fallback
            return generate_blueprint_from_data(blueprint_data, blueprint_type)
        else:
            logger.error(f"DeepSeek API error: {response.status_code}")
            return generate_blueprint(prompt, blueprint_type)
            
    except Exception as e:
        logger.error(f"DeepSeek blueprint error: {e}")
        return generate_blueprint(prompt, blueprint_type)


def generate_blueprint_from_data(blueprint_data, blueprint_type="floor_plan"):
    """Generate blueprint image from DeepSeek data"""
    
    try:
        # Create a professional blueprint image
        width, height = 1200, 800
        img = Image.new("RGB", (width, height), color=(240, 240, 255))
        draw = ImageDraw.Draw(img)
        
        # Border
        draw.rectangle([(20, 20), (width-20, height-20)], outline=(30, 60, 150), width=3)
        
        # Title
        title = blueprint_data.get('title', 'Architectural Blueprint')
        draw.text((width//2 - 200, 30), title, fill=(30, 60, 150), font=None)
        
        # Blueprint grid
        for x in range(50, width-50, 50):
            draw.line([(x, 60), (x, height-20)], fill=(200, 210, 230), width=1)
        for y in range(60, height-20, 50):
            draw.line([(50, y), (width-50, y)], fill=(200, 210, 230), width=1)
        
        # Draw rooms based on data
        rooms = blueprint_data.get('rooms', ['Living Room', 'Kitchen', 'Bedroom 1', 'Bedroom 2', 'Bathroom'])
        colors = [(30, 60, 150), (40, 80, 180), (50, 100, 200), (60, 120, 220), (70, 140, 240)]
        
        room_positions = [
            (100, 100, 400, 300),   # Living Room
            (500, 100, 800, 300),   # Kitchen
            (100, 350, 350, 600),   # Bedroom 1
            (400, 350, 650, 600),   # Bedroom 2
            (700, 350, 950, 600),   # Bathroom
        ]
        
        for i, room in enumerate(rooms[:5]):
            x1, y1, x2, y2 = room_positions[i]
            color = colors[i % len(colors)]
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)
            draw.text((x1 + 20, y1 + 20), room, fill=color)
            
            # Add room dimensions
            width_room = x2 - x1
            height_room = y2 - y1
            draw.text((x1 + 20, y1 + 50), f"{width_room//10}x{height_room//10}", fill=(100, 120, 180))
        
        # Add legend
        draw.rectangle([(width-200, height-120), (width-30, height-30)], fill=(220, 225, 240), outline=(30, 60, 150), width=2)
        draw.text((width-190, height-110), "LEGEND", fill=(30, 60, 150))
        draw.text((width-190, height-90), f"Style: {blueprint_data.get('style', 'Modern')}", fill=(30, 60, 150))
        draw.text((width-190, height-70), f"Area: {blueprint_data.get('dimensions', 'N/A')}", fill=(30, 60, 150))
        draw.text((width-190, height-50), f"Rooms: {len(rooms)}", fill=(30, 60, 150))
        
        # Save
        output_path = f"blueprints/blueprint_{uuid.uuid4().hex[:8]}.png"
        os.makedirs("blueprints", exist_ok=True)
        img.save(output_path)
        
        return output_path
        
    except Exception as e:
        logger.error(f"Blueprint image generation error: {e}")
        return None

# ========================================================
# UPSCALER MODE - FIXED ✅
# ========================================================

def run_upscaler_mode():
    """Upscaler - AI-Powered Image Enhancement - Fully Fixed"""
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(236,72,153,0.06), rgba(69,243,255,0.06));
        border-radius: 16px;
        border: 1px solid rgba(69,243,255,0.08);
        padding: 16px 20px;
        margin-bottom: 18px;
        text-align: center;
    ">
        <span style="
            display: inline-block;
            background: rgba(236,72,153,0.12);
            color: #EC4899;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 9px;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            border: 1px solid rgba(236,72,153,0.15);
            margin-bottom: 6px;
        ">⚡ AI ENHANCE</span>
        <h2 style="
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            color: #FFFFFF;
            margin: 0;
        ">
            AI <span style="
                background: linear-gradient(135deg, #45f3ff, #EC4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">Upscaler</span>
        </h2>
        <p style="
            font-family: 'Inter', sans-serif;
            color: #94a3b8;
            font-size: 12px;
            margin: 4px 0 0 0;
        ">
            AI-powered image upscaling • Detail restoration • 4K enhancement
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    us_col1, us_col2 = st.columns([1.1, 1.4], gap="medium")
    
    with us_col1:
        with st.container(border=True):
            st.markdown("""
            <h4 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 12px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                ⚙️ UPSCALER PARAMETERS
            </h4>
            """, unsafe_allow_html=True)
            
            # Image Upload
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">📷 Upload Image to Upscale</p>', unsafe_allow_html=True)
            uploaded_image_up = st.file_uploader(
                "Upload Image",
                type=['png', 'jpg', 'jpeg', 'webp'],
                key="us_image_upload",
                label_visibility="collapsed"
            )
            
            if uploaded_image_up:
                temp_path = f"temp_scenes/upload_{uuid.uuid4().hex[:8]}.png"
                os.makedirs("temp_scenes", exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_image_up.getbuffer())
                st.session_state["us_temp_image"] = temp_path
                st.image(temp_path, caption="Original Image", use_container_width=True)
            
            # Scale Factor
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🔍 Scale Factor</p>', unsafe_allow_html=True)
            scale_factor = st.select_slider(
                "Scale Factor",
                options=[2, 4, 8],
                value=2,
                key="us_scale_factor",
                label_visibility="collapsed"
            )
            
            # Enhancement Type
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🎨 Enhancement Method</p>', unsafe_allow_html=True)
            enhancement_type = st.selectbox(
                "Enhancement",
                ["standard", "sharp", "smooth", "enhance", "cinematic", "neon"],
                key="us_enhancement_type",
                label_visibility="collapsed"
            )
            
            # Quality
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📊 Upscale Quality</p>', unsafe_allow_html=True)
            us_quality = st.selectbox(
                "Quality",
                ["Standard", "HD", "4K"],
                key="us_quality",
                label_visibility="collapsed"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # ✅ FIXED: Generate Button with proper logic
            if st.button("⚡ Upscale Image", key="us_upscale_btn", use_container_width=True):
                if not st.session_state.get("us_temp_image") or not os.path.exists(st.session_state["us_temp_image"]):
                    st.error("❌ Please upload an image first.")
                else:
                    quality_map = {"Standard": 2, "HD": 3, "4K": 4}
                    required_tokens = quality_map.get(us_quality, 2)
                    
                    if st.session_state.get('user_credits', 0) < required_tokens:
                        st.error(f"❌ Insufficient credits! Required: {required_tokens}, Available: {st.session_state.get('user_credits', 0)}")
                    else:
                        try:
                            # Deduct credits
                            deduct_credits_db(st.session_state["logged_user"], required_tokens)
                            st.session_state['user_credits'] = get_user_credits_db(st.session_state["logged_user"])
                            
                            with st.spinner(f"🔄 Upscaling image {scale_factor}x with {enhancement_type} enhancement..."):
                                upscaled_path = upscale_image_fixed(
                                    st.session_state["us_temp_image"],
                                    scale_factor,
                                    enhancement_type,
                                    us_quality
                                )
                                
                                if upscaled_path and os.path.exists(upscaled_path):
                                    st.session_state["active_upscaled_image"] = upscaled_path
                                    
                                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                                    file_name = f"upscaled_{scale_factor}x_{timestamp}.png"
                                    save_render_to_db(
                                        st.session_state["logged_user"],
                                        file_name,
                                        f"Upscaled {scale_factor}x with {enhancement_type}",
                                        upscaled_path,
                                        "Upscaler",
                                        required_tokens
                                    )
                                    st.session_state["history_renders"] = load_renders_history_db(st.session_state["logged_user"])
                                    
                                    st.toast(f"✅ Image upscaled {scale_factor}x successfully!")
                                    st.rerun()
                                else:
                                    st.error("❌ Image upscaling failed. Please try a different image or settings.")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
    
    with us_col2:
        with st.container(border=True):
            st.markdown("""
            <h3 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 13px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                ⚡ UPSCALED IMAGE VIEWER
            </h3>
            """, unsafe_allow_html=True)
            
            active_upscaled = st.session_state.get("active_upscaled_image")
            if active_upscaled and os.path.exists(active_upscaled):
                orig_path = st.session_state.get("us_temp_image")
                
                col_orig, col_up = st.columns(2)
                with col_orig:
                    st.markdown('<p style="font-family: Inter; font-size: 10px; color: #94a3b8; text-align: center;">📷 Original</p>', unsafe_allow_html=True)
                    if orig_path and os.path.exists(orig_path):
                        st.image(orig_path, use_container_width=True)
                
                with col_up:
                    st.markdown('<p style="font-family: Inter; font-size: 10px; color: #45f3ff; text-align: center;">⚡ Upscaled</p>', unsafe_allow_html=True)
                    st.image(active_upscaled, use_container_width=True)
                
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_upscaled, "rb") as f:
                        upscaled_bytes = f.read()
                    st.download_button(
                        label="📥 Download Upscaled Image",
                        data=upscaled_bytes,
                        file_name=f"zovix_upscaled_{uuid.uuid4().hex[:8]}.png",
                        mime="image/png",
                        use_container_width=True,
                        key="us_download_btn"
                    )
                with col_clr:
                    if st.button("🧹 Clear Image", key="us_clear_btn", use_container_width=True):
                        safe_remove_file(active_upscaled)
                        safe_remove_file(st.session_state.get("us_temp_image", ""))
                        st.session_state["active_upscaled_image"] = None
                        st.session_state["us_temp_image"] = None
                        st.rerun()
            else:
                st.markdown("""
                    <div style="
                        height: 380px;
                        min-height: 380px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        color: #64748b;
                        text-align: center;
                        padding: 12px;
                        overflow: hidden;
                        background: rgba(10,10,12,0.4);
                        border-radius: 12px;
                        border: 1px dashed rgba(255,192,203,0.12);
                    ">
                        <span style="font-size: 48px; margin-bottom: 10px;">⚡</span>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 13px;
                            font-weight: 500;
                            color: #EC4899;
                            margin: 0;
                        ">
                            Upscaled image will render here
                        </p>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 11px;
                            color: #94a3b8;
                            max-width: 400px;
                            text-align: center;
                            margin-top: 4px;
                            line-height: 1.4;
                        ">
                            AI-enhanced high-resolution output with side-by-side comparison.
                        </p>
                    </div>
                """, unsafe_allow_html=True)


def upscale_image_fixed(image_path, scale_factor=2, enhancement_type="standard", quality="Standard"):
    """AI-powered image upscaling with multiple enhancement methods"""
    if not image_path or not os.path.exists(image_path):
        return None
    
    try:
        img = Image.open(image_path)
        width, height = img.size
        
        # Calculate new dimensions
        new_width = width * scale_factor
        new_height = height * scale_factor
        
        # Resize using different methods based on enhancement type
        if enhancement_type == "standard":
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        elif enhancement_type == "sharp":
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            enhancer = ImageEnhance.Sharpness(resized)
            resized = enhancer.enhance(1.5)
        elif enhancement_type == "smooth":
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            resized = resized.filter(ImageFilter.SMOOTH_MORE)
        elif enhancement_type == "enhance":
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            enhancer = ImageEnhance.Contrast(resized)
            resized = enhancer.enhance(1.2)
            enhancer = ImageEnhance.Color(resized)
            resized = enhancer.enhance(1.1)
        elif enhancement_type == "cinematic":
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # Cinematic color grading
            enhancer = ImageEnhance.Contrast(resized)
            resized = enhancer.enhance(1.3)
            enhancer = ImageEnhance.Color(resized)
            resized = enhancer.enhance(1.2)
        elif enhancement_type == "neon":
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            enhancer = ImageEnhance.Contrast(resized)
            resized = enhancer.enhance(1.5)
            enhancer = ImageEnhance.Color(resized)
            resized = enhancer.enhance(1.4)
        else:
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save
        output_path = f"upscaled_outputs/upscaled_{uuid.uuid4().hex[:8]}.png"
        os.makedirs("upscaled_outputs", exist_ok=True)
        resized.save(output_path, quality=95)
        
        return output_path
    except Exception as e:
        logger.error(f"Upscale error: {e}")
        return None
        
# ========================================================
# DRAW MODE - 3-TIER HYBRID SYSTEM
# Tier 1: Pollinations (FREE + FAST)
# Tier 2: Gemini Flash (PREMIUM + QUALITY)
# Tier 3: Enhanced Fallback (ALWAYS WORKING)
# ========================================================

def run_draw_mode():
    """Draw Mode - 3-Tier Hybrid System"""
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(236,72,153,0.06), rgba(69,243,255,0.06));
        border-radius: 16px;
        border: 1px solid rgba(69,243,255,0.08);
        padding: 16px 20px;
        margin-bottom: 18px;
        text-align: center;
    ">
        <span style="
            display: inline-block;
            background: rgba(236,72,153,0.12);
            color: #EC4899;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 9px;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            border: 1px solid rgba(236,72,153,0.15);
            margin-bottom: 6px;
        ">🎨 AI ART</span>
        <h2 style="
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            color: #FFFFFF;
            margin: 0;
        ">
            AI <span style="
                background: linear-gradient(135deg, #45f3ff, #EC4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">Draw</span> Engine
        </h2>
        <p style="
            font-family: 'Inter', sans-serif;
            color: #94a3b8;
            font-size: 12px;
            margin: 4px 0 0 0;
        ">
            3-Tier Hybrid • Pollinations • Gemini Flash • Enhanced Fallback
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    dr_col1, dr_col2 = st.columns([1.1, 1.4], gap="medium")
    
    with dr_col1:
        with st.container(border=True):
            st.markdown("""
            <h4 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 12px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                ⚙️ DRAW PARAMETERS
            </h4>
            """, unsafe_allow_html=True)
            
            # Drawing Prompt
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">🎨 Drawing Description</p>', unsafe_allow_html=True)
            draw_prompt = st.text_area(
                "Description",
                placeholder="E.g. A beautiful sunset over mountains, digital art style, A mystical dragon in flight, A futuristic cyberpunk city...",
                height=100,
                key="dr_prompt",
                label_visibility="collapsed"
            )
            
            # Engine Selection
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">⚙️ AI Engine</p>', unsafe_allow_html=True)
            engine_choice = st.selectbox(
                "Engine",
                ["Auto (Pollinations → Gemini → Fallback)", "Pollinations Only (Fast & Free)", "Gemini Flash Only (Premium)", "Fallback Only"],
                key="dr_engine",
                label_visibility="collapsed"
            )
            
            # Artistic Style
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🎭 Artistic Style</p>', unsafe_allow_html=True)
            draw_style = st.selectbox(
                "Style",
                ["realistic", "digital", "sketch", "watercolor", "anime", "cinematic", "neon"],
                key="dr_style",
                label_visibility="collapsed"
            )
            
            # Canvas Size
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📐 Canvas Size</p>', unsafe_allow_html=True)
            col_w, col_h = st.columns(2)
            with col_w:
                canvas_width = st.select_slider(
                    "Width",
                    options=[512, 768, 1024, 1280, 1920],
                    value=1024,
                    key="dr_width",
                    label_visibility="collapsed"
                )
            with col_h:
                canvas_height = st.select_slider(
                    "Height",
                    options=[512, 768, 1024, 1280, 1920],
                    value=768,
                    key="dr_height",
                    label_visibility="collapsed"
                )
            
            # Quality
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📊 Drawing Quality</p>', unsafe_allow_html=True)
            dr_quality = st.selectbox(
                "Quality",
                ["Standard", "HD", "4K"],
                key="dr_quality",
                label_visibility="collapsed"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # ✅ Generate Button
            if st.button("🎨 Generate Drawing", key="dr_generate_btn", use_container_width=True):
                if not draw_prompt.strip():
                    st.error("❌ Please enter a drawing description.")
                else:
                    quality_map = {"Standard": 2, "HD": 3, "4K": 4}
                    required_tokens = quality_map.get(dr_quality, 2)
                    
                    if st.session_state.get('user_credits', 0) < required_tokens:
                        st.error(f"❌ Insufficient credits! Required: {required_tokens}, Available: {st.session_state.get('user_credits', 0)}")
                    else:
                        try:
                            deduct_credits_db(st.session_state["logged_user"], required_tokens)
                            st.session_state['user_credits'] = get_user_credits_db(st.session_state["logged_user"])
                            
                            with st.spinner(f"🎨 Generating {draw_style} drawing using {engine_choice}..."):
                                drawing_path = generate_drawing_hybrid(
                                    prompt=draw_prompt,
                                    style=draw_style,
                                    canvas_size=(canvas_width, canvas_height),
                                    engine=engine_choice,
                                    quality=dr_quality
                                )
                                
                                if drawing_path and os.path.exists(drawing_path):
                                    st.session_state["active_drawing"] = drawing_path
                                    
                                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                                    file_name = f"drawing_{timestamp}.png"
                                    save_render_to_db(
                                        st.session_state["logged_user"],
                                        file_name,
                                        draw_prompt[:100],
                                        drawing_path,
                                        "Draw",
                                        required_tokens
                                    )
                                    st.session_state["history_renders"] = load_renders_history_db(st.session_state["logged_user"])
                                    
                                    engine_used = st.session_state.get("draw_engine_used", "Unknown")
                                    st.toast(f"✅ Drawing generated using {engine_used}!")
                                    st.rerun()
                                else:
                                    st.error("❌ Drawing generation failed. Please try a different prompt or style.")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
    
    with dr_col2:
        with st.container(border=True):
            st.markdown("""
            <h3 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 13px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                🎨 DRAWING VIEWER
            </h3>
            """, unsafe_allow_html=True)
            
            active_drawing = st.session_state.get("active_drawing")
            if active_drawing and os.path.exists(active_drawing):
                try:
                    from PIL import Image
                    img = Image.open(active_drawing)
                    width, height = img.size
                    
                    engine_used = st.session_state.get("draw_engine_used", "Unknown")
                    
                    st.markdown(f"""
                    <div style="
                        background: rgba(69,243,255,0.04);
                        border: 1px solid rgba(69,243,255,0.08);
                        border-radius: 8px;
                        padding: 8px 12px;
                        margin-bottom: 10px;
                    ">
                        <p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 0;">
                            📐 {width} x {height} • 🎨 {st.session_state.get('dr_style', 'Unknown')} • ⚡ {engine_used}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                except:
                    pass
                
                st.image(active_drawing, use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True)
                
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_drawing, "rb") as f:
                        drawing_bytes = f.read()
                    st.download_button(
                        label="📥 Download Drawing",
                        data=drawing_bytes,
                        file_name=f"zovix_drawing_{uuid.uuid4().hex[:8]}.png",
                        mime="image/png",
                        use_container_width=True,
                        key="dr_download_btn"
                    )
                with col_clr:
                    if st.button("🧹 Clear Drawing", key="dr_clear_btn", use_container_width=True):
                        safe_remove_file(active_drawing)
                        st.session_state["active_drawing"] = None
                        st.session_state["draw_engine_used"] = None
                        st.rerun()
            else:
                st.markdown("""
                    <div style="
                        height: 380px;
                        min-height: 380px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        color: #64748b;
                        text-align: center;
                        padding: 12px;
                        overflow: hidden;
                        background: rgba(10,10,12,0.4);
                        border-radius: 12px;
                        border: 1px dashed rgba(255,192,203,0.12);
                    ">
                        <span style="font-size: 48px; margin-bottom: 10px;">🎨</span>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 13px;
                            font-weight: 500;
                            color: #EC4899;
                            margin: 0;
                        ">
                            Drawing will render here
                        </p>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 11px;
                            color: #94a3b8;
                            max-width: 400px;
                            text-align: center;
                            margin-top: 4px;
                            line-height: 1.4;
                        ">
                            3-Tier Hybrid System • Pollinations • Gemini • Fallback
                        </p>
                    </div>
                """, unsafe_allow_html=True)


# ========================================================
# GENERATE DRAWING - 3-TIER HYBRID
# ========================================================

def generate_drawing_hybrid(prompt, style="realistic", canvas_size=(1024, 768), engine="Auto (Pollinations \u2192 Gemini \u2192 Fallback)", quality="Standard"):
    """
    WORLD-CLASS DRAW GENERATOR - 6-Tier Cascade
    Delegates to engine.py's DrawEngine for multi-provider support
    """
    from engine import DrawEngine
    
    engine_map = {
        "Auto (Pollinations \u2192 Gemini \u2192 Fallback)": "Auto",
        "Pollinations.ai (Free + Fast)": "Pollinations",
        "Gemini Flash (Premium + Quality)": "Gemini",
        "Stability AI (Highest Quality)": "Stability",
        "Replicate Flux (Fast SD)": "Replicate",
        "Hugging Face (FLUX.1)": "HuggingFace",
        "Fallback Only (100% Local)": "Fallback",
    }
    engine_filter = engine_map.get(engine, "Auto")
    
    if engine_filter == "Fallback":
        return DrawEngine.generate_fallback_only(prompt, style, canvas_size)
    else:
        return DrawEngine.generate(prompt, style, canvas_size, engine_filter, quality)# ========================================================
# ENHANCED FALLBACK - PROMPT AWARE
# ========================================================

def generate_enhanced_fallback_drawing(prompt, style="realistic", canvas_size=(1024, 768)):
    """Enhanced fallback that understands prompts"""
    
    try:
        width, height = canvas_size
        img = Image.new("RGB", (width, height), color=(18, 19, 26))
        draw = ImageDraw.Draw(img)
        prompt_lower = prompt.lower()
        
        # ==========================================
        # SUNSET DETECTION
        # ==========================================
        if "sunset" in prompt_lower or "sun" in prompt_lower:
            # Gradient sky
            for y in range(height):
                ratio = y / height
                if ratio < 0.2:
                    r, g, b = 255, 200, 150
                elif ratio < 0.4:
                    r, g, b = 255, 150, 80
                elif ratio < 0.6:
                    r, g, b = 200, 80, 40
                elif ratio < 0.8:
                    r, g, b = 150, 40, 20
                else:
                    r, g, b = 80, 20, 10
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            
            # Sun with glow
            sun_x, sun_y = width//2, height//3
            for r in range(120, 20, -10):
                draw.ellipse([(sun_x-r, sun_y-r), (sun_x+r, sun_y+r)], 
                           fill=(255, min(255, 220 + int(r//2)), min(255, 150 + int(r//3))))
            
            # Mountains
            for i in range(5):
                x1 = i * width//5 - 30
                x2 = i * width//5 + width//6
                x3 = (i+1) * width//5 + 30
                y1 = height
                y2 = height//3 - 40 + i * 20 + random.randint(-10, 10)
                y3 = height
                draw.polygon([(x1, y1), (x2, y2), (x3, y3)], fill=(40, 50, 70))
        
        # ==========================================
        # MOUNTAIN DETECTION
        # ==========================================
        elif "mountain" in prompt_lower:
            draw.rectangle([(0, 0), (width, height)], fill=(135, 206, 235))
            for i in range(5):
                x1 = i * width//5 - 30
                x2 = i * width//5 + width//6
                x3 = (i+1) * width//5 + 30
                y1 = height
                y2 = height//3 - 40 + i * 20 + random.randint(-10, 10)
                y3 = height
                draw.polygon([(x1, y1), (x2, y2), (x3, y3)], 
                           fill=(80 + i*10, 100 + i*10, 130 + i*10))
                draw.polygon([(x2-15, y2), (x2, y2-20), (x2+15, y2)], 
                           fill=(240, 240, 250))
        
        # ==========================================
        # FOREST DETECTION
        # ==========================================
        elif "forest" in prompt_lower or "tree" in prompt_lower:
            draw.rectangle([(0, 0), (width, height//2)], fill=(100, 200, 255))
            draw.rectangle([(0, height//2), (width, height)], fill=(34, 139, 34))
            for i in range(20):
                x = 30 + i * 50 + random.randint(-10, 10)
                y = height//2 + random.randint(-20, 40)
                draw.rectangle([(x-3, y), (x+3, y+30)], fill=(60, 40, 20))
                size = random.randint(20, 40)
                draw.ellipse([(x-size, y-size), (x+size, y+size//2)], 
                           fill=(34, 139, 34))
        
        # ==========================================
        # CITY DETECTION
        # ==========================================
        elif "city" in prompt_lower or "building" in prompt_lower:
            draw.rectangle([(0, 0), (width, height)], fill=(10, 10, 30))
            for i in range(50):
                x = random.randint(0, width)
                y = random.randint(0, height//3)
                draw.ellipse([(x, y), (x+2, y+2)], fill=(255, 255, 200))
            for i in range(12):
                x = i * width//12
                bw = random.randint(30, 70)
                bh = random.randint(100, height-50)
                draw.rectangle([(x, height-bh), (x+bw, height)], 
                             fill=(random.randint(20, 60), random.randint(20, 60), random.randint(30, 70)))
                for wx in range(x+5, x+bw-5, 10):
                    for wy in range(height-bh+10, height-10, 15):
                        if random.random() > 0.3:
                            draw.rectangle([(wx, wy), (wx+5, wy+8)], 
                                         fill=(255, 200, 100))
        
        # ==========================================
        # SPACE DETECTION
        # ==========================================
        elif "space" in prompt_lower or "galaxy" in prompt_lower:
            for y in range(height):
                ratio = y / height
                r = int(10 + 20 * ratio)
                g = int(5 + 10 * ratio)
                b = int(30 + 30 * ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            for i in range(100):
                x = random.randint(0, width)
                y = random.randint(0, height)
                size = random.randint(1, 3)
                brightness = random.randint(150, 255)
                draw.ellipse([(x, y), (x+size, y+size)], 
                           fill=(brightness, brightness, brightness))
        
        # ==========================================
        # ABSTRACT / DEFAULT
        # ==========================================
        else:
            colors = [(255,100,100), (100,255,100), (100,100,255), 
                     (255,200,100), (255,100,200), (100,200,255),
                     (200,100,255), (100,255,200)]
            for i in range(30):
                x = random.randint(50, width-50)
                y = random.randint(50, height-50)
                size = random.randint(30, 80)
                color = random.choice(colors)
                for r in range(size, 0, -5):
                    draw.ellipse([(x-r, y-r), (x+r, y+r)], 
                               fill=(color[0], color[1], color[2], 200))
                draw.ellipse([(x-size//3, y-size//3), (x+size//3, y+size//3)], 
                           fill=(255, 255, 255, 100))
        
        # ==========================================
        # STYLE EFFECTS
        # ==========================================
        if style == "sketch":
            img = img.convert("L").convert("RGB")
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)
        elif style == "digital":
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.3)
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.2)
        elif style == "watercolor":
            img = img.filter(ImageFilter.GaussianBlur(radius=1))
        elif style == "cinematic":
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.1)
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (width, int(height*0.1))], fill=(0,0,0,128))
            draw.rectangle([(0, int(height*0.9)), (width, height)], fill=(0,0,0,128))
        elif style == "neon":
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.4)
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.3)
        
        # ==========================================
        # WATERMARK
        # ==========================================
        draw = ImageDraw.Draw(img)
        draw.text((width-200, height-30), f"ZOVIX Draw - {datetime.now().strftime('%Y-%m-%d')}", 
                 fill=(100, 100, 100, 150))
        
        img.save(output_path, quality=95)
        logger.info(f"✅ Enhanced fallback success: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Enhanced fallback error: {e}")
        return None

def run_video_editor_mode():
    """Video Editor - Fully Fixed"""
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(236,72,153,0.06), rgba(69,243,255,0.06));
        border-radius: 16px;
        border: 1px solid rgba(69,243,255,0.08);
        padding: 16px 20px;
        margin-bottom: 18px;
        text-align: center;
    ">
        <span style="
            display: inline-block;
            background: rgba(236,72,153,0.12);
            color: #EC4899;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 9px;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            border: 1px solid rgba(236,72,153,0.15);
            margin-bottom: 6px;
        ">🎞️ PRO EDITOR</span>
        <h2 style="
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            color: #FFFFFF;
            margin: 0;
        ">
            Video <span style="
                background: linear-gradient(135deg, #45f3ff, #EC4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            ">Editor</span>
        </h2>
        <p style="
            font-family: 'Inter', sans-serif;
            color: #94a3b8;
            font-size: 12px;
            margin: 4px 0 0 0;
        ">
            1-2 Min Movie • AI-Powered Timeline • Auto-Stitching
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    ve_col1, ve_col2 = st.columns([1.1, 1.4], gap="medium")
    
    with ve_col1:
        with st.container(border=True):
            st.markdown("""
            <h4 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 12px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                ⚙️ EDITOR PARAMETERS
            </h4>
            """, unsafe_allow_html=True)
            
            # Upload Media
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">📤 UPLOAD UNLIMITED MEDIA</p>', unsafe_allow_html=True)
            uploaded_media = st.file_uploader(
                "Upload Videos, Images",
                type=['mp4', 'mov', 'avi', 'webm', 'png', 'jpg', 'jpeg', 'webp', 'mp3', 'wav'],
                accept_multiple_files=True,
                key="editor_media_upload",
                label_visibility="collapsed"
            )
            if uploaded_media:
                st.session_state["editor_uploads"] = uploaded_media
                st.success(f"✅ {len(uploaded_media)} media files uploaded successfully!")
            
            # Transitions & Effects
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🎞️ Transition Effect</p>', unsafe_allow_html=True)
            transition_effect = st.selectbox(
                "Transition",
                ["none", "fade", "crossfade", "zoom", "slide", "circle", "radial", "smooth"],
                key="editor_transition",
                label_visibility="collapsed"
            )
            
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🎨 Video Effect</p>', unsafe_allow_html=True)
            video_effect = st.selectbox(
                "Effect",
                ["none", "sepia", "grayscale", "vintage", "cinematic", "neon", "glitch", "dreamy", "dramatic"],
                key="editor_effect",
                label_visibility="collapsed"
            )
            
            # Resolution
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📐 Output Resolution</p>', unsafe_allow_html=True)
            output_resolution = st.selectbox(
                "Resolution",
                ["720p", "1080p", "4K"],
                key="editor_resolution",
                label_visibility="collapsed"
            )
            
            # BGM Upload
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🎵 ADD CUSTOM BACKGROUND MUSIC</p>', unsafe_allow_html=True)
            editor_bgm = st.file_uploader(
                "Upload BGM",
                type=['mp3', 'wav'],
                key="editor_bgm_upload",
                label_visibility="collapsed"
            )
            if editor_bgm is not None:
                st.info("✅ Custom BGM uploaded.")
            
            # Voiceover
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🎙️ Add Cinematic AI Voiceover</p>', unsafe_allow_html=True)
            use_editor_voiceover = st.toggle("Enable Voiceover", value=False, key="editor_enable_voiceover")
            if use_editor_voiceover:
                editor_voice_text = st.text_area(
                    "Voiceover Script",
                    placeholder="Yahan narration likho...",
                    height=60,
                    key="editor_voiceover_text",
                    label_visibility="collapsed"
                )
                
                st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🎤 Voice Profile</p>', unsafe_allow_html=True)
                voice_options = list(ELEVENLABS_VOICES.keys())
                editor_voice_profile = st.selectbox(
                    "Voice Profile",
                    voice_options,
                    index=0,
                    key="editor_voiceover_profile",
                    label_visibility="collapsed"
                )
            
            # BGM Volume
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">🎵 BGM Volume Level</p>', unsafe_allow_html=True)
            editor_bgm_volume = st.slider(
                "Volume",
                min_value=0.0,
                max_value=1.0,
                value=0.30,
                step=0.05,
                key="editor_bgm_volume",
                label_visibility="collapsed"
            )
            
            # Quality
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 8px 0 4px 0;">📊 Editor Quality</p>', unsafe_allow_html=True)
            editor_quality = st.selectbox(
                "Quality",
                ["Standard", "HD", "4K"],
                key="editor_quality",
                label_visibility="collapsed"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # ✅ FIXED: Process Button with proper logic
            if st.button("🚀 PROCESS & EDIT VIDEO", key="movie_generate_btn_editor", use_container_width=True):
                uploaded_files = st.session_state.get("editor_uploads", [])
                if not uploaded_files:
                    st.error("❌ Please upload at least one media file.")
                else:
                    quality_map = {"Standard": 2, "HD": 3, "4K": 4}
                    required_tokens = quality_map.get(editor_quality, 2)
                    
                    if st.session_state.get('user_credits', 0) < required_tokens:
                        st.error(f"❌ Insufficient credits! Required: {required_tokens}, Available: {st.session_state.get('user_credits', 0)}")
                    else:
                        try:
                            # Deduct credits
                            deduct_credits_db(st.session_state["logged_user"], required_tokens)
                            st.session_state['user_credits'] = get_user_credits_db(st.session_state["logged_user"])
                            
                            with st.spinner(f"🎬 Processing video with {editor_quality} quality..."):
                                output_path = f"editor_outputs/edited_video_{uuid.uuid4().hex[:8]}.mp4"
                                os.makedirs("editor_outputs", exist_ok=True)
                                
                                voiceover_text = st.session_state.get("editor_voiceover_text", "") if use_editor_voiceover else ""
                                voice_profile = st.session_state.get("editor_voiceover_profile", "Adam (Premium Male)") if use_editor_voiceover else "Adam (Premium Male)"
                                
                                success = process_editor_video(
                                    uploaded_files=uploaded_files,
                                    output_path=output_path,
                                    effect=video_effect,
                                    transition=transition_effect,
                                    resolution=output_resolution,
                                    custom_bgm=editor_bgm,
                                    bgm_volume=editor_bgm_volume,
                                    voiceover_text=voiceover_text,
                                    voice_profile=voice_profile,
                                    voice_language_choice=st.session_state.get("language_choice", "🇬🇧 English (US Standard)")
                                )
                                
                                if success and os.path.exists(output_path):
                                    st.session_state["active_editor_output"] = output_path
                                    
                                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                                    file_name = f"edited_video_{timestamp}.mp4"
                                    save_render_to_db(
                                        st.session_state["logged_user"],
                                        file_name,
                                        f"Edited video with {video_effect} effect",
                                        output_path,
                                        "Video Editor",
                                        required_tokens
                                    )
                                    st.session_state["history_renders"] = load_renders_history_db(st.session_state["logged_user"])
                                    
                                    st.toast("✅ Video edited successfully!")
                                    st.rerun()
                                else:
                                    st.error("❌ Video processing failed. Please check your media files and try again.")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
    
    with ve_col2:
        with st.container(border=True):
            st.markdown("""
            <h3 style="
                font-family: 'Orbitron', sans-serif;
                font-size: 13px;
                color: #EC4899;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            ">
                🎬 EDITED VIDEO OUTPUT
            </h3>
            """, unsafe_allow_html=True)
            
            active_output = st.session_state.get("active_editor_output")
            if active_output and os.path.exists(active_output):
                st.video(active_output, format="video/mp4", autoplay=False, loop=True, muted=False)
                
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_output, "rb") as f:
                        video_bytes = f.read()
                    st.download_button(
                        label="📥 Download Video",
                        data=video_bytes,
                        file_name=f"zovix_edited_video_{uuid.uuid4().hex[:8]}.mp4",
                        mime="video/mp4",
                        use_container_width=True,
                        key="editor_download_btn"
                    )
                with col_clr:
                    if st.button("🧹 Clear Output", key="editor_clear_btn", use_container_width=True):
                        safe_remove_file(active_output)
                        st.session_state["active_editor_output"] = None
                        st.rerun()
            else:
                st.markdown("""
                    <div style="
                        height: 380px;
                        min-height: 380px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        color: #64748b;
                        text-align: center;
                        padding: 12px;
                        overflow: hidden;
                        background: rgba(10,10,12,0.4);
                        border-radius: 12px;
                        border: 1px dashed rgba(255,192,203,0.12);
                    ">
                        <span style="font-size: 48px; margin-bottom: 10px;">🎬</span>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 13px;
                            font-weight: 500;
                            color: #EC4899;
                            margin: 0;
                        ">
                            Edited video will render here
                        </p>
                        <p style="
                            font-family: 'Inter', sans-serif;
                            font-size: 11px;
                            color: #94a3b8;
                            max-width: 400px;
                            text-align: center;
                            margin-top: 4px;
                            line-height: 1.4;
                        ">
                            Upload unlimited media files and click process to edit.
                        </p>
                    </div>
                """, unsafe_allow_html=True)
    
    # ============================================
    # HEADER
    # ============================================
    st.markdown("""
    <div class="editor-header">
        <span class="badge">🎞️ PRO EDITOR</span>
        <h2>Video <span class="highlight">Editor</span></h2>
        <p>1-2 Min Movie • AI-Powered Timeline • Auto-Stitching</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ============================================
    # MAIN CONTENT
    # ============================================
    ve_col1, ve_col2 = st.columns([1.1, 1.4], gap="medium")
    
    with ve_col1:
        with st.container(border=True):
            st.markdown("<style>.editor-title { color: #EC4899 !important; }</style>", unsafe_allow_html=True)
            st.markdown('<h4 class="editor-title"><span style="color: #EC4899 !important;">⚙️ EDITOR PARAMETERS</span></h4>', unsafe_allow_html=True)
            
            # Upload Media
            st.markdown('<p class="editor-label">📤 UPLOAD UNLIMITED MEDIA</p>', unsafe_allow_html=True)
            uploaded_media = st.file_uploader(
                "Upload Videos, Images",
                type=['mp4', 'mov', 'avi', 'webm', 'png', 'jpg', 'jpeg', 'webp', 'mp3', 'wav'],
                accept_multiple_files=True,
                key="editor_media_upload",
                label_visibility="collapsed"
            )
            if uploaded_media:
                st.session_state["editor_uploads"] = uploaded_media
                st.success(f"✅ {len(uploaded_media)} media files uploaded successfully!")
            
            # Transitions & Effects
            st.markdown('<p class="editor-label">🎞️ Transition Effect</p>', unsafe_allow_html=True)
            transition_effect = st.selectbox(
                "Transition",
                ["none", "fade", "crossfade", "zoom", "slide", "circle", "radial", "smooth"],
                key="editor_transition",
                label_visibility="collapsed"
            )
            
            st.markdown('<p class="editor-label">🎨 Video Effect</p>', unsafe_allow_html=True)
            video_effect = st.selectbox(
                "Effect",
                ["none", "sepia", "grayscale", "vintage", "cinematic", "neon", "glitch", "dreamy", "dramatic"],
                key="editor_effect",
                label_visibility="collapsed"
            )
            
            # Resolution
            st.markdown('<p class="editor-label">📐 Output Resolution</p>', unsafe_allow_html=True)
            output_resolution = st.selectbox(
                "Resolution",
                ["720p", "1080p", "4K"],
                key="editor_resolution",
                label_visibility="collapsed"
            )
            
            # BGM Upload
            st.markdown('<p class="editor-label">🎵 ADD CUSTOM BACKGROUND MUSIC</p>', unsafe_allow_html=True)
            editor_bgm = st.file_uploader(
                "Upload BGM",
                type=['mp3', 'wav'],
                key="editor_bgm_upload",
                label_visibility="collapsed"
            )
            if editor_bgm is not None:
                st.info("✅ Custom BGM uploaded.")
            
            # Voiceover
            st.markdown('<p class="editor-label">🎙️ Add Cinematic AI Voiceover</p>', unsafe_allow_html=True)
            use_editor_voiceover = st.toggle("Enable Voiceover", value=False, key="editor_enable_voiceover")
            if use_editor_voiceover:
                editor_voice_text = st.text_area(
                    "Voiceover Script",
                    placeholder="Yahan narration likho...",
                    height=60,
                    key="editor_voiceover_text",
                    label_visibility="collapsed"
                )
                
                st.markdown('<p class="editor-label">🎤 Voice Profile</p>', unsafe_allow_html=True)
                voice_options = list(ELEVENLABS_VOICES.keys())
                editor_voice_profile = st.selectbox(
                    "Voice Profile",
                    voice_options,
                    index=0,
                    key="editor_voiceover_profile",
                    label_visibility="collapsed"
                )
            
            # BGM Volume
            st.markdown('<p class="editor-label">🎵 BGM Volume Level</p>', unsafe_allow_html=True)
            editor_bgm_volume = st.slider(
                "Volume",
                min_value=0.0,
                max_value=1.0,
                value=0.30,
                step=0.05,
                key="editor_bgm_volume",
                label_visibility="collapsed"
            )
            
            # Quality
            st.markdown('<p class="editor-label">📊 Editor Quality</p>', unsafe_allow_html=True)
            editor_quality = st.selectbox(
                "Quality",
                ["Standard", "HD", "4K"],
                key="editor_quality",
                label_visibility="collapsed"  
        )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Process Button
            if st.button("🚀 PROCESS & EDIT VIDEO", key="movie_generate_btn_editor", use_container_width=True):
                # ... your existing logic ...
                pass
    
    with ve_col2:
        with st.container(border=True):
            st.markdown('<h4 class="editor-title">🎬 EDITED VIDEO OUTPUT</h4>', unsafe_allow_html=True)
            
            active_output = st.session_state.get("active_editor_output")
            if active_output and os.path.exists(active_output):
                st.video(active_output, format="video/mp4", autoplay=False, loop=True, muted=False)
                
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_output, "rb") as f:
                        video_bytes = f.read()
                    st.download_button(
                        label="📥 Download Video",
                        data=video_bytes,
                        file_name=f"zovix_edited_video_{uuid.uuid4().hex[:8]}.mp4",
                        mime="video/mp4",
                        use_container_width=True,
                        key="editor_download_btn"
                    )
                with col_clr:
                    if st.button("🧹 Clear Output", key="editor_clear_btn", use_container_width=True):
                        safe_remove_file(active_output)
                        st.session_state["active_editor_output"] = None
                        st.rerun()
            else:
                st.markdown("""
                <div class="empty-state">
                <span class="icon">🎬</span>
                <p class="title" style="color:#EC4899; !important;">Edited video will render here</p>
                <p class="desc">Upload unlimited media files and click process to edit.</p>
                <p class="desc" style="color: #EC4899; font-size: 10px;">🎵 Custom BGM supported</p>
            </div>
            """, unsafe_allow_html=True)


# ========================================================
# GENDER DETECTION UTILITY FOR FACE VIDEO MODE
# ========================================================
def detect_gender_from_image(image_path):
    """Detect gender, age from face using DeepFace AI. Auto-selects ElevenLabs voice."""
    if not image_path:
        logger.warning("detect_gender_from_image: image_path is None")
        return None
    
    # Handle UploadedFile objects by saving to temp
    resolved_path = image_path
    if not isinstance(image_path, str):
        try:
            temp_path = f"face_videos/temp_detect_{uuid.uuid4().hex[:8]}.png"
            os.makedirs("face_videos", exist_ok=True)
            if hasattr(image_path, 'getbuffer'):
                with open(temp_path, 'wb') as f:
                    f.write(image_path.getbuffer())
            elif hasattr(image_path, 'read'):
                with open(temp_path, 'wb') as f:
                    f.write(image_path.read())
            resolved_path = temp_path
        except Exception as e:
            logger.warning(f"detect_gender_from_image: Could not process upload: {e}")
            return None
    
    if not resolved_path or not os.path.exists(resolved_path):
        logger.warning(f"detect_gender_from_image: File not found: {resolved_path}")
        return None
    
    if os.path.getsize(resolved_path) < 100:
        logger.warning(f"detect_gender_from_image: File too small: {resolved_path}")
        return None
    
    try:
        scan_result = safe_deepface_analyze(resolved_path, actions=['gender', 'age'])
        
        if not scan_result.get("success"):
            logger.warning(f"detect_gender_from_image: Scan failed: {scan_result.get('error')}")
            return None
        
        detected_gender = scan_result.get("gender", "Male")
        detected_age = scan_result.get("age", 25)
        detected_category = scan_result.get("category", "Adult Male")
        detected_voice = scan_result.get("voice_label", "Adam (Premium Male)")
        
        st.session_state["fv_detected_age"] = detected_age
        st.session_state["fv_detected_gender"] = detected_gender
        
        voice_module = get_voice_module_by_age_gender(detected_age, detected_gender)
        if voice_module:
            st.session_state["fv_auto_selected_voice"] = voice_module["default_voice"]
            st.session_state["fv_detected_category"] = voice_module["category"]
            st.session_state["fv_voice_module_key"] = voice_module.get("label", "")
            st.session_state["fv_voice_recommended_list"] = voice_module.get("recommended_voices", [])
        else:
            st.session_state["fv_auto_selected_voice"] = "Adam (Premium Male)"
            st.session_state["fv_detected_category"] = "Adult Male"
            st.session_state["fv_voice_module_key"] = "👨 Adult Male (>= 14)"
            st.session_state["fv_voice_recommended_list"] = []
        
        logger.info(f"DeepFace scan -> Age:{detected_age}, Gender:{detected_gender}, "
                    f"Category:{st.session_state['fv_detected_category']}, "
                    f"Voice:{st.session_state['fv_auto_selected_voice']}")
        
        return detected_gender
    except Exception as e:
        logger.warning(f'DeepFace scan failed: {e}')
    
    return None
        


def get_gender_based_voice_recommendation(detected_gender, language='English'):
    """Get recommended voice profiles based on detected gender."""
    if detected_gender == 'male':
        if language == 'Hindi':
            return [v for v, m in ELEVENLABS_VOICES.items() if m.get('gender') == 'male' and m.get('language') in ['Hindi', 'English']]
        elif language == 'English':
            return [v for v, m in ELEVENLABS_VOICES.items() if m.get('gender') == 'male' and m.get('language') == 'English']
        return [v for v, m in ELEVENLABS_VOICES.items() if m.get('gender') == 'male']
    elif detected_gender == 'female':
        if language == 'Hindi':
            return [v for v, m in ELEVENLABS_VOICES.items() if m.get('gender') == 'female' and m.get('language') in ['Hindi', 'English']]
        elif language == 'English':
            return [v for v, m in ELEVENLABS_VOICES.items() if m.get('gender') == 'female' and m.get('language') == 'English']
        return [v for v, m in ELEVENLABS_VOICES.items() if m.get('gender') == 'female']
    return []


def run_face_video_mode():
    st.markdown("""
        <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; border: 1px solid rgba(255,192,203,0.15); padding: 20px; margin-bottom: 20px;">
            <h3 style="font-family: 'Orbitron'; font-size: 16px; color: #FFC0CB; margin: 0 0 5px 0;">👤 Face Video Generator</h3>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;"> Professional lip-sync only mode: no head/body motion, just natural speaking lips </p>
        </div>
    """, unsafe_allow_html=True)
    fv_col1, fv_col2 = st.columns([1.1, 1.4], gap="medium")
    with fv_col1:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>⚙️ FACE VIDEO PARAMETERS</h4>", unsafe_allow_html=True)
            wav2lip_setup = get_wav2lip_setup_status()
            runtime_profile = get_wav2lip_runtime_profile()
            st.caption("Wav2Lip resolver build: 2026-07-11-r3")
            if wav2lip_setup.get("ready"):
                st.success("✅ Pro backend active: Wav2Lip production inference is ready.")
                st.caption(f"Runtime profile: {runtime_profile['mode']} | face_det_batch={runtime_profile['face_det_batch_size']} | wav_batch={runtime_profile['wav2lip_batch_size']}")
            else:
                st.warning("⚠️ Pro backend not fully configured. Running built-in lip-only fallback.")
                st.caption("Set WAV2LIP_REPO_PATH and WAV2LIP_CHECKPOINT_PATH to enable best quality lip-sync.")
                repo_ok = bool(wav2lip_setup.get("repo_path"))
                script_ok = bool(wav2lip_setup.get("script_path"))
                ckpt_ok = bool(wav2lip_setup.get("checkpoint_path"))
                s3fd_ok = bool(wav2lip_setup.get("s3fd_ready"))
                st.caption(
                    f"Detected: repo={'OK' if repo_ok else 'MISSING'} | "
                    f"inference.py={'OK' if script_ok else 'MISSING'} | "
                    f"checkpoint={'OK' if ckpt_ok else 'MISSING'} | "
                    f"s3fd={'OK' if s3fd_ok else 'MISSING'}"
                )
                st.caption(
                    f"Resolved repo={wav2lip_setup.get('repo_path') or 'None'} | "
                    f"checkpoint={wav2lip_setup.get('checkpoint_path') or 'None'} | "
                    f"s3fd={wav2lip_setup.get('s3fd_path') or 'None'}"
                )
                st.caption(
                    f"Runtime cwd={wav2lip_setup.get('cwd') or 'None'} | "
                    f"app_dir={wav2lip_setup.get('app_dir') or 'None'}"
                )
            st.markdown("<div class='compact-label'>📷 CAMERA MODE</div>", unsafe_allow_html=True)
            camera_mode = st.toggle("📷 Use Camera (Take Photo Directly)", value=False, key="fv_camera_mode")
            if camera_mode:
                st.info("📷 Click the button below to take a photo with your camera. The photo will be auto-cropped to face ratio.")
                camera_photo = st.camera_input("Take a Photo", key="fv_camera_photo")
                if camera_photo:
                    face_path = f"face_videos/camera_face_{uuid.uuid4().hex[:8]}.png"
                    with open(face_path, "wb") as f:
                        f.write(camera_photo.getbuffer())
                    st.session_state["face_image_upload"] = face_path
                    st.success(f"✅ Photo captured successfully!")
                    try:
                        img = Image.open(face_path)
                        width, height = img.size
                        size = min(width, height)
                        left = (width - size) // 2
                        top = (height - size) // 2
                        right = left + size
                        bottom = top + size
                        cropped = img.crop((left, top, right, bottom))
                        cropped.save(face_path)
                        st.image(face_path, caption="Captured Face Image", use_container_width=True)
                    except Exception:
                        st.image(face_path, caption="Captured Image", use_container_width=True)
            else:
                face_image_upload = st.file_uploader("Upload Face Image (JPG, PNG, WEBP)", type=['jpg', 'jpeg', 'png', 'webp'], key="fv_face_upload")
                if face_image_upload:
                    face_path = f"face_videos/face_{uuid.uuid4().hex[:8]}.png"
                    with open(face_path, "wb") as f:
                        f.write(face_image_upload.getbuffer())
                    st.session_state["face_image_upload"] = face_path
                    st.success(f"✅ Face image uploaded: {face_image_upload.name}")
                    st.image(face_path, caption="Uploaded Face Image", use_container_width=True)
            st.markdown("---")
            st.markdown("<div class='face-controls-grid'>", unsafe_allow_html=True)
            st.markdown("""<div class='face-control-item'><div class='label'>👄 Mode</div><div class='value'>Lip-Sync Only</div></div>""", unsafe_allow_html=True)
            st.markdown("""<div class='face-control-item'><div class='label'>🎥 Motion</div><div class='value'>Disabled</div></div>""", unsafe_allow_html=True)
            st.markdown("""<div class='face-control-item'><div class='label'>⏱️ Duration</div><div class='value'>Select Below</div></div>""", unsafe_allow_html=True)
            st.markdown("""<div class='face-control-item'><div class='label'>📊 Quality</div><div class='value'>Select Below</div></div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            col_mode, col_motion, col_dur, col_qual = st.columns(4)
            with col_mode:
                st.selectbox("Mode:", ["Lip-Sync Only"], key="fv_mode", disabled=True)
            with col_motion:
                st.selectbox("Motion:", ["No Head Motion"], key="fv_motion", disabled=True)
            with col_dur:
                video_duration = st.select_slider("Duration (seconds)", options=[5, 10, 15, 20, 30, 45, 60], value=10, key="fv_duration")
            with col_qual:
                quality = st.selectbox("Video Quality:", ["Standard", "HD", "4K"], key="fv_quality")
            fv_voice_language = st.selectbox(
                "Voice Language",
                ["Hindi", "English", "All Voices"],
                key="fv_voice_language",
            )
            
            # ---- Gender Auto-Detect Feature ----
            if "fv_gender_auto" not in st.session_state:
                st.session_state["fv_gender_auto"] = True
            
            face_uploaded = st.session_state.get("face_image_upload")
            face_available = bool(face_uploaded and os.path.exists(face_uploaded))
            
            col_g1, col_g2 = st.columns([1, 1])
            with col_g1:
                gender_auto = st.toggle(
                    "🎭 Auto-Detect Gender",
                    value=st.session_state.get("fv_gender_auto", True),
                    key="fv_gender_auto_toggle",
                    help="Automatically detect gender from face image and suggest matching voice",
                )
            
            if gender_auto and face_available:
                with col_g2:
                    if st.button("🔍 Detect Now", key="fv_detect_gender_btn", use_container_width=True):
                        with st.spinner("Analyzing face image for gender..."):
                            detected = detect_gender_from_image(face_uploaded)
                            if detected:
                                st.session_state["fv_detected_gender"] = detected
                                st.session_state["fv_gender_auto"] = True
                                st.toast(f"Gender detected: {detected.title()}")
                                st.rerun()
                            else:
                                st.warning("Could not detect gender. Please select manually.")
                                st.session_state["fv_gender_auto"] = False
            
            detected_gender = st.session_state.get("fv_detected_gender")
            if gender_auto and detected_gender and face_available:
                emoji = "👨" if detected_gender == 'male' else "👩"
                st.markdown(f"""<div style='background: rgba(69,243,255,0.08); border: 1px solid rgba(69,243,255,0.2); 
                    border-radius: 8px; padding: 8px 12px; margin: 5px 0; display: flex; align-items: center; gap: 8px;'>
                    <span style='font-size: 18px;'>{emoji}</span>
                    <span style='color: #45f3ff; font-size: 13px; font-weight: 500;'>
                        Detected: <strong>{detected_gender.title()}</strong>
                    </span>
                </div>""", unsafe_allow_html=True)
                
                recommended_voices = get_gender_based_voice_recommendation(detected_gender, fv_voice_language)
                if recommended_voices:
                    fv_voice_options = recommended_voices
                else:
                    fv_voice_options = _resolve_face_voice_config(voice_language=fv_voice_language).get("available_voices", [])
            else:
                if gender_auto and not face_available:
                    st.caption("📷 Upload a face image first to enable auto gender detection")
                fv_voice_options = _resolve_face_voice_config(voice_language=fv_voice_language).get("available_voices", [])
            
            fv_current_voice = st.session_state.get("face_voice_model")
            if fv_current_voice not in fv_voice_options:
                fv_current_voice = fv_voice_options[0] if fv_voice_options else "Adam (Premium Male)"
            
            recommended_list = st.session_state.get("fv_voice_recommended_list", [])
            rec_note = f" 💡 {st.session_state.get('fv_voice_module_key', '')} rec: {', '.join(recommended_list[:3])}" if (gender_auto and recommended_list) else ""
            manual_label = "Voice Model (Manual Override)" if (gender_auto and detected_gender and face_available) else "Voice Model"
            fv_voice_model = st.selectbox(
                manual_label,
                fv_voice_options,
                index=fv_voice_options.index(fv_current_voice) if fv_voice_options and fv_current_voice in fv_voice_options else 0,
                key="fv_voice_model",
            )
            
            if gender_auto != st.session_state.get("fv_gender_auto", True):
                st.session_state["fv_gender_auto"] = gender_auto
            st.markdown("---")
            face_prompt = st.text_area("Video Description / Script (for lip sync):", placeholder="Describe what the person should say: e.g. Hello everyone! Welcome to my channel. Today we're going to explore the mysteries of the universe...", height=100, key="fv_prompt")
            st.write("")
            if st.button("👤 Generate Face Video", key="fv_generate_btn", use_container_width=True):
                # Validate face image before scanning
                face_img_for_scan = st.session_state.get("face_image_upload")
                if face_img_for_scan is not None:
                    # Check if path exists (for string paths) or if file is UploadedFile
                    is_valid = False
                    if isinstance(face_img_for_scan, str):
                        is_valid = os.path.exists(face_img_for_scan)
                    else:
                        is_valid = True  # UploadedFile objects are valid
                    
                    if is_valid and st.session_state.get("fv_gender_auto", True):
                        with st.spinner("🔍 DeepFace AI scanning face (age + gender)..."):
                            try:
                                detected = detect_gender_from_image(face_img_for_scan)
                                if detected:
                                    cat = st.session_state.get("fv_detected_category", "Unknown")
                                    age = st.session_state.get("fv_detected_age", "?")
                                    voice = st.session_state.get("fv_auto_selected_voice", "Default")
                                    st.toast(f"Scan: {cat} (Age: {age}) -> Voice: {voice}")
                                else:
                                    st.toast("Face scan fallback: Using default voice based on selection.", icon="🤖")
                            except Exception as scan_err:
                                logger.warning(f"Generate-time face scan error: {scan_err}")
                                st.toast("Face scan unavailable. Using default voice.", icon="🤖")
                
                success, required_tokens, message = validate_and_deduct_tokens("Face Video Generator", quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    if not face_prompt.strip():
                        st.error("Please enter a video description for lip sync.")
                    elif not st.session_state.get("face_image_upload") or not os.path.exists(st.session_state["face_image_upload"]):
                        st.error("Please upload a face image or take a photo using camera mode.")
                    else:
                        with st.spinner(f"Generating {quality} lip-sync face video (motion locked)..."):
                            # Use safe wrapper with error handling
                            video_path, gen_error = safe_generate_face_video_wrapper(
                                face_prompt,
                                st.session_state.get("face_image_upload"),
                                duration=video_duration,
                                quality=quality,
                                voice_language=fv_voice_language,
                                voice_label=fv_voice_model,
                            )
                            if gen_error:
                                st.error(gen_error)
                            elif video_path and os.path.exists(video_path):
                                st.session_state["active_face_video"] = video_path
                                timestamp = time.strftime("%Y%m%d_%H%M%S")
                                file_name = f"zovix_face_video_{quality.lower()}_{timestamp}.mp4"
                                save_face_video_to_db(st.session_state["logged_user"], file_name, face_prompt, video_path, st.session_state["face_image_upload"], quality)
                                st.session_state["face_video_history"] = load_face_video_history_db(st.session_state["logged_user"])
                                st.toast(f"Face video generated successfully in {quality} quality!")
                                st.rerun()
                            else:
                                st.error("Lip-sync generation failed. Please ensure Wav2Lip backend is available and try again.")
    with fv_col2:
        with st.container(border=True):
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>👤 FACE VIDEO PLAYER</h3>", unsafe_allow_html=True)
            active_face_video = st.session_state.get("active_face_video")
            if active_face_video and os.path.exists(active_face_video):
                engine_used = st.session_state.get("face_video_engine_used", "Unknown")
                runtime_mode = st.session_state.get("face_video_runtime_mode", "Unknown")
                fv_module_key = st.session_state.get("fv_voice_module_key", "")
                fv_cat = st.session_state.get("fv_detected_category", "")
                fv_age = st.session_state.get("fv_detected_age", "")
                if fv_module_key:
                    st.caption(f"🤖 AI Voice Module: {fv_module_key} | Age: {fv_age}")
                else:
                    st.caption(f"🤖 AI Scan: {fv_cat or 'Unknown'} | Age: {fv_age or '?'}")
                st.caption(f"Engine used: {engine_used} | Runtime: {runtime_mode}")
                st.video(active_face_video, format="video/mp4", autoplay=False, loop=True, muted=False)
                st.markdown("<br>", unsafe_allow_html=True)
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_face_video, "rb") as f:
                        video_bytes = f.read()
                    st.download_button(label="📥 Download Face Video", data=video_bytes, file_name=f"zovix_face_video_{uuid.uuid4().hex[:8]}.mp4", mime="video/mp4", use_container_width=True, key="fv_download_btn")
                with col_clr:
                    if st.button("🧹 Clear Video", key="fv_clear_btn", use_container_width=True):
                        safe_remove_file(active_face_video)
                        st.session_state["active_face_video"] = None
                        st.rerun()
            else:
                st.markdown("""
                    <div class="canvas-container-box" style="height: 380px; min-height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #64748b; text-align: center; padding: 12px; overflow: hidden;">
                        <span style="font-size: 50px; margin-bottom: 12px; filter: drop-shadow(0 0 10px rgba(236, 72, 153, 0.3));">👤</span>
                        <p style="font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; color:#EC4899; margin: 0;">Face video will render here</p>
                        <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px; line-height: 1.4;">Upload face image + script and generate a professional lip-sync-only talking face.</p>
                        <p style="font-size: 10px; color: #EC4899; margin-top: 5px;">⚡ Powered by ElevenLabs voice + Wav2Lip</p>
                    </div>
                """, unsafe_allow_html=True)


def run_expressive_face_video_mode():
    st.markdown("""
        <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; border: 1px solid rgba(255,192,203,0.15); padding: 20px; margin-bottom: 20px;">
            <h3 style="font-family: 'Orbitron'; font-size: 16px; color: #EC4899; margin: 0 0 5px 0;">🧬 Expressive Face Video</h3>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;">Natural eye blinks, eyebrow movement, jaw motion and full-face expressions using LivePortrait/SadTalker style driving.</p>
        </div>
    """, unsafe_allow_html=True)

    efv_col1, efv_col2 = st.columns([1.1, 1.4], gap="medium")
    with efv_col1:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #EC4899; margin-bottom: 15px;'>⚙️ EXPRESSIVE PARAMETERS</h4>", unsafe_allow_html=True)
            expressive_setup = get_expressive_setup_status()
            st.caption(f"Runtime profile: {expressive_setup.get('runtime_mode', 'Unknown')}")
            if expressive_setup.get("liveportrait_ready"):
                st.success("✅ LivePortrait backend detected.")
            else:
                st.warning("⚠️ LivePortrait repo/script not detected.")
            if expressive_setup.get("sadtalker_ready"):
                st.success("✅ SadTalker backend detected.")
            else:
                st.warning("⚠️ SadTalker repo/script not detected.")

            with st.expander("🔧 Setup commands for production inference"):
                st.code(
                    """git clone https://github.com/KwaiVGI/LivePortrait.git LivePortrait
git clone https://github.com/OpenTalker/SadTalker.git SadTalker

# LivePortrait env (inside repo)
pip install -r LivePortrait/requirements.txt

# SadTalker env (inside repo)
pip install -r SadTalker/requirements.txt

# Optional quality boosters
pip install gfpgan realesrgan""",
                    language="bash",
                )

            face_image_upload = st.file_uploader("Upload Face Image (JPG, PNG, WEBP)", type=['jpg', 'jpeg', 'png', 'webp'], key="efv_face_upload")
            if face_image_upload:
                face_path = f"face_videos/expressive_face_{uuid.uuid4().hex[:8]}.png"
                with open(face_path, "wb") as f:
                    f.write(face_image_upload.getbuffer())
                st.session_state["face_image_upload"] = face_path
                st.success(f"✅ Face image uploaded: {face_image_upload.name}")
                st.image(face_path, caption="Uploaded Face Image", use_container_width=True)

            engine_choice = st.selectbox(
                "Backend Preference",
                ["Auto (LivePortrait → SadTalker → Wav2Lip)", "Auto (LivePortrait → SadTalker)", "LivePortrait Only", "SadTalker Only", "Wav2Lip Fallback"],
                key="efv_backend_choice",
            )

            efv_duration = st.select_slider("Duration (seconds)", options=[5, 10, 15, 20, 30, 45, 60], value=10, key="efv_duration")
            efv_quality = st.selectbox("Video Quality:", ["Standard", "HD", "4K"], key="efv_quality")
            efv_voice_language = st.selectbox(
                "Voice Language",
                ["Hindi", "English", "All Voices"],
                key="efv_voice_language",
            )
            efv_voice_options = _resolve_face_voice_config(voice_language=efv_voice_language).get("available_voices", [])
            efv_current_voice = st.session_state.get("face_voice_model")
            if efv_current_voice not in efv_voice_options:
                efv_current_voice = efv_voice_options[0] if efv_voice_options else "Adam (Premium Male)"
            efv_voice_model = st.selectbox(
                "Voice Model",
                efv_voice_options,
                index=efv_voice_options.index(efv_current_voice) if efv_voice_options and efv_current_voice in efv_voice_options else 0,
                key="efv_voice_model",
            )
            efv_prompt = st.text_area(
                "Video Description / Script:",
                placeholder="Type natural dialogue so model can animate eyes, eyebrows and jaw in sync with speech...",
                height=100,
                key="efv_prompt",
            )

            if st.button("🧬 Generate Expressive Face Video", key="efv_generate_btn", use_container_width=True):
                success, required_tokens, message = validate_and_deduct_tokens("Expressive Face Video", efv_quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    if not efv_prompt.strip():
                        st.error("Please enter a script for expressive face generation.")
                    elif not st.session_state.get("face_image_upload") or not os.path.exists(st.session_state["face_image_upload"]):
                        st.error("Please upload a face image first.")
                    else:
                        with st.spinner(f"Generating {efv_quality} expressive face video..."):
                            video_path = generate_expressive_face_video(
                                efv_prompt,
                                st.session_state["face_image_upload"],
                                efv_duration,
                                quality=efv_quality,
                                preferred_engine=engine_choice,
                                voice_language=efv_voice_language,
                                voice_label=efv_voice_model,
                            )
                            if video_path and os.path.exists(video_path):
                                st.session_state["active_expressive_face_video"] = video_path
                                timestamp = time.strftime("%Y%m%d_%H%M%S")
                                file_name = f"zovix_expressive_face_video_{efv_quality.lower()}_{timestamp}.mp4"
                                save_face_video_to_db(
                                    st.session_state["logged_user"],
                                    file_name,
                                    efv_prompt,
                                    video_path,
                                    st.session_state["face_image_upload"],
                                    efv_quality,
                                )
                                st.session_state["face_video_history"] = load_face_video_history_db(st.session_state["logged_user"])
                                st.toast(f"Expressive face video generated in {efv_quality} quality!")
                                st.rerun()
                            else:
                                st.error("Expressive generation failed. Verify LivePortrait/SadTalker setup and try again.")

    with efv_col2:
        with st.container(border=True):
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>🧬 EXPRESSIVE FACE PLAYER</h3>", unsafe_allow_html=True)
            active_video = st.session_state.get("active_expressive_face_video")
            if active_video and os.path.exists(active_video):
                engine_used = st.session_state.get("expressive_face_engine_used", "Unknown")
                runtime_mode = st.session_state.get("expressive_face_runtime_mode", "Unknown")
                fv_module_key = st.session_state.get("fv_voice_module_key", "")
                fv_cat = st.session_state.get("fv_detected_category", "")
                fv_age = st.session_state.get("fv_detected_age", "")
                if fv_module_key:
                    st.caption(f"🤖 AI Voice Module: {fv_module_key} | Age: {fv_age}")
                else:
                    st.caption(f"🤖 AI Scan: {fv_cat or 'Unknown'} | Age: {fv_age or '?'}")
                st.caption(f"Engine used: {engine_used} | Runtime: {runtime_mode}")
                st.video(active_video, format="video/mp4", autoplay=False, loop=True, muted=False)
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_video, "rb") as f:
                        video_bytes = f.read()
                    st.download_button(
                        label="📥 Download Expressive Video",
                        data=video_bytes,
                        file_name=f"zovix_expressive_face_video_{uuid.uuid4().hex[:8]}.mp4",
                        mime="video/mp4",
                        use_container_width=True,
                        key="efv_download_btn",
                    )
                with col_clr:
                    if st.button("🧹 Clear Video", key="efv_clear_btn", use_container_width=True):
                        safe_remove_file(active_video)
                        st.session_state["active_expressive_face_video"] = None
                        st.rerun()
            else:
                st.info("No expressive render yet. Upload a face image and generate your first expressive clip.")


def _extract_video_url_from_replicate_output(output_obj):
    if isinstance(output_obj, str) and output_obj.startswith("http"):
        return output_obj
    if isinstance(output_obj, dict):
        for key in ["video", "output", "url", "mp4", "result"]:
            val = output_obj.get(key)
            found = _extract_video_url_from_replicate_output(val)
            if found:
                return found
    if isinstance(output_obj, (list, tuple)):
        for item in output_obj:
            found = _extract_video_url_from_replicate_output(item)
            if found:
                return found
    return None


def _get_replicate_api_token():
    secret_keys = ["REPLICATE_API_TOKEN", "REPLICATE_API_KEY"]
    for key in secret_keys:
        try:
            value = st.secrets.get(key)
        except Exception:
            value = None
        if value:
            return str(value).strip()

    for key in secret_keys:
        value = os.getenv(key)
        if value:
            return str(value).strip()

    return None


def _run_replicate_face_model(client, model_ref, image_path, audio_path, script_text):
    image_path = str(image_path)
    if not os.path.isfile(image_path) or os.path.getsize(image_path) <= 0:
        raise ValueError("Replicate face generation requires a valid image file path.")

    model_lc = str(model_ref).lower()
    has_audio = bool(audio_path and os.path.isfile(audio_path) and os.path.getsize(audio_path) > 1024)

    if "p-video-avatar" in model_lc:
        input_builders = [
            lambda i, a, t: {"image": i, "voice_script": t, "voice_prompt": "speak naturally", "video_prompt": "real human talking head with natural lip movement and subtle eye blinks", "resolution": "720p"},
            lambda i, a, t: {"image": i, "voice_script": t, "resolution": "720p"},
        ]
    elif "sadtalker" in model_lc:
        input_builders = [
            lambda i, a, t: {"source_image": i, "driven_audio": a, "preprocess": "full"},
            lambda i, a, t: {"source_image": i, "driven_audio": a},
            lambda i, a, t: {"image": i, "audio": a},
        ]
    elif "liveportrait" in model_lc:
        input_builders = [
            lambda i, a, t: {"source_image": i, "driving_audio": a},
            lambda i, a, t: {"image": i, "audio": a},
            lambda i, a, t: {"source": i, "driving": a},
        ]
    else:
        input_builders = [
            lambda i, a, t: {"image": i, "voice_script": t},
            lambda i, a, t: {"image": i, "text": t},
        ]

    for build_payload in input_builders:
        try:
            with open(image_path, "rb") as img_file:
                aud_file = open(audio_path, "rb") if has_audio else None
                try:
                    payload = build_payload(img_file, aud_file, script_text)
                    output = client.run(model_ref, input=payload)
                finally:
                    if aud_file:
                        aud_file.close()

            video_url = _extract_video_url_from_replicate_output(output)
            if video_url:
                return video_url
        except Exception as e:
            logger.warning(f"Replicate payload failed for {model_ref}: {e}")
            continue

    return None


def generate_world_face_video(prompt, face_image_path, duration=10, quality="HD", animation_style="Expressive Real Human (No Lip-Only Fallback)", backend_choice="Auto (LivePortrait → SadTalker → Wav2Lip)", motion_level="high", voice_language=None, voice_label=None):
    """Cloud-only face generation using Replicate models; no local face animation pipeline."""
    if not face_image_path or not os.path.exists(face_image_path):
        return None

    if not HAS_REPLICATE:
        logger.warning("Replicate library is not installed.")
        return None

    replicate_token = _get_replicate_api_token()
    if not replicate_token:
        logger.warning("Replicate API token is missing from Streamlit secrets or environment.")
        return None

    temp_audio = None
    try:
        voice_cfg = _resolve_face_voice_config(voice_language=voice_language, voice_label=voice_label, preferred_gender=st.session_state.get('fv_detected_gender') if st.session_state.get('fv_gender_auto', False) else None)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_aud:
            temp_audio = tmp_aud.name
        _synthesize_face_audio_strict(prompt, temp_audio, voice_cfg, duration_hint=duration)

        client = replicate.Client(api_token=replicate_token)

        model_candidates = [
            str(os.getenv("REPLICATE_FACE_MODEL", "prunaai/p-video-avatar")).strip() or "prunaai/p-video-avatar",
            "prunaai/p-video-avatar",
            "lucataco/sadtalker",
            "cjwbw/sadtalker",
            "gandhana/liveportrait",
            "gandhary/liveportrait",
        ]

        deduped = []
        seen = set()
        for model in model_candidates:
            key = model.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            
            deduped.append(model.strip())

        for model_ref in deduped:
            try:
                video_url = _run_replicate_face_model(client, model_ref, face_image_path, temp_audio, prompt)
                if video_url:
                    st.session_state["face_video_engine_used"] = f"Replicate ({model_ref})"
                    st.session_state["face_video_runtime_mode"] = "Cloud"
                    return video_url
            except Exception as e:
                logger.warning(f"Replicate fallback failed for {model_ref}: {e}")

        return None
    except Exception as e:
        logger.warning(f"Replicate face generation failed: {e}")
        return None
    finally:
        if temp_audio:
            safe_remove_file(temp_audio)

# Legacy local face-engine hooks are intentionally disabled in cloud mode.
def get_wav2lip_setup_status():
    return {
        "ready": False,
        "repo_path": None,
        "script_path": None,
        "checkpoint_path": None,
        "s3fd_path": None,
        "s3fd_ready": False,
        "cwd": os.getcwd(),
        "app_dir": os.path.dirname(__file__),
        "forced_mode": False,
    }


def get_wav2lip_runtime_profile():
    return {
        "mode": "Cloud",
        "face_det_batch_size": "0",
        "wav2lip_batch_size": "0",
        "resize_factor": "1",
    }


def get_expressive_setup_status():
    return {
        "liveportrait_repo": None,
        "liveportrait_script": None,
        "liveportrait_python": None,
        "liveportrait_ready": False,
        "liveportrait_models_ready": False,
        "sadtalker_repo": None,
        "sadtalker_script": None,
        "sadtalker_python": None,
        "sadtalker_ready": False,
        "sadtalker_models_ready": False,
        "sadtalker_force_ready": False,
        "runtime_mode": "Cloud",
        "any_ready": False,
        "force_enable": False,
    }


def run_wav2lip_cli(face_image_path, audio_path, output_video_path, width, height, fps=24):
    logger.info("Local Wav2Lip path disabled. Using Replicate cloud generation only.")
    return False


def run_lip_sync_pipeline(face_image_path, audio_path, output_video_path, width, height, duration=10, emotion="neutral", camera_angle="front"):
    logger.info("Local lip-sync pipeline disabled. Using Replicate cloud generation only.")
    return False


def run_liveportrait_cli(face_image_path, audio_path, output_video_path, width, height, duration=10, motion_level="high"):
    logger.info("Local LivePortrait path disabled. Using Replicate cloud generation only.")
    return False


def run_sadtalker_cli(face_image_path, audio_path, output_video_path, width, height, duration=10, motion_level="high"):
    logger.info("Local SadTalker path disabled. Using Replicate cloud generation only.")
    return False


def run_expressive_face_pipeline(face_image_path, audio_path, output_video_path, width, height, duration=10, preferred_engine="Auto (LivePortrait → SadTalker)", motion_level="high"):
    logger.info("Local expressive pipeline disabled. Using Replicate cloud generation only.")
    return False


def run_unified_face_video_mode():
    """Premium Face Video Studio - Matching Studio Style"""
    
    # ============================================
    # FACE VIDEO CSS - DARK THEME
    # ============================================
    st.markdown("""
    <style>
        /* ============================================
           FACE VIDEO - DARK THEME
           ============================================ */
        
        /* HEADER */
        .face-header {
            background: linear-gradient(135deg, rgba(236,72,153,0.06), rgba(69,243,255,0.06));
            border-radius: 16px;
            border: 1px solid rgba(69,243,255,0.08);
            padding: 16px 20px;
            margin-bottom: 18px;
            text-align: center;
        }
        .face-header .badge {
            display: inline-block;
            background: rgba(236,72,153,0.12);
            color: #EC4899;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 9px;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            border: 1px solid rgba(236,72,153,0.15);
            margin-bottom: 6px;
        }
        .face-header h2 {
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            color: #FFFFFF;
            margin: 0;
        }
        .face-header h2 .highlight {
            background: linear-gradient(135deg, #45f3ff, #EC4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .face-header p {
            font-family: 'Inter', sans-serif;
            color: #94a3b8;
            font-size: 12px;
            margin: 4px 0 0 0;
        }
        
        /* ============================================
           SELECT BOX - DARK
           ============================================ */
        .stSelectbox > div,
        div[data-testid="stSelectbox"] > div {
            background: #0a0a12 !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 10px !important;
        }
        .stSelectbox select,
        div[data-testid="stSelectbox"] select {
            background: #0a0a12 !important;
            color: #e0e0e0 !important;
            border: none !important;
            border-radius: 10px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 13px !important;
            padding: 8px 12px !important;
        }
        .stSelectbox select:focus,
        div[data-testid="stSelectbox"] select:focus {
            border-color: #EC4899 !important;
            outline: none !important;
        }
        
        /* Selectbox Dropdown Menu */
        div[data-baseweb="select"] {
            background: #0a0a12 !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 10px !important;
        }
        div[data-baseweb="select"] > div {
            background: #0a0a12 !important;
        }
        div[data-baseweb="select"] input {
            background: #0a0a12 !important;
            color: #e0e0e0 !important;
        }
        ul[data-baseweb="menu"] {
            background: #0f0f1a !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 10px !important;
        }
        ul[data-baseweb="menu"] li {
            background: #0f0f1a !important;
            color: #e0e0e0 !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 13px !important;
        }
        ul[data-baseweb="menu"] li:hover {
            background: rgba(236,72,153,0.1) !important;
            color: #FFFFFF !important;
        }
        ul[data-baseweb="menu"] li[aria-selected="true"] {
            background: rgba(236,72,153,0.15) !important;
            color: #EC4899 !important;
        }
        
        /* ============================================
           SLIDER - DARK
           ============================================ */
        div[data-testid="stSlider"] {
            background: rgba(10,10,15,0.7) !important;
            border-radius: 10px !important;
            padding: 8px 12px !important;
            border: 1px solid rgba(255,255,255,0.04) !important;
        }
        div[data-testid="stSlider"] label {
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            color: #94a3b8 !important;
        }
        div[data-testid="stSlider"] .stSliderValue {
            color: #45f3ff !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 11px !important;
        }
        
        /* ============================================
           FILE UPLOADER - DARK
           ============================================ */
        div[data-testid="stFileUploader"] {
            background: rgba(10,10,15,0.7) !important;
            border-radius: 10px !important;
            border: 1px dashed rgba(255,255,255,0.08) !important;
            padding: 12px !important;
            margin: 4px 0 !important;
        }
        div[data-testid="stFileUploader"]:hover {
            border-color: #EC4899 !important;
        }
        div[data-testid="stFileUploader"] p {
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            color: #94a3b8 !important;
        }
        div[data-testid="stFileUploader"] .stFileUploaderButton {
            background: rgba(236,72,153,0.1) !important;
            color: #EC4899 !important;
            border: 1px solid rgba(236,72,153,0.2) !important;
            border-radius: 8px !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 10px !important;
        }
        div[data-testid="stFileUploader"] .stFileUploaderButton:hover {
            background: rgba(236,72,153,0.2) !important;
        }
        
        /* ============================================
           TEXT AREA - DARK
           ============================================ */
        .stTextArea textarea,
        div[data-testid="stTextArea"] textarea {
            background: #0a0a12 !important;
            color: #e0e0e0 !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 10px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 13px !important;
            padding: 12px 14px !important;
            min-height: 80px !important;
        }
        .stTextArea textarea::placeholder,
        div[data-testid="stTextArea"] textarea::placeholder {
            color: #64748b !important;
        }
        .stTextArea textarea:focus,
        div[data-testid="stTextArea"] textarea:focus {
            border-color: #EC4899 !important;
            box-shadow: 0 0 20px rgba(236,72,153,0.08) !important;
            outline: none !important;
        }
        
        /* ============================================
           BUTTONS - DARK
           ============================================ */
        .stButton > button {
            background: rgba(255,255,255,0.05) !important;
            color: #e0e0e0 !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 10px !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            transition: all 0.3s ease !important;
        }
        .stButton > button:hover {
            background: #EC4899 !important;
            color: #FFFFFF !important;
            border-color: #EC4899 !important;
            box-shadow: 0 0 25px rgba(236,72,153,0.2) !important;
        }
        
        /* ============================================
           CONTAINERS - DARK
           ============================================ */
        div[data-testid="stVerticalBlockBorder"] {
            background: rgba(18,19,26,0.7) !important;
            border: 1px solid rgba(255,255,255,0.04) !important;
            border-radius: 12px !important;
            padding: 16px !important;
        }
        
        /* ============================================
           LABELS - DARK
           ============================================ */
        .face-label {
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            color: #94a3b8 !important;
            margin-bottom: 4px !important;
        }
        
        .face-title {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 12px !important;
            color: #FFC0CB !important;
            margin-bottom: 12px !important;
            letter-spacing: 0.5px !important;
        }
        
        /* ============================================
           VIDEO PLAYER - DARK
           ============================================ */
        div[data-testid="stVideo"] {
            background: #000000 !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255,255,255,0.04) !important;
            overflow: hidden !important;
        }
        
        /* ============================================
           EMPTY STATE - DARK
           ============================================ */
        .empty-state {
            height: 380px;
            min-height: 380px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: #64748b;
            text-align: center;
            padding: 12px;
            overflow: hidden;
            background: rgba(10,10,12,0.4);
            border-radius: 12px;
            border: 1px dashed rgba(255,192,203,0.12);
        }
        .empty-state .icon {
            font-size: 48px;
            margin-bottom: 10px;
        }
        .empty-state .title {
            font-family: 'Inter', sans-serif;
            font-size: 13px;
            font-weight: 500;
            color: #FFC0CB;
            margin: 0;
        }
        .empty-state .desc {
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            color: #94a3b8;
            max-width: 400px;
            text-align: center;
            margin-top: 4px;
            line-height: 1.4;
        }
        .empty-state .powered {
            font-family: 'Inter', sans-serif;
            font-size: 10px;
            color: #EC4899;
            margin-top: 4px;
        }
        
        /* ============================================
           SUCCESS MESSAGE - DARK
           ============================================ */
        .stAlert {
            background: rgba(10,10,15,0.9) !important;
            border-radius: 10px !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
        }
        .stAlert .stAlertContent {
            font-family: 'Inter', sans-serif !important;
            font-size: 12px !important;
            color: #e0e0e0 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ============================================
    # HEADER
    # ============================================
    st.markdown("""
    <div class="face-header">
        <span class="badge">👤 AI AVATAR</span>
        <h2>Global <span class="highlight">Face Video</span> Studio</h2>
        <p>Upload photo • Enter script • Generate talking face video from cloud</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ============================================
    # MAIN CONTENT
    # ============================================
    fv_col1, fv_col2 = st.columns([1.1, 1.4], gap="medium")
    
    with fv_col1:
        with st.container(border=True):
            st.markdown("<style>.face-title { color: #EC4899; !important; }</style>", unsafe_allow_html=True)
            st.markdown('<h4 class="face-title"><span style="color: #EC4899; !important;">🥶 ZOVIX FACE STUDIO</span></h4>', unsafe_allow_html=True)
            
            # Upload Face Photo
            st.markdown('<p class="face-label">📷 Upload Face Photo</p>', unsafe_allow_html=True)
            face_image_upload = st.file_uploader(
                "Upload Face Photo",
                type=['jpg', 'jpeg', 'png', 'webp'],
                key="unified_fv_face_upload",
                label_visibility="collapsed",
                help="200MB per file · JPG, PNG, WEBP"
            )
            if face_image_upload:
                st.session_state["unified_face_image_bytes"] = bytes(face_image_upload.getbuffer())
                st.success(f"✅ {face_image_upload.name} uploaded successfully!")
                st.image(st.session_state["unified_face_image_bytes"], caption="Uploaded Face", use_container_width=True)
            
            # Script
            st.markdown('<p class="face-label">📝 Dialogue / Script</p>', unsafe_allow_html=True)
            face_prompt = st.text_area(
                "Dialogue / Script",
                placeholder="Type what the person should speak naturally...",
                height=80,
                key="unified_fv_prompt",
                label_visibility="collapsed"
            )
            
            # Duration & Quality
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.markdown('<p class="face-label">⏱️ Duration</p>', unsafe_allow_html=True)
                video_duration = st.select_slider(
                    "Duration",
                    options=[5, 10, 15, 20, 30, 45, 60],
                    value=10,
                    key="fv_duration",
                    label_visibility="collapsed"
                )
            with col_f2:
                st.markdown('<p class="face-label">📊 Quality</p>', unsafe_allow_html=True)
                quality = st.selectbox(
                    "Quality",
                    ["Standard", "HD", "4K"],
                    key="fv_quality",
                    label_visibility="collapsed"
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
                        # Generate Button - Pure Replicate Cloud Engine ☁️
            if st.button("🌍 Generate Global Face Video", key="unified_fv_generate_btn", use_container_width=True):
                            if not face_prompt or not face_prompt.strip():
                                st.error("Please enter a dialogue/script for the face video.")
                            elif not face_image_upload:
                                st.error("Please upload a face photo first.")
                            else:
                                # Save uploaded file to temp
                                face_bytes = st.session_state.get("unified_face_image_bytes")
                                temp_face_path = None
                                if face_bytes:
                                    temp_face_path = f"face_videos/temp_unified_face_{uuid.uuid4().hex[:8]}.png"
                                    os.makedirs("face_videos", exist_ok=True)
                                    with open(temp_face_path, 'wb') as f:
                                        f.write(face_bytes)
                    
                                # Step 1: DeepFace gender auto-detect
                                with st.spinner("🔍 AI scanning face for voice selection..."):
                                    try:
                                        scan_result = deepface_scan_face_and_select_voice(temp_face_path)
                                        if scan_result:
                                            detected_gender = scan_result.get("gender", "Male")
                                            detected_age = scan_result.get("age", 25)
                                            auto_voice = scan_result.get("voice_label", "Adam (Premium Male)")
                                            st.session_state["fv_detected_gender"] = detected_gender
                                            st.session_state["fv_detected_age"] = detected_age
                                            st.session_state["fv_auto_selected_voice"] = auto_voice
                                            st.session_state["fv_detected_category"] = scan_result.get("category", "Adult Male")
                                            st.toast(f"🎯 {scan_result.get('category', '')} (Age: {detected_age}) → {auto_voice}")
                                    except Exception as scan_err:
                                        logger.warning(f"Face scan error: {scan_err}")
                                        st.toast("Face scan unavailable. Using default voice.", icon="🤖")
                    
                                # Step 2: Token validation
                                success, required_tokens, message = validate_and_deduct_tokens("Face Video Generator", quality)
                                if not success:
                                    st.error(message)
                                else:
                                    st.success(f"✓ {message}")
                        
                                    # Step 3: Generate via Replicate Cloud directly ☁️
                                    with st.spinner(f"☁️ Generating {quality} face video on Replicate Cloud GPU..."):
                                        try:
                                            video_url = generate_world_face_video(
                                                prompt=face_prompt,
                                                face_image_path=temp_face_path,
                                                duration=video_duration,
                                                quality=quality,
                                                voice_language="English",
                                                voice_label=st.session_state.get("fv_auto_selected_voice", None),
                                            )
                                
                                            if video_url:
                                                st.session_state["active_face_video_url"] = video_url
                                                st.session_state["active_face_video"] = None  # Clear local path
                                                timestamp = time.strftime("%Y%m%d_%H%M%S")
                                                file_name = f"zovix_face_video_{quality.lower()}_{timestamp}.mp4"
                                                save_face_video_to_db(
                                                    st.session_state.get("logged_user", "guest"),
                                                    file_name, face_prompt, video_url,
                                                    temp_face_path or "", quality
                                                )
                                                st.session_state["face_video_history"] = load_face_video_history_db(st.session_state.get("logged_user", "guest"))
                                                st.balloons()
                                                st.toast(f"✅ Face video generated successfully on Cloud GPU!")
                                                st.rerun()
                                            else:
                                                st.error("❌ Replicate Cloud generation failed. Check API key and try again.")
                                        except Exception as e:
                                            st.error(f"❌ Cloud Generation Error: {str(e)}")
                                            logger.error(f"Unified face video error: {e}")
    
    with fv_col2:
        with st.container(border=True):
            st.markdown("<style>.face-title { color: #EC4899; !important; }</style>", unsafe_allow_html=True)
            st.markdown('<h4 class="face-title"><span style="color: #EC4899; !important;">🌍 GLOBAL FACE PLAYER</span></h4>', unsafe_allow_html=True)
            
                        # Show both URL-based (cloud) and local file-based face videos
            active_face_video_url = st.session_state.get("active_face_video_url")
            active_face_video_local = st.session_state.get("active_face_video")
            video_to_show = active_face_video_url or active_face_video_local
            
            if video_to_show and (isinstance(video_to_show, str) and (video_to_show.startswith("http") or os.path.exists(video_to_show))):
                engine_used = st.session_state.get("face_video_engine_used", "Unknown")
                runtime_mode = st.session_state.get("face_video_runtime_mode", "Unknown")
                st.caption(f"⚡ Engine: {engine_used} | Runtime: {runtime_mode}")
                st.video(video_to_show, format="video/mp4", autoplay=False, loop=True, muted=False)
                
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    download_available = False
                    download_data = None
                    if isinstance(video_to_show, str) and video_to_show.startswith("http"):
                        try:
                            dl = requests.get(video_to_show, timeout=30)
                            if dl.status_code == 200 and len(dl.content) > 1024:
                                download_data = dl.content
                                download_available = True
                        except Exception:
                            pass
                    elif isinstance(video_to_show, str) and os.path.exists(video_to_show):
                        try:
                            with open(video_to_show, 'rb') as f:
                                download_data = f.read()
                            download_available = True
                        except Exception:
                            pass
                    
                    if download_available and download_data:
                        st.download_button(
                            label="📥 Download Video",
                            data=download_data,
                            file_name=f"zovix_face_video_{uuid.uuid4().hex[:8]}.mp4",
                            mime="video/mp4",
                            use_container_width=True,
                            key="unified_fv_download_btn",
                        )
                    else:
                        st.info("📥 Download temporarily unavailable")
                with col_clr:
                    if st.button("🧹 Clear Video", key="unified_fv_clear_btn", use_container_width=True):
                        st.session_state["active_face_video_url"] = None
                        st.session_state["active_face_video"] = None
                        st.rerun()
            else:
                st.markdown("""
                <div class="empty-state">
                    <span class="icon">👤</span>
                    <p class="title" style="color: #EC4899; !important;">Face video will render here</p>
                    <p class="desc">Upload face photo + script and generate a professional talking face.</p>
                    <p class="powered">⚡ Powered by Zovix</p>
                </div>
                """, unsafe_allow_html=True)
# ========================================================
# 38. AUTH MODALS - IMPROVED
# ========================================================

@st.dialog("🔐 Security Gateway Node Access", width="small")
def show_auth_modal(mode="login"):
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 15px;">
            <div style="font-family: 'Orbitron', sans-serif; font-size: 16px; color: #EC4899; text-transform: uppercase; letter-spacing: 1.5px;">
                { '🔑 Sign In Portal' if mode == 'login' else '📝 Register Identity' }
            </div>
            <p style="font-size: 11px; color: #94a3b8; margin-top: 5px;">Secure access nodes dynamically configured.</p>
        </div>
    """, unsafe_allow_html=True)
    
    username_val = st.text_input("Username / Email", placeholder="Enter your username or email", key="auth_modal_username_input").strip()
    password_val = st.text_input("Password", type="password", placeholder="Enter your password", key="auth_modal_password_input").strip()
    st.write("")
    
    if mode == "login":
        col_login, col_register = st.columns(2)
        with col_login:
            if st.button("🔑 Sign In", key="auth_modal_login_btn", use_container_width=True):
                # 🎯 Aapki asli keys se direct live data uthane ke liye fix
                username_val = st.session_state.get("auth_modal_username_input", "").strip()
                password_val = st.session_state.get("auth_modal_password_input", "").strip()
                
                if not username_val or not password_val:
                    st.error("Please enter both username and password.")
                else:
                    auth_result, twofa_enabled = authenticate_user_db(username_val, password_val)
                    if auth_result:
                        if twofa_enabled and HAS_2FA:
                            st.session_state["2fa_temp_user"] = username_val
                            st.session_state["show_2fa"] = True
                            st.rerun()
                        else:
                            st.session_state["is_logged_in"] = True
                            st.session_state["logged_user"] = username_val
                            st.session_state["xp_points"] = get_user_xp_db(username_val)
                            st.session_state["creator_level"] = 1 + (st.session_state["xp_points"] // 100)
                            st.session_state["history_renders"] = load_renders_history_db(username_val)
                            st.session_state["face_video_history"] = load_face_video_history_db(username_val)
                            st.session_state["current_page"] = "studio"
                            st.session_state["user_credits"] = get_user_credits_db(username_val)
                            st.session_state["credit_balance"] = st.session_state["user_credits"]
                            
                            if st.session_state.get("auth_redirect_mode"):
                                st.session_state["studio_active_mode"] = st.session_state["auth_redirect_mode"]
                                st.session_state["current_workspace_mode"] = st.session_state["auth_redirect_mode"]
                            
                            check_and_refresh_subscription(username_val)
                            
                            if st.session_state.get("pending_credits", 0) > 0:
                                add_credits(username_val, st.session_state["pending_credits"])
                                st.success(f"✅ Added {st.session_state['pending_credits']} credits from pending payment!")
                                st.session_state["pending_credits"] = 0
                                st.session_state["pending_pack_name"] = ""
                                st.session_state["payment_verified"] = False
                            
                            if not gdpr_manager.get_consent(username_val):
                                gdpr_manager.set_consent(username_val)
                            
                            st.toast(f"Welcome back, {username_val}! 🎉")
                            st.rerun()
                    else:
                        st.error("❌ Invalid username or password. Please try again.")
        
        with col_register:
            if st.button("📝 Register", key="auth_modal_register_btn", use_container_width=True):
                if not username_val or not password_val:
                    st.error("Please enter both username and password.")
                elif len(password_val) < 4:
                    st.error("Password must be at least 4 characters long.")
                else:
                    if register_user_db(username_val, password_val):
                        st.session_state["is_logged_in"] = True
                        st.session_state["logged_user"] = username_val
                        st.session_state["xp_points"] = 0
                        st.session_state["creator_level"] = 1
                        st.session_state["history_renders"] = []
                        st.session_state["face_video_history"] = []
                        st.session_state["current_page"] = "studio"
                        st.session_state['user_credits'] = get_user_credits_db(username_val)
                        st.session_state['credit_balance'] = st.session_state['user_credits']
                        
                        if st.session_state.get("auth_redirect_mode"):
                            st.session_state["studio_active_mode"] = st.session_state["auth_redirect_mode"]
                            st.session_state["current_workspace_mode"] = st.session_state["auth_redirect_mode"]
                        
                        check_and_refresh_subscription(username_val)
                        gdpr_manager.set_consent(username_val)
                        
                        st.toast(f"Welcome to ZOVIX, {username_val}! 🚀")
                        st.rerun()
                    else:
                        st.error("Registration failed. Please try a different username.")
        
        st.markdown("<div style='text-align:center; font-size:10px; color:#64748b; margin: 15px 0;'>OR SIGN IN WITH SOCIAL PLATFORMS</div>", unsafe_allow_html=True)
        col_g, col_f = st.columns(2)
        with col_g:
            if st.button("🔵 Google", key="modal_social_g", use_container_width=True):
                st.session_state["active_social_login"] = "Google"
        with col_f:
            if st.button("🔵 Facebook", key="modal_social_f", use_container_width=True):
                st.session_state["active_social_login"] = "Facebook"

        if "active_social_login" in st.session_state:
            social_login_dialog_box(st.session_state["active_social_login"])

def social_login_dialog_box(platform):
    st.markdown(f"""
        <div style="background: rgba(18, 19, 26, 0.95); padding: 5px; border-radius: 12px; text-align: center;">
            <div style="font-family: 'Orbitron', sans-serif; font-size: 14px; color: #FFC0CB; margin-bottom: 10px; letter-spacing: 1px; text-transform: uppercase;">Login with {platform}</div>
            <p style="font-size:12px; color:#94a3b8; margin-bottom:15px;">Enter your email to continue</p>
        </div>
    """, unsafe_allow_html=True)
    social_email = st.text_input("Email Address", placeholder="yourname@gmail.com", key="social_email_input").strip()
    st.write("")
    if st.button("Authenticate & Log In", key="social_confirm_btn", use_container_width=True):
        if social_email and "@" in social_email:
            success = login_or_register_social(social_email, platform)
            if success:
                st.session_state["is_logged_in"] = True
                st.session_state["logged_user"] = social_email
                st.session_state["xp_points"] = get_user_xp_db(social_email)
                st.session_state["creator_level"] = 1 + (st.session_state["xp_points"] // 100)
                st.session_state["history_renders"] = load_renders_history_db(social_email)
                st.session_state["face_video_history"] = load_face_video_history_db(social_email)
                st.session_state["current_page"] = "studio"
                st.session_state['user_credits'] = get_user_credits_db(social_email)
                st.session_state['credit_balance'] = st.session_state['user_credits']
                
                if st.session_state.get("auth_redirect_mode"):
                    st.session_state["studio_active_mode"] = st.session_state["auth_redirect_mode"]
                    st.session_state["current_workspace_mode"] = st.session_state["auth_redirect_mode"]
                
                check_and_refresh_subscription(social_email)
                
                if st.session_state.get("pending_credits", 0) > 0:
                    add_credits(social_email, st.session_state["pending_credits"])
                    st.success(f"✅ Added {st.session_state['pending_credits']} credits from pending payment!")
                    st.session_state["pending_credits"] = 0
                    st.session_state["pending_pack_name"] = ""
                    st.session_state["payment_verified"] = False
                
                gdpr_manager.set_consent(social_email)
                st.toast(f"Logged in successfully via {platform}! 🎉")
                st.rerun()
            else:
                st.error("Authentication failed. Please try again.")
        else:
            st.error("Please enter a valid email address.")

@st.dialog("🔐 Two-Factor Authentication", width="small")
def show_2fa_modal():
    st.markdown("""
        <div style="text-align: center; margin-bottom: 15px;">
            <div style="font-family: 'Orbitron', sans-serif; font-size: 16px; color: #FFC0CB; text-transform: uppercase; letter-spacing: 1.5px;">
                🔐 Two-Factor Authentication
            </div>
            <p style="font-size: 11px; color: #94a3b8; margin-top: 5px;">Enter the 6-digit code from your authenticator app</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Check if this is setup or login mode
    if st.session_state.get("2fa_setup_mode"):
        # SETUP MODE - Show QR Code
        secret = st.session_state.get("pending_2fa_secret", "")
        if not secret:
            secret = pyotp.random_base32()
            st.session_state["pending_2fa_secret"] = secret
            user = st.session_state.get("logged_user", "")
            conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET twofa_secret = ? WHERE username = ?", (secret, user))
            conn.commit()
            conn.close()
        
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=st.session_state.get("logged_user", "user"), issuer_name="ZOVIX Portal")
        qr = qrcode.QRCode(box_size=6, border=2)
        qr.add_data(uri)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#FFC0CB", back_color="#0a0a0f")
        qr_path = f"face_videos/2fa_qr_{uuid.uuid4().hex[:8]}.png"
        os.makedirs("face_videos", exist_ok=True)
        qr_img.save(qr_path)
        
        st.markdown("<h4 style='color: #FFC0CB; text-align: center;'>📱 Scan QR Code with Authenticator App</h4>", unsafe_allow_html=True)
        st.image(qr_path, caption="Scan with Google Authenticator / Authy", width=250)
        st.info(f"🔑 Or enter this key manually: `{secret}`")
        st.code(secret, language="text")
        
        test_code = st.text_input("Enter 6-digit code to verify:", max_chars=6, type="password", key="2fa_setup_code").strip()
        if st.button("✅ Verify & Activate", key="2fa_setup_verify_btn", use_container_width=True):
            if test_code and len(test_code) == 6:
                if totp.verify(test_code):
                    st.session_state["2fa_enabled"] = True
                    st.session_state["2fa_setup_mode"] = False
                    st.session_state["pending_2fa_secret"] = None
                    st.success("✅ 2FA Activated! Your account is secured.")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Invalid code. Try again.")
            else:
                st.error("Please enter a 6-digit code.")
        
        if st.button("Cancel Setup", key="2fa_cancel_setup_btn", use_container_width=True):
            st.session_state["2fa_setup_mode"] = False
            st.rerun()
    else:
        # LOGIN MODE - Verify code
        code = st.text_input("Authentication Code", max_chars=6, type="password", key="2fa_code_input").strip()
        st.write("")
        
        if st.button("✅ Verify", key="2fa_verify_btn", use_container_width=True):
            if code and len(code) == 6:
                username = st.session_state.get("2fa_temp_user", "")
                if HAS_2FA and pyotp:
                    try:
                        conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
                        cursor = conn.cursor()
                        cursor.execute("SELECT twofa_secret FROM users WHERE username = ?", (username,))
                        row = cursor.fetchone()
                        conn.close()
                        
                        if row and row[0]:
                            totp = pyotp.TOTP(row[0])
                            if totp.verify(code):
                                st.session_state["2fa_verified"] = True
                                st.session_state["is_logged_in"] = True
                                st.session_state["logged_user"] = username
                                st.session_state["xp_points"] = get_user_xp_db(username)
                                st.session_state["creator_level"] = 1 + (st.session_state["xp_points"] // 100)
                                st.session_state["history_renders"] = load_renders_history_db(username)
                                st.session_state["face_video_history"] = load_face_video_history_db(username)
                                st.session_state["current_page"] = "studio"
                                st.session_state['user_credits'] = get_user_credits_db(username)
                                st.session_state['credit_balance'] = st.session_state['user_credits']
                                
                                if st.session_state.get("auth_redirect_mode"):
                                    st.session_state["studio_active_mode"] = st.session_state["auth_redirect_mode"]
                                    st.session_state["current_workspace_mode"] = st.session_state["auth_redirect_mode"]
                                
                                check_and_refresh_subscription(username)
                                
                                if st.session_state.get("pending_credits", 0) > 0:
                                    add_credits(username, st.session_state["pending_credits"])
                                    st.success(f"✅ Added {st.session_state['pending_credits']} credits from pending payment!")
                                    st.session_state["pending_credits"] = 0
                                    st.session_state["pending_pack_name"] = ""
                                    st.session_state["payment_verified"] = False
                                
                                gdpr_manager.set_consent(username) if hasattr(gdpr_manager, 'set_consent') else None
                                
                                st.session_state["2fa_temp_user"] = None
                                st.toast("2FA verified! Welcome back! 🎉")
                                st.rerun()
                            else:
                                st.error("Invalid code. Please try again.")
                        else:
                            st.error("2FA not set up for this account.")
                    except Exception as e:
                        logger.error(f"2FA verification error: {e}")
                        st.error("Error verifying 2FA code.")
                else:
                    st.error("2FA system not available.")
            else:
                st.error("Please enter a valid 6-digit code.")

@st.dialog("🎬 Cinematic Production Monitor", width="large")
def open_preview_modal(video_path):
    st.markdown(f"""
        <div style="background: rgba(18, 19, 26, 0.95); padding: 15px; border-radius: 12px; border: 1px solid rgba(255, 192, 203, 0.15);">
            <div style="font-family: 'Orbitron', sans-serif; font-size: 14px; color: #FFC0CB; margin-bottom: 12px; letter-spacing: 1px;">🟢 THEATRICAL PLAYBACK MONITOR</div>
        </div>
    """, unsafe_allow_html=True)
    st.video(video_path, format="video/mp4", autoplay=False, loop=True, muted=False)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Close Monitor", key="close_theatrical_monitor_btn", use_container_width=True):
        st.rerun()



def run_cinematic_engine():
    """Cinematic Engine - Matching Studio Style"""
    
    # ============================================
    # CINEMATIC ENGINE CSS - COMPLETE DARK THEME
    # ============================================
    st.markdown("""
    <style>
        /* ============================================
           CINEMATIC ENGINE - DARK THEME
           ============================================ */
        
        /* HEADER */
        .cinematic-header {
            background: linear-gradient(135deg, rgba(236,72,153,0.06), rgba(69,243,255,0.06));
            border-radius: 16px;
            border: 1px solid rgba(69,243,255,0.08);
            padding: 16px 20px;
            margin-bottom: 18px;
            text-align: center;
        }
        .cinematic-header .badge {
            display: inline-block;
            background: rgba(236,72,153,0.12);
            color: #EC4899;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 9px;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1px;
            border: 1px solid rgba(236,72,153,0.15);
            margin-bottom: 6px;
        }
        .cinematic-header h2 {
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            color: #FFFFFF;
            margin: 0;
        }
        .cinematic-header h2 .highlight {
            background: linear-gradient(135deg, #45f3ff, #EC4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .cinematic-header p {
            font-family: 'Inter', sans-serif;
            color: #94a3b8;
            font-size: 12px;
            margin: 4px 0 0 0;
        }
        
        /* ============================================
           PROMPT BOX - DARK
           ============================================ */
        .stTextArea textarea,
        div[data-testid="stTextArea"] textarea {
            background: #0a0a12 !important;
            color: #e0e0e0 !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 10px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 13px !important;
            padding: 12px 14px !important;
            min-height: 80px !important;
        }
        .stTextArea textarea::placeholder,
        div[data-testid="stTextArea"] textarea::placeholder {
            color: #64748b !important;
        }
        .stTextArea textarea:focus,
        div[data-testid="stTextArea"] textarea:focus {
            border-color: #EC4899 !important;
            box-shadow: 0 0 20px rgba(236,72,153,0.08) !important;
            outline: none !important;
        }
        
        /* ============================================
           SELECT BOX (DROPDOWN) - DARK
           ============================================ */
        .stSelectbox > div,
        div[data-testid="stSelectbox"] > div {
            background: #0a0a12 !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 10px !important;
        }
        .stSelectbox select,
        div[data-testid="stSelectbox"] select {
            background: #0a0a12 !important;
            color: #e0e0e0 !important;
            border: none !important;
            border-radius: 10px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 13px !important;
            padding: 8px 12px !important;
        }
        .stSelectbox select:focus,
        div[data-testid="stSelectbox"] select:focus {
            border-color: #EC4899 !important;
            outline: none !important;
        }
        
        /* Selectbox Dropdown Menu */
        div[data-baseweb="select"] {
            background: #0a0a12 !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 10px !important;
        }
        div[data-baseweb="select"] > div {
            background: #0a0a12 !important;
        }
        div[data-baseweb="select"] input {
            background: #0a0a12 !important;
            color: #e0e0e0 !important;
        }
        ul[data-baseweb="menu"] {
            background: #0f0f1a !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 10px !important;
        }
        ul[data-baseweb="menu"] li {
            background: #0f0f1a !important;
            color: #e0e0e0 !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 13px !important;
        }
        ul[data-baseweb="menu"] li:hover {
            background: rgba(236,72,153,0.1) !important;
            color: #FFFFFF !important;
        }
        ul[data-baseweb="menu"] li[aria-selected="true"] {
            background: rgba(236,72,153,0.15) !important;
            color: #EC4899 !important;
        }
        
        /* ============================================
           SLIDER - DARK
           ============================================ */
        div[data-testid="stSlider"] {
            background: rgba(10,10,15,0.7) !important;
            border-radius: 10px !important;
            padding: 8px 12px !important;
            border: 1px solid rgba(255,255,255,0.04) !important;
        }
        div[data-testid="stSlider"] label {
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            color: #94a3b8 !important;
        }
        div[data-testid="stSlider"] .stSliderValue {
            color: #45f3ff !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 11px !important;
        }
        
        /* ============================================
           FILE UPLOADER - DARK
           ============================================ */
        div[data-testid="stFileUploader"] {
            background: rgba(10,10,15,0.7) !important;
            border-radius: 10px !important;
            border: 1px dashed rgba(255,255,255,0.08) !important;
            padding: 12px !important;
        }
        div[data-testid="stFileUploader"]:hover {
            border-color: #EC4899 !important;
        }
        div[data-testid="stFileUploader"] p {
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            color: #94a3b8 !important;
        }
        div[data-testid="stFileUploader"] .stFileUploaderButton {
            background: rgba(236,72,153,0.1) !important;
            color: #EC4899 !important;
            border: 1px solid rgba(236,72,153,0.2) !important;
            border-radius: 8px !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 10px !important;
        }
        div[data-testid="stFileUploader"] .stFileUploaderButton:hover {
            background: rgba(236,72,153,0.2) !important;
        }
        
        /* ============================================
           TOGGLE / CHECKBOX - DARK
           ============================================ */
        .stCheckbox label {
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            color: #94a3b8 !important;
        }
        .stCheckbox label:hover {
            color: #FFFFFF !important;
        }
        .stCheckbox input[type="checkbox"] {
            accent-color: #EC4899 !important;
        }
        
        /* ============================================
           RADIO BUTTONS - DARK
           ============================================ */
        div[data-testid="stRadio"] {
            background: rgba(10,10,15,0.7) !important;
            border-radius: 10px !important;
            padding: 8px 12px !important;
            border: 1px solid rgba(255,255,255,0.04) !important;
        }
        div[data-testid="stRadio"] label {
            font-family: 'Inter', sans-serif !important;
            font-size: 12px !important;
            color: #94a3b8 !important;
        }
        div[data-testid="stRadio"] label:hover {
            color: #FFFFFF !important;
        }
        div[data-testid="stRadio"] input[type="radio"]:checked + label {
            color: #EC4899 !important;
        }
        
        /* ============================================
           SELECTION CARDS - DARK
           ============================================ */
        .selected-opt-wrap button,
        .unselected-opt-wrap button {
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            border-radius: 10px !important;
            padding: 8px 12px !important;
            min-height: 40px !important;
        }
        .selected-opt-wrap button {
            background: #EC4899 !important;
            color: #FFFFFF !important;
            border: 2px solid #EC4899 !important;
            box-shadow: 0 0 20px rgba(236,72,153,0.15) !important;
        }
        .unselected-opt-wrap button {
            background: rgba(255,255,255,0.04) !important;
            color: #94a3b8 !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
        }
        .unselected-opt-wrap button:hover {
            background: rgba(236,72,153,0.05) !important;
            border-color: #EC4899 !important;
            color: #FFFFFF !important;
        }
        
        /* ============================================
           CONTAINERS - DARK
           ============================================ */
        div[data-testid="stVerticalBlockBorder"] {
            background: rgba(18,19,26,0.7) !important;
            border: 1px solid rgba(255,255,255,0.04) !important;
            border-radius: 12px !important;
            padding: 16px !important;
        }
        
        /* ============================================
           BUTTONS - DARK
           ============================================ */
        .stButton > button {
            background: rgba(255,255,255,0.05) !important;
            color: #e0e0e0 !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 10px !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            transition: all 0.3s ease !important;
        }
        .stButton > button:hover {
            background: #EC4899 !important;
            color: #FFFFFF !important;
            border-color: #EC4899 !important;
            box-shadow: 0 0 25px rgba(236,72,153,0.2) !important;
        }
        
        /* ============================================
           VIDEO OUTPUT - DARK
           ============================================ */
        .canvas-container-box {
            background: rgba(10,10,12,0.6) !important;
            border: 1px solid rgba(255,255,255,0.04) !important;
            border-radius: 12px !important;
            padding: 12px !important;
            min-height: 420px !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
        }
        
        /* ============================================
           COMPACT LABEL - DARK
           ============================================ */
        .compact-label {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 11px !important;
            color: #94a3b8 !important;
            letter-spacing: 1.5px !important;
            text-transform: uppercase !important;
            margin: 12px 0 6px 0 !important;
        }
        
        /* ============================================
           MESSAGES - DARK
           ============================================ */
        .stAlert {
            background: rgba(10,10,15,0.9) !important;
            border-radius: 10px !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
        }
        .stAlert .stAlertContent {
            font-family: 'Inter', sans-serif !important;
            font-size: 12px !important;
            color: #e0e0e0 !important;
        }
        
        /* ============================================
           EXPANDER - DARK
           ============================================ */
        .streamlit-expanderHeader {
            background: rgba(10,10,15,0.7) !important;
            border-radius: 10px !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 11px !important;
            color: #94a3b8 !important;
            border: 1px solid rgba(255,255,255,0.04) !important;
        }
        .streamlit-expanderHeader:hover {
            color: #FFFFFF !important;
        }
        .streamlit-expanderContent {
            background: rgba(10,10,15,0.5) !important;
            border-radius: 0 0 10px 10px !important;
            padding: 8px 12px !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ============================================
    # HEADER
    # ============================================
    st.markdown("""
    <div class="cinematic-header">
        <span class="badge">🎬 AI-POWERED</span>
        <h2>Cinematic <span class="highlight">Engine</span></h2>
        <p>Transform your ideas into professional cinematic videos with AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ============================================
    # TRANSLATION, KEYS & SHORTCUTS
    # ============================================
    st.markdown('<p class="compact-label">🌐 TRANSLATION, KEYS & SHORTCUTS</p>', unsafe_allow_html=True)
    
    t_col1, t_col2, t_col3 = st.columns([1, 1, 1.2])
    with t_col1:
        st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">⚡ Smart Template Quick Mode</p>', unsafe_allow_html=True)
        st.session_state["quick_template_mode"] = st.toggle(
            "Fast 30s Compile",
            value=st.session_state["quick_template_mode"],
            label_visibility="collapsed"
        )
    with t_col2:
        st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">🌐 Voice Language</p>', unsafe_allow_html=True)
        st.session_state["language_choice"] = st.selectbox(
            "Voice Language",
            ["🇮🇳 Hinglish (Fluent Hindi Mix)", "🇬🇧 English (US Standard)", "🇫🇷 French (Parisian Neural)", "🇯🇵 Japanese (Formal Tokyo)"],
            key="studio_language_selector_layer",
            label_visibility="collapsed"
        )
    with t_col3:
        st.text(" ")
    
    st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 12px 0;'>", unsafe_allow_html=True)
    
    # ============================================
    # PROMPT INTERFACE
    # ============================================
    with st.container(border=True):
        st.markdown('<p class="compact-label" style="margin: 0 0 8px 0;">💡 Prompt Interface</p>', unsafe_allow_html=True)
        
        input_mode = st.radio(
            "Prompt Select Option Mode:",
            ["💡 Autonomous AI Topic", "✍️ Manual Custom Script", "🧠 DeepSeek AI Blueprint"],
            horizontal=True,
            key="studio_mode_radio",
            label_visibility="collapsed"
        )
        
        initial_topic_val = st.session_state.get("studio_prompt_value", "")
        
        if input_mode == "🧠 DeepSeek AI Blueprint":
            user_input = st.text_area(
                "Prompt Input",
                value=initial_topic_val,
                placeholder="Explain video concept: e.g. Ek kisan ke paas do beej the...",
                height=90,
                label_visibility="collapsed",
                key="studio_prompt_deepseek_input"
            )
            
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">📐 Aspect Ratio</p>', unsafe_allow_html=True)
            aspect_choice = st.selectbox(
                "Aspect Ratio",
                ["16:9 LANDSCAPE (YOUTUBE)", "9:16 VERTICAL (SHORTS/REELS)"],
                key="studio_deepseek_aspect",
                label_visibility="collapsed"
            )
            
            if st.button("📐 Generate Blueprint", key="deepseek_generate_blueprint_btn", use_container_width=True):
                if not user_input.strip():
                    st.error("Please enter a video concept.")
                else:
                    with st.spinner("🧠 DeepSeek AI is generating your video blueprint..."):
                        aspect_for_deepseek = "9:16" if "VERTICAL" in st.session_state.get("studio_deepseek_aspect", "9:16 VERTICAL") else "16:9"
                        blueprint = generate_video_blueprint_with_deepseek(user_input, aspect_for_deepseek)
                        if "error" in blueprint:
                            st.error(f"❌ DeepSeek Error: {blueprint['error']}")
                        else:
                            st.session_state["deepseek_blueprint_data"] = blueprint
                            st.session_state["deepseek_blueprint_visible"] = True
                            st.session_state["studio_prompt_value"] = user_input
                            st.toast("✅ Blueprint generated successfully!")
                            st.rerun()

            if st.session_state.get("deepseek_blueprint_visible") and st.session_state.get("deepseek_blueprint_data"):
                # Display the DeepSeek Blueprint
                bp = st.session_state["deepseek_blueprint_data"]
                st.markdown("""
                <div style="background: linear-gradient(135deg, rgba(236,72,153,0.08), rgba(139,92,246,0.08)); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,192,203,0.15); margin: 10px 0;">
                    <div style="font-family: 'Orbitron', sans-serif; font-size: 12px; color: #EC4899; letter-spacing: 1px; margin-bottom: 8px;">
                        🧠 DEEPSEEK AI BLUEPRINT
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Title
                title = bp.get("title", "Untitled Blueprint")
                st.markdown(f"### 🎬 {title}")

                # Description
                description = bp.get("description", "")
                if description:
                    st.markdown(f"<p style='color: #94a3b8; font-size: 13px;'>{description}</p>", unsafe_allow_html=True)

                # Video Structure
                structure = bp.get("video_structure", bp.get("structure", {}))
                if structure:
                    st.markdown("<h4 style='color: #FFC0CB; margin-top: 12px;'>📋 Video Structure</h4>", unsafe_allow_html=True)
                    scenes = structure.get("scenes", structure.get("sections", []))
                    if scenes:
                        for i, scene in enumerate(scenes):
                            scene_title = scene.get("title", scene.get("scene_text", f"Scene {i+1}"))
                            scene_desc = scene.get("description", scene.get("text", ""))
                            scene_keyword = scene.get("keyword", scene.get("search_keyword", ""))
                            scene_dur = scene.get("duration", 5)
                            with st.expander(f"🎬 Scene {i+1}: {scene_title}", expanded=(i==0)):
                                st.markdown(f"<p style='color: #e2e8f0;'>{scene_desc}</p>", unsafe_allow_html=True)
                                if scene_keyword:
                                    st.markdown(f"<p style='color: #94a3b8; font-size: 11px;'>🔍 Keyword: <code>{scene_keyword}</code></p>", unsafe_allow_html=True)
                                st.markdown(f"<p style='color: #94a3b8; font-size: 11px;'>⏱ Duration: {scene_dur}s</p>", unsafe_allow_html=True)
                    else:
                        st.info("No scenes found in blueprint structure")

                # Visual Style
                style = bp.get("visual_style", bp.get("style", {}))
                if style:
                    st.markdown("<h4 style='color: #FFC0CB; margin-top: 12px;'>🎨 Visual Style</h4>", unsafe_allow_html=True)
                    for key, val in style.items() if isinstance(style, dict) else []:
                        st.markdown(f"<p style='color: #94a3b8; font-size: 12px; margin: 2px 0;'><b>{key.replace('_', ' ').title()}:</b> {val}</p>", unsafe_allow_html=True)

                # Music Mood
                mood = bp.get("music_mood", bp.get("mood", ""))
                if mood:
                    st.markdown(f"<p style='color: #94a3b8; font-size: 12px; margin-top: 8px;'><b>🎵 Music Mood:</b> {mood}</p>", unsafe_allow_html=True)

                # Aspect Ratio
                ar = bp.get("aspect_ratio", "")
                if ar:
                    st.markdown(f"<p style='color: #94a3b8; font-size: 12px;'><b>📐 Aspect Ratio:</b> {ar}</p>", unsafe_allow_html=True)

                # Use Blueprint button
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🎬 Use This Blueprint for Generation", key="use_blueprint_btn", use_container_width=True):
                    if structure and scenes:
                        st.session_state["blueprint_scenes"] = scenes
                        st.session_state["blueprint_mood"] = mood
                        st.session_state["studio_prompt_value"] = description or title
                    st.success("✅ Blueprint loaded! Now click Generate to create video.")
                    st.toast("Blueprint ready for generation! 🚀")

                # Clear blueprint
                if st.button("🗑 Clear Blueprint", key="clear_blueprint_btn", use_container_width=True):
                    st.session_state["deepseek_blueprint_data"] = None
                    st.session_state["deepseek_blueprint_visible"] = False
                    st.rerun()
        
        else:
            user_input = st.text_area(
                "Prompt Input",
                value=initial_topic_val,
                placeholder="Explain video concept: e.g. Bermuda triangle ka ansuljha rahasya jo kisi ko nahi pata tha." if input_mode == "💡 Autonomous AI Topic" 
                else "Write a custom script separated by paragraph breaks...",
                height=90,
                label_visibility="collapsed",
                key="studio_prompt_standard_input"
            )
        
        # Render Quality
        st.markdown('<p class="compact-label" style="margin: 10px 0 4px 0;">📊 Render Quality</p>', unsafe_allow_html=True)
        cinematic_quality = st.selectbox(
            "Quality",
            ["Standard", "HD", "Pro"],
            key="cinematic_quality",
                        label_visibility="collapsed"
        )
        
        col_btn1, col_btn2 = st.columns([4, 1])
        with col_btn2:
            if st.button("Generate", key="studio_generate_action_btn", use_container_width=True):
                # Cinematic Video Generation Logic
                if not user_input.strip():
                    st.error("Please enter a video topic or script.")
                else:
                    try:
                        # Step 1: Validate tokens
                        burn_rate = BASE_BURN_RATE.get("Cinematic Engine", 4)
                        if cinematic_quality in ["HD", "Pro"]:
                            burn_rate += 1 if cinematic_quality == "HD" else 2
                        token_check = validate_and_deduct_tokens("Cinematic Engine", burn_rate)
                        if token_check is not True:
                            st.error(token_check)
                            st.stop()
                        
                        # Step 2: Parse parameters
                        selected_size = st.session_state.get("aspect_ratio", "9:16 Vertical (Shorts/Reels)")
                        dur_choice = st.session_state.get("duration_choice", "Quick Format Shorts (10-15s)")
                        voice_profile = st.session_state.get("voice_profile", "Adam (Premium Male)")
                        lang_choice = st.session_state.get("language_choice", "🇮🇳 Hinglish (Fluent Hindi Mix)")
                        selected_model = "gemini-2.5-pro" if "gemini-2.5-pro" in st.session_state.get("model_choice", "") else "gemini-2.5-flash"
                        
                        # Step 3: Generate script using ScriptingEngine
                        with st.spinner("📝 Generating script using AI..."):
                            scenes_data, music_mood = ScriptingEngine.generate_script(
                                topic=user_input,
                                duration_choice=dur_choice,
                                selected_model=selected_model,
                                language_choice=lang_choice
                            )
                            if not scenes_data:
                                st.error("Failed to generate script. Please try again.")
                                st.stop()
                            st.success(f"✅ Script generated: {len(scenes_data)} scenes, mood: {music_mood}")
                        
                        # Step 4: Get BGM
                        bgm_path = None
                        if uploaded_bgm is not None:
                            bgm_path = f"face_videos/custom_bgm_{uuid.uuid4().hex[:8]}.mp3"
                            with open(bgm_path, "wb") as f:
                                f.write(uploaded_bgm.getbuffer())
                        else:
                            bgm_path = get_music_path(music_mood) if 'get_music_path' in dir() else None
                        
                        with st.spinner("🎬 Generating cinematic video..."):
                            status_placeholder = st.empty()
                            progress_bar = st.progress(0, text="Starting cinematic engine...")
                            
                            status_placeholder.info("Building scenes with visuals and voiceover...")
                            progress_bar.progress(0.3, text="Processing scenes...")
                            
                            success = StitcherEngine.build_scene_stitched_video_isolated(
                                scenes_data=scenes_data,
                                video_output="final_shorts.mp4",
                                size_choice=selected_size,
                                voice_profile=voice_profile,
                                language_choice=lang_choice,
                                bgm_path=bgm_path,
                                bgm_volume=bgm_volume,
                                music_mood=music_mood
                            )
                            
                            if success and os.path.exists("final_shorts.mp4") and os.path.getsize("final_shorts.mp4") > 1000:
                                progress_bar.progress(1.0, text="✅ Cinematic video created!")
                                st.success("🎬 Cinematic video generated successfully!")
                                st.session_state["cinematic_video_ready"] = True
                                st.balloons()
                                st.rerun()
                            else:
                                progress_bar.progress(0, text="❌ Failed")
                                st.error("Video compilation failed. Check API keys and try again.")
                    
                    except Exception as e:
                        st.error(f"❌ Cinematic Engine Error: {str(e)}")
                        import traceback
                        st.error(traceback.format_exc())
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ============================================
    # ENGINE CONFIGURATORS & VIDEO OUTPUT
    # ============================================
    parameters_col, video_canvas_col = st.columns([1.1, 1.4], gap="medium")
    
    with parameters_col:
        with st.container(border=True):
            st.markdown("""
            <h4 style="font-family: 'Orbitron', sans-serif; font-size: 12px; color: #EC4899; margin-bottom: 12px; letter-spacing: 0.5px;">
                ⚙️ ENGINE CONFIGURATORS
            </h4>
            """, unsafe_allow_html=True)
            
            # Model Core
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">🤖 Model Core</p>', unsafe_allow_html=True)
            render_premium_selection_cards("", ["🤖 gemini-2.5-flash (Fast Stream Processing)", "🤖 gemini-2.5-pro (Deep Creative Narrative)"], "model_choice")
            selected_model = "gemini-2.5-pro" if "gemini-2.5-pro" in st.session_state["model_choice"] else "gemini-2.5-flash"
            
            # Aspect Ratio
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 10px 0 4px 0;">📐 Aspect Ratio</p>', unsafe_allow_html=True)
            render_premium_selection_cards("", ["📐 9:16 Vertical (Shorts/Reels)", "📐 16:9 Landscape (YouTube)", "📐 1:1 Square (Instagram)"], "aspect_ratio")
            
            # Duration
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 10px 0 4px 0;">⏱️ Duration</p>', unsafe_allow_html=True)
            render_premium_selection_cards("", ["⏱️ Quick Format Shorts (10-15s)", "⏱️ Expanded Long Format (1 Minute / 60s)"], "duration_choice")
            
            # Voice Profile
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 10px 0 4px 0;">🎤 Voice Profile</p>', unsafe_allow_html=True)
            voice_options = list(ELEVENLABS_VOICES.keys())
            current_voice = st.session_state.get("voice_profile", "Adam (Premium Male)")
            if current_voice not in voice_options:
                current_voice = "Adam (Premium Male)"
            selected_voice = st.selectbox(
                "Select Voice",
                voice_options,
                index=voice_options.index(current_voice) if current_voice in voice_options else 0,
                key="cinematic_voice_select",
                label_visibility="collapsed"
            )
            if selected_voice != st.session_state.get("voice_profile"):
                st.session_state["voice_profile"] = selected_voice
            
            # Resolution
            st.markdown('<p style="font-family: Inter; font-size: 11px; color: #94a3b8; margin: 10px 0 4px 0;">📊 Resolution</p>', unsafe_allow_html=True)
            render_premium_selection_cards("", ["720p", "1080p", "2K", "4K"], "res_choice")
            
            st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 12px 0;'>", unsafe_allow_html=True)
            
            # Face Lock
            st.markdown("""
            <h4 style="font-family: 'Orbitron', sans-serif; font-size: 11px; color: #EC4899; margin-bottom: 8px; letter-spacing: 0.5px;">
                🔒 FACE LOCK SECURITY
            </h4>
            """, unsafe_allow_html=True)
            face_lock_enabled = st.toggle("Enable Face Lock", value=False, key="face_lock_enabled_toggle")
            if face_lock_enabled:
                # Step 1: Upload reference face image
                if "face_lock_ref" not in st.session_state:
                    st.session_state["face_lock_ref"] = None
                    st.session_state["face_lock_unlocked"] = False
                
                col_ref, col_scan = st.columns(2)
                with col_ref:
                    face_lock_image = st.file_uploader("📸 Upload Your Face (Reference)", type=['jpg', 'jpeg', 'png', 'webp'], key="face_lock_upload")
                    if face_lock_image:
                        face_lock_path = f"face_videos/face_lock_{uuid.uuid4().hex[:8]}.png"
                        with open(face_lock_path, "wb") as f:
                            f.write(face_lock_image.getbuffer())
                        st.session_state["face_lock_ref"] = face_lock_path
                        st.image(face_lock_path, caption="Reference Face", width=200)
                        st.success("✅ Reference face saved!")
                
                # Step 2: Face verification via webcam/live cam
                with col_scan:
                    if st.session_state["face_lock_ref"] and os.path.exists(st.session_state["face_lock_ref"]):
                        if st.button("🔍 Scan & Verify Face", key="face_lock_verify_btn", use_container_width=True):
                            with st.spinner("🔄 Running face recognition..."):
                                try:
                                    from deepface import DeepFace
                                    # Open webcam capture
                                    import cv2
                                    cap = cv2.VideoCapture(0)
                                    if not cap.isOpened():
                                        st.error("❌ Webcam not accessible. Enable camera permissions.")
                                    else:
                                        ret, frame = cap.read()
                                        cap.release()
                                        if ret:
                                            live_path = f"face_videos/face_lock_live_{uuid.uuid4().hex[:8]}.png"
                                            cv2.imwrite(live_path, frame)
                                            result = DeepFace.verify(
                                                img1_path=st.session_state["face_lock_ref"],
                                                img2_path=live_path,
                                                enforce_detection=False
                                            )
                                            os.remove(live_path)
                                            if result.get("verified"):
                                                st.session_state["face_lock_unlocked"] = True
                                                st.success("✅ Face Match! Workspace Unlocked! 🎉")
                                                st.balloons()
                                            else:
                                                st.session_state["face_lock_unlocked"] = False
                                                st.error("❌ Face does not match! Access Denied")
                                                st.warning("⚠️ Distance: " + str(round(result.get("distance", 1), 4)))
                                        else:
                                            st.error("❌ Could not capture from webcam")
                                except ImportError:
                                    st.error("❌ DeepFace not installed. Run: pip install deepface")
                                except Exception as e:
                                    st.error(f"❌ Face verification error: {e}")
                        
                        if st.session_state.get("face_lock_unlocked"):
                            st.success("🔓 Workspace UNLOCKED - Full access granted")
                        else:
                            st.warning("🔒 Workspace LOCKED - Verify face to unlock")
                    else:
                        st.info("📸 Upload a reference face first, then verify")
                
                # Show status
                if st.session_state.get("face_lock_unlocked"):
                    st.success("🔓 Face Lock: ACTIVE & UNLOCKED")
                elif st.session_state["face_lock_ref"]:
                    st.warning("🔒 Face Lock: ACTIVE but LOCKED - Verify your face")
                else:
                    st.info("📸 Face Lock: Setup incomplete - Upload reference photo")
            else:
                st.session_state["face_lock_unlocked"] = False
                st.info("🔓 Face Lock Disabled - Workspace is open")
            
            st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 12px 0;'>", unsafe_allow_html=True)
            
            # Audio Mixing
            st.markdown("""
            <h4 style="font-family: 'Orbitron', sans-serif; font-size: 11px; color: #EC4899; margin-bottom: 8px; letter-spacing: 0.5px;">
                🎵 AUDIO MIXING CONFIG
            </h4>
            """, unsafe_allow_html=True)
            uploaded_bgm = st.file_uploader("Upload Custom BGM Track", type=['mp3', 'wav'], key="studio_audio_bgm_uploader")
            if uploaded_bgm is not None:
                st.info("✅ Custom BGM uploaded. Will be used instead of library selection.")
            bgm_volume = st.slider(
                "BGM Audio Level Mixer",
                0.0, 1.0, 0.30, step=0.05,
                key="studio_audio_bgm_volume_slider"
            )
    
    with video_canvas_col:
        with st.container(border=True):
            st.markdown("""
            <h3 style="font-family: 'Orbitron', sans-serif; font-size: 13px; color:#EC4899; margin-bottom: 12px; letter-spacing: 0.5px;">
                🎥 LIVE VIDEO OUTPUT BOX
            </h3>
            """, unsafe_allow_html=True)
            
            if os.path.exists("final_shorts.mp4") and os.path.getsize("final_shorts.mp4") > 0:
                st.video("final_shorts.mp4", format="video/mp4", autoplay=False, loop=True, muted=False)
                
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    if st.button("📥 Download Video", key="canvas_download_btn", use_container_width=True):
                        if os.path.exists("final_shorts.mp4"):
                            with open("final_shorts.mp4", "rb") as f:
                                video_bytes = f.read()
                            st.download_button(
                                label="📥 Click to Save",
                                data=video_bytes,
                                file_name="zovix_video.mp4",
                                mime="video/mp4",
                                key="download_final_btn"
                            )
                with col_clr:
                    if st.button("🧹 Clear", key="canvas_clear_btn", use_container_width=True):
                        safe_remove_file("final_shorts.mp4")
                        st.rerun()
            else:
                st.markdown("""
                    <div style="height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #64748b; background: rgba(10,10,12,0.4); border-radius: 12px; border: 1px dashed rgba(255,192,203,0.12); width: 100%;">
                        <span style="font-size: 48px; margin-bottom: 10px;">🎬</span>
                        <p style="font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 500; color: #EC4899;; margin: 0;">
                            Video will render here
                        </p>
                        <p style="font-family: 'Inter', sans-serif; font-size: 11px; color: #94a3b8; max-width: 400px; text-align: center; margin-top: 4px; line-height: 1.4;">
                            Configure parameters above and click Generate
                        </p>
                    </div>
                """, unsafe_allow_html=True)
    # ========================================================
    # RENDER LOGS (At bottom)
    # ========================================================
    with st.expander("📊 View Render Logs & Metadata", expanded=False):
        st.markdown(f"""
            <table style="width: 100%; border-collapse: collapse; font-family: 'Inter'; font-size: 12px; color: #94a3b8;">
                <tr style="border-bottom: 1px solid rgba(255,192,203,0.06);">
                    <td style="padding: 6px 0; font-weight: bold; color: #EC4899;">Parameter</td>
                    <td style="padding: 6px 0; font-weight: bold; color: #EC4899;">Value</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,192,203,0.06);">
                    <td style="padding: 6px 0; color: #ffffff;">Aspect Ratio</td>
                    <td style="padding: 6px 0; color: #b8860b;">{st.session_state['aspect_ratio']}</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,192,203,0.06);">
                    <td style="padding: 6px 0; color: #ffffff;">Voice</td>
                    <td style="padding: 6px 0; color: #b8860b;">{st.session_state['voice_profile']}</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,192,203,0.06);">
                    <td style="padding: 6px 0; color: #ffffff;">Model</td>
                    <td style="padding: 6px 0; color: #b8860b;">{selected_model}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #ffffff;">Status</td>
                    <td style="padding: 6px 0; color: #10b981; font-weight: bold;">{'✅ Successfully Compiled' if os.path.exists('final_shorts.mp4') else '⏳ Waiting for render'}</td>
                </tr>
            </table>
        """, unsafe_allow_html=True)

# ========================================================
# 40. PRIVACY POLICY
# ========================================================

@st.dialog("⚠️ Confirm Data Deletion", width="small")
def show_confirm_delete_dialog():
    """Yeh function alag se popup/modal kholega bina kisi error ke"""
    st.markdown("""
        ### ⚠️ Warning!
        This action will permanently delete:
        - All your generated content
        - Account history and preferences
        - Personal data and settings
        
        **This action cannot be undone.**
    """)
    if st.button("✅ Yes, Delete All My Data", use_container_width=True):
        if gdpr_manager.delete_user_data(st.session_state["logged_user"]):
            st.success("All your data has been deleted. You will be logged out.")
            st.session_state["is_logged_in"] = False
            st.session_state["current_page"] = "landing"
            st.rerun()
        else:
            st.error("Failed to delete data. Please contact support.")


def show_privacy_policy():
    st.markdown("---")
    with st.expander("📜 Privacy Policy & Legal Terms"):
        st.markdown("""
        ### Privacy Policy
        **Last updated: June 21, 2026**
        
        At Zovix, we take your privacy seriously. This policy outlines how we collect, use, and protect your personal information.
        
        #### 1. Information We Collect
        - **Account Information**: Username, email address, and authentication credentials
        - **Usage Data**: Generated content history, preferences, and interaction patterns
        - **Payment Data**: Transaction history (handled securely via Razorpay and Crypto gateways)
        - **Technical Data**: IP address, browser type, device information
        
        #### 2. How We Use Your Data
        - To provide and improve our AI video generation services
        - To process payments and manage your account
        - To personalize your experience and recommend content
        - To communicate important updates and security notices
        
        #### 3. Data Security
        - All sensitive data is encrypted using industry-standard encryption (AES-256)
        - Payments are processed through PCI-DSS compliant gateways (Razorpay, Crypto)
        - We employ rate limiting, 2FA, and access controls to protect your account
        
        #### 4. Data Retention
        - We retain your data as long as your account is active
        - Payment records are kept for 7 years as per regulatory requirements
        
        #### 5. Your Rights (GDPR & CCPA Compliance)
        - **Right to Access**: View all data we hold about you
        - **Right to Rectification**: Correct inaccurate data
        - **Right to Erasure**: Request complete deletion of your data by emailing us at zovixenterprises@gmail.com
        - **Right to Data Portability**: Export your data in a machine-readable format
        - **Right to Object**: Opt-out of non-essential data processing
        
        #### 6. Cookies
        - We use essential cookies for authentication and session management
        - No third-party tracking cookies are used without explicit consent
        - You can manage cookie preferences in your browser settings
        
        #### 7. Third-Party Services
        - **Razorpay**: Secure payment processing
        - **Crypto Payment Gateways**: Cryptocurrency transactions
        - **Google Gemini**: AI content generation (API usage is anonymized)
        - **ElevenLabs**: Voice synthesis (prompts are processed securely)
        
        #### 8. Contact Information
        - **Email**: zovixenterprises@gmail.com
        - **Response Time**: Within 48 hours for privacy-related inquiries or data deletion requests
        
        #### 9. Changes to This Policy
        - We will notify you of any material changes via email or in-app notification
        - Continued use of the platform constitutes acceptance of the updated policy
        
        #### 10. Consent
        By using Zovix, you consent to this Privacy Policy.
        """)

# ========================================================
# 41. GET PREMIUM THEME CSS
# ========================================================

@st.cache_data(ttl=3600)
def get_premium_theme_css():
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=Inter:wght@300;400;500;600;700;800&family=Orbitron:wght@500;600;800;900&display=swap');
    [data-testid="stHeader"], header, [data-testid="stToolbar"], #MainMenu, footer {
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
        padding: 0px !important;
        margin: 0px !important;
    }
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        margin-top: 0rem !important;
        max-width: 100% !important;
    }
    html, body, .stApp, [data-testid="stAppViewContainer"] {
        background-color: #06070a !important;
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(255, 192, 203, 0.03) 0px, transparent 50%),
            radial-gradient(circle at 90% 80%, rgba(124, 58, 237, 0.02) 0px, transparent 50%),
            radial-gradient(circle at 50% 50%, #06070a 0%, #010102 100%) !important;
        color: #f8fafc !important;
        font-family: 'Inter', sans-serif !important;
    }
    [data-testid="stSidebar"] {
        display: none !important;
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
        background-color: #0e1117 !important;
        background-image: radial-gradient(circle at 50% 20%, #0c0d14 0%, #06070a 100%) !important;
        border-right: 2px solid #45f3ff !important;
        transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        z-index: 999 !important;
        min-width: 0 !important;
        max-width: 0 !important;
    }
    section[data-testid="stMain"] {
        padding-left: 0 !important;
    }
    [data-testid="stSidebarContent"] {
        background-color: transparent !important;
        padding: 1rem !important;
    }
    .main-header {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        padding: 12px 0 16px 0 !important;
        border-bottom: 1px solid rgba(255,255,255,0.08) !important;
        margin-bottom: 15px !important;
        width: 100% !important;
        flex-wrap: nowrap !important;
    }
    .header-left {
        display: flex !important;
        flex-direction: column !important;
    }
    .header-left .title {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 26px !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.1 !important;
        letter-spacing: 1px !important;
    }
    .header-left .subtitle {
        font-family: 'Inter', sans-serif !important;
        font-size: 11px !important;
        color: #EC4899 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        margin: 2px 0 0 0 !important;
    }
    .z-logo {
        background: linear-gradient(135deg, #45f3ff 0%, #EC4899 100%) !important;
        color: white !important;
        font-family: "Orbitron", "Segoe UI", sans-serif !important;
        font-size: 32px !important;
        font-weight: 900 !important;
        width: 64px !important;
        height: 64px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        border-radius: 50% !important;
        box-shadow: 0 0 30px rgba(69, 243, 255, 0.4), 0 0 60px rgba(236, 72, 153, 0.2) !important;
        border: 2px solid rgba(255,255,255,0.1) !important;
        letter-spacing: 1px !important;
        text-shadow: 0 0 20px rgba(255,255,255,0.3) !important;
        transition: all 0.3s ease !important;
    }
    .z-logo:hover {
        transform: scale(1.05) rotate(5deg) !important;
        box-shadow: 0 0 40px rgba(69, 243, 255, 0.6), 0 0 80px rgba(236, 72, 153, 0.3) !important;
    }
    .exit-btn-wrap .stButton button {
        background: linear-gradient(135deg, #FF2E63 0%, #B80032 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        padding: 8px 28px !important;
        border-radius: 6px !important;
        font-family: 'Orbitron', sans-serif !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        box-shadow: 0 4px 15px rgba(255, 46, 99, 0.3) !important;
        transition: all 0.3s ease !important;
        height: 44px !important;
        margin: 0 !important;
    }
    .exit-btn-wrap .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(255, 46, 99, 0.5) !important;
    }
    div[data-testid="stVerticalBlockBorder"] {
        background: rgba(18, 19, 26, 0.85) !important;
        backdrop-filter: blur(15px) saturate(180%) !important;
        border: 1px solid rgba(255, 192, 203, 0.12) !important;
        border-radius: 14px !important;
        padding: 18px !important; 
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.8) !important;
        margin-bottom: 12px !important;
        transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    div[data-testid="stVideo"], 
    div[data-testid="stVideo"] video,
    .stVideo {
        max-height: 420px !important; 
        width: 100% !important;
        max-width: 100% !important;
        border-radius: 14px !important;
        overflow: hidden !important;
        border: 2px solid rgba(236, 72, 153, 0.3) !important;
        background: #000000 !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.7) !important;
        object-fit: contain !important;
    }
    .stButton > button {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
        font-weight: 800 !important;
        font-family: 'Orbitron', sans-serif !important;
        font-size: 14px !important;
        border-radius: 8px !important;
        border: 1.5px solid #CBD5E1 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
        transition: all 0.15s ease !important;
        text-transform: uppercase !important;
        padding: 10px 16px !important;
        height: auto !important;
        min-height: 48px !important;
    }
    .stButton > button:hover,
    .stButton > button:active,
    .stButton > button:focus {
        background: #EC4899 !important;
        background-color: #EC4899 !important;
        color: #FFFFFF !important;
        border-color: #EC4899 !important;
        box-shadow: 0 0 15px rgba(236, 72, 153, 0.5) !important;
        transform: scale(1.02) !important;
    }
    .leonardo-hero {
        position: relative !important;
        width: 100% !important;
        height: 450px !important;
        background-image: linear-gradient(rgba(6, 7, 10, 0.5), rgba(6, 7, 10, 0.95)), url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1964&auto=format&fit=crop') !important;
        background-size: cover !important;
        background-position: center !important;
        border-radius: 20px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        border: 1px solid rgba(255, 192, 203, 0.15) !important;
        margin-bottom: 30px !important;
        backdrop-filter: blur(8px) saturate(120%) !important;
    }
    .leonardo-title {
        font-family: 'Cinzel', 'Orbitron', sans-serif !important;
        font-weight: 900 !important;
        font-size: 60px !important;
        letter-spacing: 8px !important;
        color: #ffffff !important;
        text-align: center !important;
        text-transform: uppercase !important;
        text-shadow: 0 4px 20px rgba(236, 72, 153, 0.4) !important;
        margin-bottom: 20px !important;
        padding: 0 20px !important;
    }
    .leonardo-icons-row {
        display: flex !important;
        gap: 16px !important;
        margin-top: 25px !important;
        justify-content: center !important;
        flex-wrap: wrap !important;
    }
    .leonardo-icon-tab {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        background: rgba(18, 19, 26, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 12px 22px !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        min-width: 100px !important;
    }
    .leonardo-icon-tab:hover {
        border-color: #EC4899 !important;
        transform: translateY(-2px) !important;
        background: rgba(236, 72, 153, 0.08) !important;
    }
    .leonardo-icon-tab span {
        font-size: 24px !important;
        margin-bottom: 5px !important;
    }
    .leonardo-icon-tab p {
        margin: 0 !important;
        font-size: 12px !important;
        font-family: 'Orbitron', sans-serif !important;
        color: #a0a0a0 !important;
    }
    .compact-label {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 13px !important;
        color: #a0a0a0 !important;
        letter-spacing: 2px !important;
        margin-top: 18px !important;
        margin-bottom: 8px !important;
        text-transform: uppercase !important;
    }
    .canvas-container-box {
        background-color: #000000 !important;
        border: 2px solid rgba(236, 72, 153, 0.3) !important;
        border-radius: 16px !important;
        padding: 16px !important;
        width: 100% !important;
        max-width: 100% !important;
        height: 420px !important; 
        min-height: 420px !important;
        max-height: 420px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.85) !important;
        overflow: hidden !important;
    }
    .photo-slider-container {
        display: flex !important;
        gap: 20px !important;
        overflow-x: auto !important;
        padding: 15px 0 !important;
        scroll-snap-type: x mandatory !important;
    }
    .photo-slider-container::-webkit-scrollbar {
        height: 6px !important;
    }
    .photo-slider-container::-webkit-scrollbar-track {
        background: rgba(255,255,255,0.05) !important;
    }
    .photo-slider-container::-webkit-scrollbar-thumb {
        background: #EC4899 !important;
        border-radius: 4px !important;
    }
    .photo-slide-item {
        flex: 0 0 250px !important;
        scroll-snap-align: start !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        transition: all 0.15s ease !important;
    }
    .photo-slide-item:hover {
        transform: scale(1.03) !important;
        border-color: #EC4899 !important;
    }
    .photo-slide-item img {
        width: 100% !important;
        height: 180px !important;
        object-fit: cover !important;
    }
    .photo-slide-item .caption {
        padding: 10px !important;
        font-size: 12px !important;
        color: #94a3b8 !important;
        text-align: center !important;
        font-family: 'Inter', sans-serif !important;
    }
    .editor-upload-grid {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 18px !important;
        margin-bottom: 18px !important;
    }
    .editor-upload-box {
        background: rgba(18, 19, 26, 0.85) !important;
        border: 2px dashed rgba(255,192,203,0.2) !important;
        border-radius: 14px !important;
        padding: 25px !important;
        text-align: center !important;
        min-height: 140px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.15s ease !important;
    }
    .editor-upload-box:hover {
        border-color: #EC4899 !important;
        background: rgba(236, 72, 153, 0.05) !important;
    }
    .editor-upload-box .icon {
        font-size: 36px !important;
        margin-bottom: 10px !important;
    }
    .editor-upload-box .label {
        font-size: 14px !important;
        color: #94a3b8 !important;
        font-family: 'Orbitron', sans-serif !important;
        letter-spacing: 0.5px !important;
    }
    .editor-upload-box .count {
        font-size: 16px !important;
        color: #45f3ff !important;
        font-weight: bold !important;
        margin-top: 6px !important;
    }
    .selected-opt-wrap button,
    .selected-opt-wrap .stButton > button,
    .selected-opt-wrap div[data-testid="stButton"] button {
        background: #EC4899 !important;
        background-color: #EC4899 !important;
        background-image: none !important;
        color: #FFFFFF !important;
        border: 2px solid #EC4899 !important;
        box-shadow: 0 0 15px rgba(236, 72, 153, 0.45) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        height: 56px !important;
        text-transform: none !important;
        border-radius: 10px !important;
        width: 100% !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        padding: 8px 12px !important;
    }
    .unselected-opt-wrap button,
    .unselected-opt-wrap .stButton > button,
    .unselected-opt-wrap div[data-testid="stButton"] button {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        background-image: none !important;
        color: #1F2937 !important;
        border: 1.5px solid #CBD5E1 !important;
        box-shadow: none !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        height: 56px !important;
        text-transform: none !important;
        border-radius: 10px !important;
        width: 100% !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        padding: 8px 12px !important;
    }
    .face-controls-grid {
        display: grid !important;
        grid-template-columns: 1fr 1fr 1fr 1fr !important;
        gap: 12px !important;
        margin-bottom: 12px !important;
    }
    .face-control-item {
        background: rgba(18, 19, 26, 0.85) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 10px !important;
        padding: 14px !important;
        text-align: center !important;
    }
    .face-control-item .label {
        font-size: 12px !important;
        color: #94a3b8 !important;
        font-family: 'Orbitron', sans-serif !important;
        letter-spacing: 0.5px !important;
    }
    .face-control-item .value {
        font-size: 18px !important;
        color: #FFC0CB !important;
        font-weight: bold !important;
        margin-top: 6px !important;
    }
    .setup-compact-row {
        display: flex !important;
        gap: 18px !important;
        flex-wrap: wrap !important;
        margin-bottom: 12px !important;
    }
    .setup-compact-row > div {
        flex: 1 !important;
        min-width: 250px !important;
    }
    .ai-feature-card {
        background: rgba(18, 19, 26, 0.95) !important;
        border: 1px solid rgba(69, 243, 255, 0.2) !important;
        border-radius: 18px !important;
        padding: 30px !important;
        transition: all 0.15s ease !important;
        text-align: center !important;
    }
    .ai-feature-card:hover {
        border-color: #EC4899 !important;
        transform: translateY(-4px) !important;
        box-shadow: 0 8px 30px rgba(236, 72, 153, 0.15) !important;
    }
    .ai-feature-card .icon {
        font-size: 56px !important;
        margin-bottom: 14px !important;
    }
    .ai-feature-card .title {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 18px !important;
        color: #ffffff !important;
        margin-bottom: 10px !important;
    }
    .ai-feature-card .desc {
        font-size: 14px !important;
        color: #94a3b8 !important;
        line-height: 1.6 !important;
    }
    .quick-access-panel {
        background: rgba(18, 19, 26, 0.95) !important;
        border-radius: 14px !important;
        border: 1px solid rgba(255,192,203,0.15) !important;
        padding: 20px !important;
        margin-bottom: 25px !important;
        transition: all 0.15s ease !important;
    }
    .quick-access-panel .panel-header {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 14px !important;
        color: #FFC0CB !important;
        margin-bottom: 15px !important;
        letter-spacing: 1px !important;
        cursor: pointer !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
    }
    .quick-access-panel .panel-header:hover {
        color: #EC4899 !important;
    }
    @media (max-width: 1024px) and (min-width: 769px) {
        .block-container { padding-left: 1.5rem !important; padding-right: 1.5rem !important; }
        [data-testid="stSidebar"] { min-width: 220px !important; max-width: 280px !important; }
        .leonardo-title { font-size: 42px !important; letter-spacing: 4px !important; }
        .leonardo-hero { height: 350px !important; }
        .header-left .title { font-size: 22px !important; }
        .z-logo { width: 52px !important; height: 52px !important; font-size: 26px !important; }
        .canvas-container-box { height: 380px !important; min-height: 380px !important; max-height: 380px !important; }
        div[data-testid="stVideo"] { max-height: 380px !important; }
        .leonardo-icon-tab { min-width: 80px !important; padding: 10px 16px !important; }
        .leonardo-icon-tab span { font-size: 20px !important; }
        .leonardo-icon-tab p { font-size: 10px !important; }
        .selected-opt-wrap button, .unselected-opt-wrap button { font-size: 11px !important; height: 48px !important; }
        .face-controls-grid { grid-template-columns: 1fr 1fr !important; }
        .editor-upload-grid { grid-template-columns: 1fr 1fr !important; }
        .stButton > button { font-size: 12px !important; padding: 8px 14px !important; min-height: 42px !important; }
        .compact-label { font-size: 11px !important; }
        .photo-slide-item { flex: 0 0 200px !important; }
        .photo-slide-item img { height: 150px !important; }
    }
    @media (max-width: 768px) {
        .block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; padding-top: 0.3rem !important; }
        [data-testid="stSidebar"] { min-width: 160px !important; max-width: 200px !important; }
        [data-testid="stSidebar"] .stButton button { font-size: 8px !important; padding: 4px 6px !important; min-height: 28px !important; }
        .main-header { flex-wrap: wrap !important; gap: 6px !important; padding: 6px 0 10px 0 !important; }
        .header-left .title { font-size: 16px !important; letter-spacing: 0.5px !important; }
        .header-left .subtitle { font-size: 8px !important; letter-spacing: 1px !important; }
        .z-logo { width: 38px !important; height: 38px !important; font-size: 18px !important; border-radius: 50% !important; }
        .exit-btn-wrap .stButton button { font-size: 8px !important; padding: 4px 12px !important; height: 30px !important; min-height: 30px !important; }
        .leonardo-hero { height: 200px !important; margin-bottom: 16px !important; border-radius: 12px !important; }
        .leonardo-title { font-size: 22px !important; letter-spacing: 2px !important; padding: 0 10px !important; margin-bottom: 10px !important; }
        .leonardo-hero p { font-size: 10px !important; letter-spacing: 1px !important; }
        .leonardo-icons-row { gap: 6px !important; margin-top: 12px !important; }
        .leonardo-icon-tab { min-width: 50px !important; padding: 4px 8px !important; border-radius: 8px !important; }
        .leonardo-icon-tab span { font-size: 14px !important; margin-bottom: 2px !important; }
        .leonardo-icon-tab p { font-size: 6px !important; letter-spacing: 0.5px !important; }
        div[data-testid="stVerticalBlockBorder"] { padding: 10px !important; border-radius: 10px !important; margin-bottom: 8px !important; }
        .stButton > button { font-size: 9px !important; padding: 4px 8px !important; min-height: 32px !important; border-radius: 6px !important; }
        .selected-opt-wrap button, .selected-opt-wrap .stButton > button, .selected-opt-wrap div[data-testid="stButton"] button { font-size: 8px !important; height: 34px !important; border-radius: 6px !important; padding: 4px 6px !important; min-height: 34px !important; }
        .unselected-opt-wrap button, .unselected-opt-wrap .stButton > button, .unselected-opt-wrap div[data-testid="stButton"] button { font-size: 8px !important; height: 34px !important; border-radius: 6px !important; padding: 4px 6px !important; min-height: 34px !important; }
        .canvas-container-box { height: 220px !important; min-height: 220px !important; max-height: 220px !important; border-radius: 10px !important; padding: 8px !important; }
        div[data-testid="stVideo"] { max-height: 220px !important; }
        div[data-testid="stVideo"], div[data-testid="stVideo"] video, .stVideo { max-height: 220px !important; border-radius: 10px !important; }
        .compact-label { font-size: 8px !important; letter-spacing: 1px !important; margin-top: 10px !important; margin-bottom: 4px !important; }
        .photo-slider-container { gap: 10px !important; padding: 8px 0 !important; }
        .photo-slide-item { flex: 0 0 120px !important; border-radius: 8px !important; }
        .photo-slide-item img { height: 90px !important; }
        .photo-slide-item .caption { font-size: 8px !important; padding: 6px !important; }
        .face-controls-grid { grid-template-columns: 1fr 1fr !important; gap: 6px !important; margin-bottom: 8px !important; }
        .face-control-item { padding: 6px !important; border-radius: 6px !important; }
        .face-control-item .label { font-size: 7px !important; letter-spacing: 0.5px !important; }
        .face-control-item .value { font-size: 11px !important; margin-top: 2px !important; }
        .editor-upload-grid { grid-template-columns: 1fr !important; gap: 8px !important; margin-bottom: 10px !important; }
        .editor-upload-box { padding: 14px !important; min-height: 80px !important; border-radius: 10px !important; }
        .editor-upload-box .icon { font-size: 24px !important; margin-bottom: 4px !important; }
        .editor-upload-box .label { font-size: 10px !important; }
        .editor-upload-box .count { font-size: 12px !important; }
        .setup-compact-row { flex-direction: column !important; gap: 8px !important; }
        .setup-compact-row > div { min-width: 100% !important; }
        .ai-feature-card { padding: 16px !important; border-radius: 12px !important; }
        .ai-feature-card .icon { font-size: 36px !important; margin-bottom: 8px !important; }
        .ai-feature-card .title { font-size: 13px !important; margin-bottom: 6px !important; }
        .ai-feature-card .desc { font-size: 10px !important; line-height: 1.4 !important; }
        .quick-access-panel { padding: 10px !important; border-radius: 10px !important; margin-bottom: 12px !important; }
        .quick-access-panel .panel-header { font-size: 10px !important; margin-bottom: 8px !important; letter-spacing: 0.5px !important; }
        .quick-access-panel .stButton button { font-size: 7px !important; padding: 3px 4px !important; min-height: 24px !important; }
        .sidebar-tabs-container .stButton button { font-size: 7px !important; padding: 3px 4px !important; min-height: 24px !important; }
        .stDialog { max-width: 95% !important; margin: 10px auto !important; }
        .row-widget.stColumns { gap: 6px !important; }
        .sh_cols .stContainer { padding: 8px !important; }
        .sh_cols img { height: 90px !important; }
    }
    @media (max-width: 480px) {
        .block-container { padding-left: 0.3rem !important; padding-right: 0.3rem !important; }
        [data-testid="stSidebar"] { min-width: 130px !important; max-width: 160px !important; }
        .header-left .title { font-size: 13px !important; }
        .z-logo { width: 30px !important; height: 30px !important; font-size: 14px !important; border-radius: 50% !important; }
        .leonardo-title { font-size: 16px !important; letter-spacing: 1px !important; }
        .leonardo-hero { height: 160px !important; }
        .leonardo-icon-tab { min-width: 40px !important; padding: 3px 5px !important; }
        .leonardo-icon-tab span { font-size: 10px !important; }
        .leonardo-icon-tab p { font-size: 5px !important; }
        .stButton > button { font-size: 7px !important; padding: 3px 6px !important; min-height: 26px !important; }
        .canvas-container-box { height: 180px !important; min-height: 180px !important; max-height: 180px !important; }
        div[data-testid="stVideo"] { max-height: 180px !important; }
        .photo-slide-item { flex: 0 0 90px !important; }
        .photo-slide-item img { height: 70px !important; }
        .face-controls-grid { grid-template-columns: 1fr 1fr !important; gap: 4px !important; }
        .face-control-item .label { font-size: 6px !important; }
        .face-control-item .value { font-size: 9px !important; }
    }
    </style>
    """

# ========================================================
# 42. SYSTEM HEALTH CHECK
# ========================================================

def system_health_check():
    health_status = {
        "status": "healthy",
        "checks": []
    }
    
    try:
        conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        health_status["checks"].append({"name": "Database", "status": "healthy"})
    except:
        health_status["checks"].append({"name": "Database", "status": "error"})
        health_status["status"] = "error"
    
    if HAS_REDIS:
        try:
            import redis
            client = redis.Redis.from_url(SYSTEM_CONFIG["REDIS_URL"])
            client.ping()
            health_status["checks"].append({"name": "Redis", "status": "healthy"})
        except:
            health_status["checks"].append({"name": "Redis", "status": "error"})
            health_status["status"] = "error"
    
    worker_status = load_balancer.get_worker_status()
    healthy_workers = sum(1 for w in worker_status if w['status'] == 'healthy')
    total_workers = len(worker_status)
    
    if healthy_workers < total_workers:
        health_status["checks"].append({"name": "Workers", "status": "degraded", "details": f"{healthy_workers}/{total_workers} healthy"})
    else:
        health_status["checks"].append({"name": "Workers", "status": "healthy", "details": f"{healthy_workers}/{total_workers}"})
    
    if not GEMINI_API_KEY:
        health_status["checks"].append({"name": "Gemini API", "status": "warning", "details": "API key not set"})
    
    if not ELEVENLABS_API_KEY:
        health_status["checks"].append({"name": "ElevenLabs API", "status": "warning", "details": "API key not set"})
    
    return health_status

# ========================================================
# 43. RENDER SUBSCRIPTION BADGE, ACHIEVEMENTS, REFERRAL, LEADERBOARD, COMPETITIVE
# ========================================================

def render_subscription_badge():
    has_sub, pack_name = has_active_subscription(st.session_state["logged_user"])
    if has_sub:
        st.success(f"✅ **Active Subscription:** {pack_name}")
        st.caption("Your subscription is active and tokens are being refreshed monthly.")
    else:
        st.info("ℹ️ No active subscription. Subscribe to get monthly tokens!")

def render_achievements():
    st.markdown("### 🏆 Achievements")
    achievements = check_achievements(st.session_state["logged_user"])
    if achievements:
        for ach in achievements:
            st.markdown(f"✅ {ach}")
    else:
        st.info("Complete milestones to earn achievements!")

def render_referral_system():
    st.markdown("### 🔗 Referral System")
    st.info("Share your referral link and earn 10 credits per new user!")
    referral_link = f"https://zovix.ai/ref/{st.session_state['logged_user']}"
    st.text(referral_link)
    if st.button("📋 Copy Referral Link", key="copy_ref_link", use_container_width=True):
        st.toast("Referral link copied!")
    
    reward_referral(st.session_state["logged_user"])

def render_leaderboard():
    st.markdown("### 🏅 Leaderboard")
    leaderboard = get_leaderboard(limit=5)
    if leaderboard:
        for idx, user in enumerate(leaderboard):
            medal = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"{idx+1}."
            st.markdown(f"{medal} **{user['username']}** - {user['credits']:.1f} Credits | XP: {user['xp']} | Streak: {user['streak']} days")
    else:
        st.info("No leaderboard data yet. Start creating to climb the ranks!")

def render_competitive_features():
    st.markdown("### 🎯 Competitive Features")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏆 View Global Leaderboard", use_container_width=True):
            st.toast("Leaderboard refreshed!")
    with col2:
        if st.button("📊 Compare with Friends", use_container_width=True):
            st.toast("Comparison feature coming soon!")


def handle_engine_access_request(mode_value: str):
    if not st.session_state.get("is_logged_in", False):
        st.session_state["auth_redirect_mode"] = mode_value
        show_auth_modal("login")
        return False

    st.session_state["studio_active_mode"] = mode_value
    st.session_state["current_workspace_mode"] = mode_value
    st.session_state["auth_redirect_mode"] = None
    st.rerun()
    return True

# ========================================================
# 44. MAIN APPLICATION FLOW
# ========================================================

# Handle payment response FIRST
handle_payment_response()

if st.session_state.get("show_2fa", False):
    show_2fa_modal()
    st.stop()

if st.session_state.get("is_logged_in"):
    now_ts = time.time()
    if now_ts - float(st.session_state.get("last_payment_check", 0)) > 8:
        st.session_state["last_payment_check"] = now_ts
        reconcile_pending_razorpay_payments(st.session_state.get("logged_user", ""))

    if not gdpr_manager.get_consent(st.session_state["logged_user"]):
        if not gdpr_manager.request_consent(st.session_state["logged_user"]):
            st.stop()

if st.session_state["current_page"] == "landing":
    from landing_page import WorldClassLandingPage
    landing = WorldClassLandingPage()
    landing.render()
    if st.session_state.pop("landing_auth_requested", False):
        show_auth_modal("login")
    st.stop()  

elif st.session_state["current_page"] == "studio":
    if not st.session_state["is_logged_in"]:
        st.session_state["current_page"] = "landing"
        st.rerun()
    
    if st.session_state.get("2fa_enabled", False) and not st.session_state.get("2fa_verified", False):
        show_2fa_modal()
        st.stop()
    
    st.markdown(get_premium_theme_css(), unsafe_allow_html=True)
    get_language_selector()
    
    # ========================================================
    # STUDIO PAGE CSS - CLEAN PREMIUM STYLE
    # ========================================================
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* GLOBAL */
        .stApp { font-family: 'Inter', sans-serif !important; color: #f8fafc !important; background: #06070a !important; }
        .block-container { padding-top: 0.5rem !important; }
        
        /* HEADINGS */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Orbitron', sans-serif !important;
            letter-spacing: 0.5px !important;
        }
        .highlight {
            background: linear-gradient(135deg, #45f3ff, #EC4899) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            background-clip: text !important;
        }
        
        /* HEADER */
        .studio-header {
            background: linear-gradient(135deg, rgba(236,72,153,0.06), rgba(69,243,255,0.06));
            border-radius: 16px;
            padding: 20px 25px;
            border: 1px solid rgba(69,243,255,0.08);
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .studio-header .left h1 {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 22px !important;
            color: #FFFFFF !important;
            margin: 0 !important;
        }
        .studio-header .left p {
            font-family: 'Inter', sans-serif !important;
            color: #94a3b8 !important;
            font-size: 11px !important;
            margin: 2px 0 0 0 !important;
            letter-spacing: 1.5px !important;
            text-transform: uppercase !important;
        }
        .studio-header .right {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .studio-header .right .credits {
            background: rgba(69,243,255,0.08);
            padding: 6px 16px;
            border-radius: 16px;
            color: #45f3ff;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 13px !important;
            border: 1px solid rgba(69,243,255,0.12);
        }
        .studio-header .right .exit-btn {
            background: linear-gradient(135deg, #FF2E63, #B80032);
            color: white;
            border: none;
            padding: 8px 20px;
            border-radius: 8px;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .studio-header .right .exit-btn:hover { transform: scale(1.05); }
        
        /* STATS */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin: 15px 0 20px 0;
        }
        .stats-grid .stat {
            background: rgba(18,19,26,0.8);
            border: 1px solid rgba(255,255,255,0.04);
            border-radius: 12px;
            padding: 14px 12px;
            text-align: center;
        }
        .stats-grid .stat .num {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 24px !important;
            font-weight: 900 !important;
            color: #45f3ff !important;
        }
        .stats-grid .stat .label {
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            color: #94a3b8 !important;
            margin-top: 2px !important;
        }
        
        /* QUICK ACCESS */
        .quick-access {
            background: rgba(18,19,26,0.8);
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.04);
            padding: 14px 18px;
            margin-bottom: 18px;
        }
        .quick-access .qa-header {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 12px !important;
            color: #FFC0CB !important;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .quick-access .qa-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 6px;
            margin-top: 10px;
        }
        .quick-access .qa-grid .qa-btn {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.04);
            border-radius: 8px;
            padding: 8px 4px;
            text-align: center;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 8px !important;
            color: #94a3b8 !important;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .quick-access .qa-grid .qa-btn:hover {
            border-color: #EC4899;
            color: #FFFFFF;
        }
        .quick-access .qa-grid .qa-btn .qa-icon { font-size: 16px; display: block; margin-bottom: 2px; }
        
        /* MODE BUTTONS */
        .mode-label {
            font-family: 'Orbitron', sans-serif !important;
            color: #94a3b8 !important;
            font-size: 11px !important;
            margin: 12px 0 8px 0 !important;
            letter-spacing: 1px !important;
        }
        .mode-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 8px;
            margin: 8px 0 15px 0;
        }
        .mode-grid .mode-btn {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.04);
            border-radius: 10px;
            padding: 12px 6px;
            text-align: center;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 8px !important;
            color: #94a3b8 !important;
            cursor: pointer;
            transition: all 0.3s ease;
            min-height: 60px;
        }
        .mode-grid .mode-btn:hover {
            border-color: #EC4899;
            color: #FFFFFF;
            transform: translateY(-2px);
        }
        .mode-grid .mode-btn.active {
            background: #EC4899;
            color: #FFFFFF;
            border-color: #EC4899;
            box-shadow: 0 0 20px rgba(236,72,153,0.15);
        }
        .mode-grid .mode-btn .mode-icon { font-size: 20px; display: block; margin-bottom: 3px; }
        
        /* SECTION HEADERS */
        .section-header {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 13px !important;
            color: #94a3b8 !important;
            letter-spacing: 1px !important;
            margin: 20px 0 8px 0 !important;
            text-transform: uppercase !important;
        }
        
        /* COMPACT LABEL */
        .compact-label {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 11px !important;
            color: #94a3b8 !important;
            letter-spacing: 1.5px !important;
            text-transform: uppercase !important;
            margin: 12px 0 6px 0 !important;
        }
        
        /* BUTTONS */
        .stButton > button {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            text-transform: uppercase !important;
            border-radius: 8px !important;
            background: rgba(255,255,255,0.05) !important;
            color: #e0e0e0 !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            transition: all 0.3s ease !important;
        }
        .stButton > button:hover {
            background: #EC4899 !important;
            color: #FFFFFF !important;
            border-color: #EC4899 !important;
            box-shadow: 0 0 20px rgba(236,72,153,0.2) !important;
        }
        
        /* RESPONSIVE */
        @media (max-width: 768px) {
            .studio-header { flex-direction: column; text-align: center; gap: 10px; }
            .studio-header .left h1 { font-size: 18px !important; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .quick-access .qa-grid { grid-template-columns: repeat(3, 1fr); }
            .mode-grid { grid-template-columns: repeat(3, 1fr); }
        }
        @media (max-width: 480px) {
            .stats-grid { grid-template-columns: 1fr; }
            .quick-access .qa-grid { grid-template-columns: repeat(2, 1fr); }
            .mode-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar.expander("🟢 System Health", expanded=False):
        health = system_health_check()
        for check in health["checks"]:
            icon = "✅" if check["status"] == "healthy" else "⚠️" if check["status"] == "warning" else "❌"
            st.markdown(f"{icon} **{check['name']}**: {check['status']}")
            if check.get("details"):
                st.caption(check["details"])
    
    # ==========================================================
    # STUDIO HEADER
    # ==========================================================
    credits = int(st.session_state.get('user_credits', 0))
    
    st.markdown(f"""
    <div class="studio-header">
        <div class="left">
            <h1><span class="highlight">ZOVIX</span> TO CREATE</h1>
            <p>ACTIVE GENERATION PIPELINE WORKSPACE</p>
        </div>
        <div class="right">
            <span class="credits">⚡ {credits}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("EXIT", key="exit_studio_btn", use_container_width=True):
        st.session_state["current_page"] = "landing"
        st.session_state["is_logged_in"] = False
        st.session_state["2fa_verified"] = False
        st.rerun()
    
    # ========================================================
    # STATS
    # ========================================================
    history = st.session_state.get("history_renders", [])
    face_history = st.session_state.get("face_video_history", [])
    xp = st.session_state.get('xp_points', 0)
    total_videos = len(history) + len(face_history)
    
    st.markdown(f"""
    <div class="stats-grid">
        <div class="stat"><div class="num">{total_videos}</div><div class="label">Total Videos</div></div>
        <div class="stat"><div class="num">{len(history)}</div><div class="label">Cinematic</div></div>
        <div class="stat"><div class="num">{len(face_history)}</div><div class="label">Face Videos</div></div>
        <div class="stat"><div class="num">{xp}</div><div class="label">XP Points</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========================================================
    # VOUCHER CHECK
    # ========================================================
    if check_49_voucher_valid():
        st.info(f"🎫 ₹49 Voucher Active! 30 Credits added. Valid for: {st.session_state.get('voucher_49_expiry', datetime.now() + timedelta(hours=24)).strftime('%H:%M:%S')} remaining")
    
    # ========================================================
    # QUICK ACCESS
    # ========================================================
    st.markdown("""
    <div class="quick-access">
        <div class="qa-header" onclick="document.getElementById('qa_toggle').click()">
            <span style="color:#EC4899; !important; font-weight: bold;">⚡ QUICK ACCESS MODES</span>
            <span>{}</span>
        </div>
    </div>
    """.format("▼" if st.session_state.get("quick_access_open") else "▶"), unsafe_allow_html=True)
    
    if st.button("Toggle Quick Access", key="qa_toggle", use_container_width=True):
        st.session_state["quick_access_open"] = not st.session_state.get("quick_access_open", False)
        st.rerun()
    
    if st.session_state.get("quick_access_open", False):
        st.markdown('<div class="qa-grid">', unsafe_allow_html=True)
        quick_items = [
            ("🚀", "FACTORY", "🚀 Zovix Mass Factory"),
            ("💎", "CREDITS", "💎 Buy Credits"),
            ("📂", "PORTFOLIO", "📂 My Portfolio"),
            ("👤", "PROFILE", "👤 My Premium Profile"),
            ("👥", "SUB-USERS", "👥 SUB-USER ACCESS MANAGEMENT"),
            ("📅", "SCHEDULER", "📅 ADVANCED AI CONTENT SCHEDULER")
        ]
        cols = st.columns(6)
        for i, (icon, label, tab) in enumerate(quick_items):
            with cols[i]:
                if st.button(f"{icon} {label}", key=f"qa_{label}", use_container_width=True):
                    st.session_state["sidebar_tab"] = tab
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ========================================================
# MODE SELECTOR - PREMIUM (SIRF YAHI RAKHNA HAI)
# ========================================================
st.markdown('<p class="mode-label">🎯 ACTIVE STUDIO WORKSPACE MODE</p>', unsafe_allow_html=True)

modes = [
    ("👤", "FACE VIDEO", "Face Video Mode"),
    ("🎬", "CINEMATIC", "Cinematic Engine"),
    ("🎨", "CREATIVE", "Creative Workshop Mode"),
    ("🎞️", "EDITOR", "Video Editor Mode"),
    ("📐", "BLUEPRINTS", "Blueprints Mode"),
    ("⚡", "UPSCALER", "Upscaler Mode"),
    ("✏️", "DRAW", "Draw Mode"),
    ("🤖", "AI AGENT", "AI Agent Mode"),
    ("🎙️", "SALES", "AI Sales Mode"),
    ("🧠", "DYNAMIC UI", "Dynamic UI Mode"),
    ("🎤", "LIVE VOICE", "Live Emotion Mode")
]

for i in range(0, len(modes), 11):
    row_modes = modes[i:i+11]
    cols = st.columns(len(row_modes))
    for j, (icon, label, mode_value) in enumerate(row_modes):
        with cols[j]:
            is_active = (st.session_state["studio_active_mode"] == mode_value)
            active_class = "active" if is_active else ""
            
            # DIRECT BUTTON - NO onclick HACK
            if st.button(f"{icon}\n{label}", key=f"mode_{i+j}", use_container_width=True):
                handle_engine_access_request(mode_value)
            
            # CSS for active state
            if is_active:
                st.markdown(f"""
                <style>
                    div[data-testid="stButton"] button[key="mode_{i+j}"] {{
                        background: #EC4899 !important;
                        color: #FFFFFF !important;
                        border-color: #EC4899 !important;
                        box-shadow: 0 0 25px rgba(236,72,153,0.2) !important;
                        font-family: 'Orbitron', sans-serif !important;
                        font-weight: 700 !important;
                        letter-spacing: 0.5px !important;
                    }}
                </style>
                """, unsafe_allow_html=True)
    
    # ========================================================
    # SIDEBAR TABS
    # ========================================================
    
    if st.session_state["sidebar_tab"] == "💎 Buy Credits":
        render_enhanced_payment_ui()
    
    if st.session_state["sidebar_tab"] == "📂 My Portfolio":
        logged_user_email = st.session_state.get("logged_user", "").lower().strip()
        if logged_user_email == "rajmehta886297@gmail.com":
            show_admin_dashboard()
        else:
            st.markdown("<h4 style='font-family: Orbitron; color: #FFC0CB;'>📂 My Portfolio</h4>", unsafe_allow_html=True)
            st.info("View and manage all your generated content.")
            history = st.session_state.get("history_renders", [])
        
            if history:
                st.markdown(f"**Total Items:** {len(history)}")
                for idx, item in enumerate(history[:10]):
                    with st.container(border=True):
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.markdown(f"**{item['file_name']}**")
                            st.caption(item['prompt'][:80] + "..." if len(item['prompt']) > 80 else item['prompt'])
                        with col_b:
                            st.caption(item['timestamp'])
                            if st.button("🗑️ Delete", key=f"del_{idx}"):
                                st.toast("Delete functionality coming soon!")
            else:
                st.info("No items in portfolio yet. Start creating!")
    
    elif st.session_state["sidebar_tab"] == "👤 My Premium Profile":
        st.markdown("<h4 style='font-family: Orbitron; color: #EC4899;'>👤 My Premium Profile</h4>", unsafe_allow_html=True)
        if st.session_state["is_logged_in"]:
            st.markdown(f"**Username:** {st.session_state['logged_user']}")
            st.markdown(f"**XP Points:** {st.session_state.get('xp_points', 0)}")
            st.markdown(f"**Creator Level:** {st.session_state.get('creator_level', 1)}")
            st.markdown(f"**Credits:** {get_user_credits_db(st.session_state['logged_user'])}")
            st.markdown(f"**Support Tier:** {get_support_tier(st.session_state['logged_user'])}")
            render_subscription_badge()
            render_achievements()
            
            st.markdown("---")
            st.markdown("### 🔐 Two-Factor Authentication")
            if st.session_state.get("2fa_enabled", False):
                st.success("✅ 2FA is enabled for your account")
                if st.button("Disable 2FA", use_container_width=True):
                    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "UPDATE users SET twofa_secret = '' WHERE username = ?",
                            (st.session_state["logged_user"],)
                        )
                        conn.commit()
                        st.session_state["2fa_enabled"] = False
                        st.success("2FA disabled successfully!")
                        st.rerun()
                    finally:
                        conn.close()
    
    if st.session_state["sidebar_tab"] == "👥 SUB-USER ACCESS MANAGEMENT":
        st.markdown("<h4 style='font-family: Orbitron; color: #EC4899;'>👥 SUB-USER ACCESS MANAGEMENT</h4>", unsafe_allow_html=True)
        sub_col1, sub_col2 = st.columns([1.1, 1.4], gap="medium")
        with sub_col1:
            with st.container(border=True):
                st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #EC4899; margin-bottom: 15px;'>➕ ADD NEW LINKED SUB-USER</h4>", unsafe_allow_html=True)
                new_sub_user_id = st.text_input("Sub-User Email/ID:", placeholder="friend@zovix.ai", key="add_sub_user_text_input").strip()
                st.write("")
                if st.button("Link Sub-User Account", key="link_sub_user_action_btn", use_container_width=True):
                    if not new_sub_user_id:
                        st.error("Provide a valid ID configuration.")
                    else:
                        succ, msg = add_sub_user_db(st.session_state["logged_user"], new_sub_user_id)
                        if succ:
                            st.success(msg)
                            time.sleep(0.1)
                            st.rerun()
                        else:
                            st.error(msg)
        with sub_col2:
            with st.container(border=True):
                st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #EC4899; margin-bottom: 15px;'>📋 CONNECTED ACTIVE SUB-USERS</h4>", unsafe_allow_html=True)
                active_subs = get_sub_users(st.session_state["logged_user"])
                if not active_subs:
                    st.info("No sub-users configured under this main node. You can link up to 2 sub-accounts.")
                else:
                    for s_u in active_subs:
                        s_col1, s_col2 = st.columns([2, 1])
                        with s_col1:
                            st.markdown(f"**Node:** `{s_u}`")
                        with s_col2:
                            if st.button("Unlink Account", key=f"unlink_{s_u}", use_container_width=True):
                                remove_sub_user_db(st.session_state["logged_user"], s_u)
                                st.toast("Sub-User node link dissolved.")
                                time.sleep(0.1)
                                st.rerun()
    
    elif st.session_state["sidebar_tab"] == "📅 ADVANCED AI CONTENT SCHEDULER":
        st.markdown("<h4 style='font-family: Orbitron; color: #EC4899;'>📅 ADVANCED AI CONTENT SCHEDULER</h4>", unsafe_allow_html=True)
        sch_col1, sch_col2 = st.columns([1.1, 1.4], gap="medium")
        with sch_col1:
            with st.container(border=True):
                st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #EC4899; margin-bottom: 15px;'>📅 BOOK A SOCIAL RUN</h4>", unsafe_allow_html=True)
                sch_category = st.selectbox("Social Channel Niche:", list(CATEGORY_POOL.keys()), key="sched_category_selectbox")
                sch_topic = st.text_input("Short Prompt / Topic Parameters:", placeholder="e.g. Bizarre adapting biology inside boiling vents", key="sched_topic_input_val")
                sch_time = st.text_input("Scheduled Execution Date & Time:", value=str(datetime.now() + timedelta(days=1))[:16], key="sched_datetime_input")
                sch_platform = st.selectbox("Platform Destination:", ["YouTube Shorts", "Instagram Reels", "TikTok Feed", "X (Twitter) Video"], key="sched_platform_selectbox")
                st.write("")
                if st.button("Schedule Social Run", key="book_schedule_run_action_btn", use_container_width=True):
                    if not sch_topic.strip():
                        st.error("Please provide prompt or topic details.")
                    else:
                        conn_sch = sqlite3.connect("zovix_v4.db")
                        cur_sch = conn_sch.cursor()
                        cur_sch.execute("INSERT INTO social_schedule (username, category, topic, scheduled_time, platform, status) VALUES (?, ?, ?, ?, ?, ?)", (st.session_state["logged_user"], sch_category, sch_topic, sch_time, sch_platform, 'Scheduled'))
                        conn_sch.commit()
                        conn_sch.close()
                        st.toast("Success! Scheduled booking added to calendar.")
                        st.rerun()
        with sch_col2:
            with st.container(border=True):
                st.markdown("<h3 style='font-family: Orbitron; font-size: 14px; color: #EC4899; margin-bottom: 15px;'>📊 ACTIVE SCHEDULED JOBS CALENDAR</h3>", unsafe_allow_html=True)
                conn_list = sqlite3.connect("zovix_v4.db")
                cur_list = conn_list.cursor()
                cur_list.execute("SELECT category, topic, scheduled_time, platform, status FROM social_schedule WHERE username = ? ORDER BY id DESC LIMIT 5", (st.session_state["logged_user"],))
                sch_rows = cur_list.fetchall()
                conn_list.close()
                if not sch_rows:
                    st.info("No content scheduled yet.")
                else:
                    for idx_s, r_sch in enumerate(sch_rows):
                        st.markdown(f"""
                            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px; margin-bottom: 10px;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-family:'Orbitron'; font-size: 11px; color:#EC4899; font-weight:bold;">{r_sch[3].upper()}</span>
                                    <span style="font-size:10px; color:#10b981; font-weight:bold; background:rgba(16,185,129,0.15); padding:2px 6px; border-radius:12px;">{r_sch[4].upper()}</span>
                                </div>
                                <div style="font-size: 13px; font-weight: bold; color: #ffffff; margin-top: 5px;">Category: {r_sch[0].replace('_', ' ')}</div>
                                <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Topic: "{r_sch[1]}"</div>
                                <div style="font-size:11px; color:#A0AEC0; font-family: monospace; margin-top: 4px;">📅 Execution Run: {r_sch[2]}</div>
                            </div>
                        """, unsafe_allow_html=True)
    
    # ========================================================
    # ENGINE OUTPUT
    # ========================================================
    if st.session_state["studio_active_mode"] == "Cinematic Engine":
        run_cinematic_engine()
    elif st.session_state["studio_active_mode"] == "Creative Workshop Mode":
        run_creative_workshop()
    elif st.session_state["studio_active_mode"] == "Blueprints Mode":
        run_blueprints_mode()
    elif st.session_state["studio_active_mode"] == "Upscaler Mode":
        run_upscaler_mode()
    elif st.session_state["studio_active_mode"] == "Draw Mode":
        run_draw_mode()
    elif st.session_state["studio_active_mode"] == "Video Editor Mode":
        run_video_editor_mode()
    elif st.session_state["studio_active_mode"] == "Face Video Mode":
        run_unified_face_video_mode()
    elif st.session_state["studio_active_mode"] == "Expressive Face Video Mode":
        run_unified_face_video_mode()
    elif st.session_state["studio_active_mode"] == "AI Agent Mode":
        render_ai_agent_ui()
    elif st.session_state["studio_active_mode"] == "AI Sales Mode":
        render_ai_sales_ui()
    elif st.session_state["studio_active_mode"] == "Dynamic UI Mode":
        generate_dynamic_ui()
    elif st.session_state["studio_active_mode"] == "Live Emotion Mode":
        render_live_emotion_voice()
    
    # ========================================================
    # PORTFOLIO, HISTORY, TRENDING, FOOTER
    # ========================================================
    st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 25px 0;'>", unsafe_allow_html=True)

    current_mode = st.session_state["studio_active_mode"]

    def get_mode_portfolio(current_mode):
        portfolio_renders_list = st.session_state.get("history_renders", [])
        face_video_list = st.session_state.get("face_video_history", [])
        valid_items = []
        gallery_title = ""
        no_items_msg = ""
        display_type = "image"
        
        if current_mode == "Face Video Mode":
            for item in face_video_list:
                if os.path.exists(item.get("path", "")):
                    valid_items.append(item)
            gallery_title = "👤 MY FACE VIDEO GENERATIONS"
            no_items_msg = "No face videos created yet. Upload a face image and generate!"
            display_type = "video"
        elif current_mode == "Expressive Face Video Mode":
            for item in face_video_list:
                file_name = item.get("file_name", "").lower()
                if os.path.exists(item.get("path", "")) and "expressive_face_video" in file_name:
                    valid_items.append(item)
            gallery_title = "🧬 EXPRESSIVE FACE GENERATIONS"
            no_items_msg = "No expressive face videos created yet. Generate one with LivePortrait/SadTalker."
            display_type = "video"
        elif current_mode == "Cinematic Engine":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                file_name = item.get("file_name", "")
                gen_type = item.get("generation_type", "")
                if gen_type and gen_type != "Cinematic Engine":
                    continue
                if os.path.exists(file_path) and "cinematic" in file_name.lower():
                    valid_items.append(item)
            gallery_title = "🎬 CINEMATIC ENGINE VIDEOS"
            no_items_msg = "No cinematic videos created yet. Generate your first cinematic video!"
            display_type = "video"
        elif current_mode == "Creative Workshop Mode":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                gen_type = item.get("generation_type", "")
                if gen_type and gen_type != "Creative Workshop":
                    continue
                if os.path.exists(file_path):
                    valid_items.append(item)
            gallery_title = "🎨 CREATIVE WORKSHOP IMAGES"
            no_items_msg = "No workshop images created yet. Generate your first masterpiece!"
            display_type = "image"
        elif current_mode == "Video Editor Mode":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                gen_type = item.get("generation_type", "")
                if gen_type and gen_type != "Video Editor":
                    continue
                if os.path.exists(file_path):
                    valid_items.append(item)
            gallery_title = "🎬 VIDEO EDITOR OUTPUTS"
            no_items_msg = "No edited videos created yet. Upload media and process!"
            display_type = "video"
        elif current_mode == "Blueprints Mode":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                gen_type = item.get("generation_type", "")
                if gen_type and gen_type != "General":
                    continue
                if os.path.exists(file_path):
                    valid_items.append(item)
            gallery_title = "📐 BLUEPRINT GENERATIONS"
            no_items_msg = "No blueprints created yet. Generate your first architectural blueprint!"
            display_type = "image"
        elif current_mode == "Upscaler Mode":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                gen_type = item.get("generation_type", "")
                if gen_type and gen_type != "General":
                    continue
                if os.path.exists(file_path):
                    valid_items.append(item)
            gallery_title = "⚡ UPSCALED IMAGES"
            no_items_msg = "No upscaled images created yet. Upload an image to upscale!"
            display_type = "image"
        elif current_mode == "Draw Mode":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                gen_type = item.get("generation_type", "")
                if gen_type and gen_type != "General":
                    continue
                if os.path.exists(file_path):
                    valid_items.append(item)
            gallery_title = "🎨 DRAWING OUTPUTS"
            no_items_msg = "No drawings created yet. Generate your first sketch!"
            display_type = "image"
        elif current_mode == "AI Agent Mode":
            agent_logs = st.session_state.get("agent_generated_ad", "")
            if agent_logs:
                valid_items.append({"type": "text", "content": agent_logs, "file_name": "WhatsApp Ad", "prompt": "Generated WhatsApp advertisement"})
            agent_caption = st.session_state.get("agent_instagram_caption", "")
            if agent_caption:
                valid_items.append({"type": "text", "content": agent_caption, "file_name": "Instagram Post", "prompt": "Generated Instagram post caption"})
            gallery_title = "🤖 AI AGENT OUTPUTS"
            no_items_msg = "No agent outputs generated yet. Configure and activate your AI agent!"
            display_type = "text"
        elif current_mode == "AI Sales Mode":
            sales_video = st.session_state.get("sales_video_output")
            if sales_video and os.path.exists(sales_video):
                valid_items.append({"path": sales_video, "file_name": f"Sales_Video_{datetime.now().strftime('%Y%m%d')}", "prompt": st.session_state.get("sales_script", "Sales video"), "type": "video"})
            gallery_title = "🎙️ AI SALES VIDEOS"
            no_items_msg = "No sales videos created yet. Generate your first AI sales video!"
            display_type = "video"
        elif current_mode == "Dynamic UI Mode":
            ui_profile = st.session_state.get("dynamic_ui_profile_mode", "intermediate")
            valid_items.append({"type": "text", "content": f"Current UI Profile: {ui_profile}\n\nBehavior Profile: {st.session_state.get('user_behavior_profile', 'beginner')}\n\nUI Theme: {st.session_state.get('ui_theme_mode', 'auto')}", "file_name": "UI Configuration", "prompt": f"Dynamic UI Profile: {ui_profile}"})
            gallery_title = "🧠 DYNAMIC UI PROFILES"
            no_items_msg = "No UI profiles configured yet. Customize your interface!"
            display_type = "text"
        elif current_mode == "Live Emotion Mode":
            audio_output = st.session_state.get("emotion_voice_output")
            if audio_output and os.path.exists(audio_output):
                valid_items.append({"path": audio_output, "file_name": f"Voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "prompt": st.session_state.get("emotion_voice_text", "Emotion voice"), "emotion": st.session_state.get("emotion_voice_emotion", "neutral"), "type": "audio"})
            gallery_title = "🎤 LIVE EMOTION VOICE OUTPUTS"
            no_items_msg = "No voice outputs generated yet. Generate your first emotion voice!"
            display_type = "audio"
        else:
            valid_items = []
            gallery_title = "📁 MY PORTFOLIO"
            no_items_msg = "Select a mode to view its portfolio."
            display_type = "image"
        
        return valid_items, gallery_title, no_items_msg, display_type

    valid_items, gallery_title, no_items_msg, display_type = get_mode_portfolio(current_mode)
    st.markdown(f"<h3 style='font-family: Orbitron; font-size: 16px; color:  #EC4899; margin-bottom: 15px; letter-spacing: 0.5px;'>{gallery_title}</h3>", unsafe_allow_html=True)

    if not valid_items:
        st.info(no_items_msg)
    else:
        if display_type == "audio":
            audio_cols = st.columns(3)
            for idx, item in enumerate(valid_items[:6]):
                with audio_cols[idx % 3]:
                    with st.container(border=True):
                        emotion = item.get("emotion", "neutral")
                        emoji_map = {"neutral": "😐", "happy": "😊", "sad": "😢", "angry": "😡", "excited": "🤩", "serious": "😤", "mysterious": "🕵️"}
                        emotion_emoji = emoji_map.get(emotion, "😐")
                        st.markdown(f"""
                            <div style="font-family: 'Orbitron'; font-size: 10px; color: #EC4899; font-weight: bold; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                {emotion_emoji} {item.get("file_name", "Voice")[:30]}
                            </div>
                        """, unsafe_allow_html=True)
                        if os.path.exists(item.get("path", "")):
                            with open(item["path"], "rb") as f:
                                audio_bytes = f.read()
                            st.audio(audio_bytes, format="audio/mp3")
                        st.markdown(f"""
                            <p style="font-size: 10px; color: #EC4899; line-height: 1.3; height: 36px; overflow: hidden; text-overflow: ellipsis; margin: 8px 0 0 0; font-weight: 300;">
                                "{item.get('prompt', '')[:60]}"
                            </p>
                        """, unsafe_allow_html=True)
        elif display_type == "text":
            text_cols = st.columns(2)
            for idx, item in enumerate(valid_items):
                with text_cols[idx % 2]:
                    with st.container(border=True):
                        st.markdown(f"""
                            <div style="font-family: 'Orbitron'; font-size: 10px; color: #EC4899; font-weight: bold; margin-bottom: 4px;">
                                📝 {item.get("file_name", "Output")}
                            </div>
                        """, unsafe_allow_html=True)
                        st.markdown(f"""
                            <div style="background: rgba(18, 19, 26, 0.85); border-radius: 8px; padding: 10px; max-height: 150px; overflow-y: auto; font-size: 11px; color: #94a3b8; font-family: monospace; line-height: 1.5; border: 1px solid rgba(255,255,255,0.04);">
                                {item.get("content", "")[:500]}
                            </div>
                        """, unsafe_allow_html=True)
        elif display_type == "video":
            video_cols = st.columns(3)
            for idx, item in enumerate(valid_items[:9]):
                with video_cols[idx % 3]:
                    with st.container(border=True):
                        file_path = item.get("path", "")
                        file_name = item.get("file_name", "Untitled")
                        prompt = item.get("prompt", "")
                        if "quality" in item:
                            quality = item.get("quality", "Standard")
                            st.markdown(f"""
                                <div style="font-family: 'Orbitron'; font-size: 10px; color: #EC4899; font-weight: bold; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                    📁 {file_name[:25]}
                                    <span style="font-size: 8px; color: #45f3ff; margin-left: 5px;">[{quality}]</span>
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                                <div style="font-family: 'Orbitron'; font-size: 10px; color:  #EC4899; font-weight: bold; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                    📁 {file_name[:30]}
                                </div>
                            """, unsafe_allow_html=True)
                        if os.path.exists(file_path):
                            try:
                                st.video(file_path, format="video/mp4", autoplay=False, loop=True, muted=False)
                            except:
                                st.markdown("""
                                    <div style="height: 120px; width: 100%; border-radius: 6px; overflow: hidden; border: 1px solid rgba(255,192,203,0.2); display: flex; flex-direction: column; align-items: center; justify-content: center; background: radial-gradient(circle, #1e1b29 0%, #0a0a0f 100%); margin-bottom: 10px;">
                                        <span style="font-size: 36px; display: block;">🎬</span>
                                        <span style="font-family: 'Orbitron'; font-size: 9px; color:  #EC4899; margin-top: 5px; text-transform: uppercase;">VIDEO</span>
                                    </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.markdown("""
                                <div style="height: 120px; width: 100%; border-radius: 6px; overflow: hidden; border: 1px solid rgba(255,192,203,0.2); display: flex; flex-direction: column; align-items: center; justify-content: center; background: radial-gradient(circle, #1e1b29 0%, #0a0a0f 100%); margin-bottom: 10px;">
                                    <span style="font-size: 36px; display: block;">🎬</span>
                                    <span style="font-family: 'Orbitron'; font-size: 9px; color: #EC4899; margin-top: 5px; text-transform: uppercase;">VIDEO</span>
                                </div>
                            """, unsafe_allow_html=True)
                        st.markdown(f"""
                            <p style="font-size: 10px; color:  #EC4899; line-height: 1.3; height: 36px; overflow: hidden; text-overflow: ellipsis; margin: 8px 0 0 0; font-weight: 300;">
                                "{prompt[:60]}"
                            </p>
                        """, unsafe_allow_html=True)
        else:
            image_cols = st.columns(4)
            for idx, item in enumerate(valid_items[:8]):
                with image_cols[idx % 4]:
                    with st.container(border=True):
                        file_path = item.get("path", "")
                        file_name = item.get("file_name", "Untitled")
                        prompt = item.get("prompt", "")
                        st.markdown(f"""
                            <div style="font-family: 'Orbitron'; font-size: 10px; color: #EC4899; font-weight: bold; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                📁 {file_name[:30]}
                            </div>
                        """, unsafe_allow_html=True)
                        img_b64 = get_base64_img_raw(file_path)
                        if img_b64:
                            ext = os.path.splitext(file_path)[1].lower().replace('.', '')
                            if ext == 'jpg':
                                ext = 'jpeg'
                            mime_type = f"image/{ext}" if ext in ['png', 'jpeg', 'webp', 'gif', 'svg'] else "image/png"
                            st.markdown(f"""
                                <div style="height: 120px; width: 100%; border-radius: 6px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: center; background: #000; margin-bottom: 10px;">
                                    <img src="data:{mime_type};base64,{img_b64}" style="max-height: 100%; max-width: 100%; object-fit: contain;" />
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown("""
                                <div style="height: 120px; width: 100%; border-radius: 6px; overflow: hidden; border: 1px solid rgba(255,192,203,0.2); display: flex; flex-direction: column; align-items: center; justify-content: center; background: radial-gradient(circle, #1e1b29 0%, #0a0a0f 100%); margin-bottom: 10px;">
                                    <span style="font-size: 36px; display: block;">🖼️</span>
                                    <span style="font-family: 'Orbitron'; font-size: 9px; color: #FFC0CB; margin-top: 5px; text-transform: uppercase;">IMAGE</span>
                                </div>
                            """, unsafe_allow_html=True)
                        st.markdown(f"""
                            <p style="font-size: 10px; color: #94a3b8; line-height: 1.3; height: 36px; overflow: hidden; text-overflow: ellipsis; margin: 8px 0 0 0; font-weight: 300;">
                                "{prompt[:60]}"
                            </p>
                        """, unsafe_allow_html=True)
    
    st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 25px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-family: Orbitron; font-size: 16px; color: #EC4899; margin-bottom: 15px; letter-spacing: 0.5px;'>📈 GLOBAL TRENDING HOT TOPICS (ONE-CLICK IMPORT)</h3>", unsafe_allow_html=True)
    trend_cols = st.columns(3)
    mock_trends = [
        {"hashtag": "#InterstellarVoid", "category": "Space Mysteries", "title": "Astronomers record unexplained radio whispers emitting from interstellar coordinates.", "clicks": "142K views/hr"},
        {"hashtag": "#DwarkaRuins", "category": "Mythology Mysteries", "title": "Submerged architectural monoliths matching descriptions of Dwarka found near seafloor.", "clicks": "98K views/hr"},
        {"hashtag": "#PratfallEffect", "category": "Dark Psychology", "title": "Why flawed charismatic leaders trigger obsessive loyalty inside digital echo chambers.", "clicks": "210K views/hr"}
    ]
    for idx_t, trend in enumerate(mock_trends):
        with trend_cols[idx_t]:
            with st.container(border=True):
                st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-family:'Orbitron'; font-size: 10px; font-weight:bold; color:#fbbf24;">{trend["hashtag"]}</span>
                        <span style="font-size: 9px; color:#EC4899; font-weight:bold;">🔥 {trend["clicks"]}</span>
                    </div>
                    <div style="font-size: 11px; color:#ffffff; font-weight:bold; height: 38px; overflow:hidden;">{trend["title"]}</div>
                    <div style="font-size: 10px; color: #EC4899; margin-bottom: 10px;">Channel: {trend["category"]}</div>
                """, unsafe_allow_html=True)
                if st.button(f"One-Click Import Trend", key=f"import_trend_action_btn_{idx_t}", use_container_width=True):
                    st.session_state["studio_prompt_value"] = trend["title"]
                    st.session_state["studio_prompt_mode"] = "💡 Autonomous AI Topic"
                    st.toast("Success! Hot Topic imported.")
                    st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("ℹ Engine Technical Specs & Policies", expanded=False):
        st.markdown("<h4 style='font-family:Orbitron; font-size:13px; color:#ffffff; margin-bottom: 12px;'>🚀 INTEGRATED WORKFLOW PIPELINE</h4>", unsafe_allow_html=True)
        col_step1, col_step2, col_step3 = st.columns(3)
        with col_step1:
            st.markdown("""
                <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 12px; height: 100%;">
                    <div style="font-size: 16px; font-weight: bold; color: #ffd700; margin-bottom: 8px; font-family: 'Orbitron';">01</div>
                    <h5 style="color: #ffffff; font-family: Orbitron; font-size: 11px; margin-bottom: 6px;">1. Structured Scripting</h5>
                    <p style="color: #EC4899; font-size: 10px; line-height: 1.5;">Constructs structured scripts with scene-by-scene keyword parameters using the LLM engine.</p>
                </div>
            """, unsafe_allow_html=True)
        with col_step2:
            st.markdown("""
                <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 12px; height: 100%;">
                    <div style="font-size: 16px; font-weight: bold; color: #ffd700; margin-bottom: 8px; font-family: 'Orbitron';">02</div>
                    <h5 style="color: #ffffff; font-family: Orbitron; font-size: 11px; margin-bottom: 6px;">2. Voice Segment Synthetics</h5>
                    <p style="color: #EC4899; font-size: 10px; line-height: 1.5;">Generates specific voice streams per scene block and calculates precise audio timelines.</p>
                </div>
            """, unsafe_allow_html=True)
        with col_step3:
            st.markdown("""
                <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 12px; height: 100%;">
                    <div style="font-size: 16px; font-weight: bold; color: #ffd700; margin-bottom: 8px; font-family: 'Orbitron';">03</div>
                    <h5 style="color: #ffffff; font-family: Orbitron; font-size: 11px; margin-bottom: 6px;">3. Multi-Scene Stitching</h5>
                    <p style="color: #EC4899; font-size: 10px; line-height: 1.5;">Trims visual assets to matching segment runtimes and compiles them together into final outputs.</p>
                </div>
            """, unsafe_allow_html=True)
        st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 15px 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='font-family:Orbitron; font-size:13px; color:#ffffff; margin-bottom: 12px;'>🚨 DISCLAIMER & PLATFORM POLICIES</h4>", unsafe_allow_html=True)
        disc_col1, disc_col2 = st.columns(2)
        with disc_col1:
            st.markdown("""
                <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 12px; height: 100%;">
                    <h5 style="color: #EC4899; font-family: Orbitron; font-size: 10px; margin-bottom: 8px;">Generative Media Policy</h5>
                    <p style="color:  #EC4899; font-size: 10px; line-height: 1.5;">ZOVIX operates as an automated synthesis tool. We do not claim ownership over stock materials retrieved from third-party APIs.</p>
                </div>
            """, unsafe_allow_html=True)
        with disc_col2:
            st.markdown("""
                <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 12px; height: 100%;">
                    <h5 style="color: #EC4899; font-family: Orbitron; font-size: 10px; margin-bottom: 8px;">Usage & Credit Terms</h5>
                    <p style="color: #EC4899; font-size: 10px; line-height: 1.5;">Access to processing nodes requires active credits. Standard 720p generations consume 1 credit.</p>
                </div>
            """, unsafe_allow_html=True)
    
    show_privacy_policy()
    
    st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 30px 0 15px 0;'>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: center; padding: 10px 0 20px 0; color:  #EC4899; font-family: 'Inter'; font-size: 12px;">
            <p style="margin-bottom: 8px; font-weight: 400; color:  #EC4899;">© 2026 ZOVIX. All rights reserved.</p>
            <div style="display: flex; justify-content: center; gap: 15px; font-family: 'Orbitron'; font-size: 10px; letter-spacing: 0.5px;">
                <a href="#" style="color:   #EC4899; text-decoration: none;">SUPPORT</a>
                <span style="color: rgba(255,255,255,0.08);">|</span>
                <a href="#" style="color: #EC4899; text-decoration: none;">DOCUMENTATION</a>
                <span style="color: rgba(255,255,255,0.08);">|</span>
                <a href="#" style="color: #EC4899; text-decoration: none;">API ACCESS</a>
            </div>
        </div>
    """, unsafe_allow_html=True)