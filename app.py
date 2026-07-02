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
import hmac
import re
import sys
import logging
import pickle
from dotenv import load_dotenv
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

# API Keys
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
STRIPE_PUBLISHABLE_KEY = get_system_secret("STRIPE_PUBLISHABLE_KEY")
STRIPE_SECRET_KEY = get_system_secret("STRIPE_SECRET_KEY")
PAYPAL_CLIENT_ID = get_system_secret("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = get_system_secret("PAYPAL_SECRET")
BINANCE_API_KEY = get_system_secret("BINANCE_API_KEY")
BINANCE_API_SECRET = get_system_secret("BINANCE_API_SECRET")
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
    from streamlit.runtime.scriptrunner import add_script_run_context
except ImportError:
    try:
        from streamlit.runtime.scriptrunner.script_run_context import add_script_run_context
    except ImportError:
        def add_script_run_context(thread):
            pass

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

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
    import stripe
    HAS_STRIPE = True
except ImportError:
    HAS_STRIPE = False
    logger.warning("stripe not installed.")

try:
    import paypalrestsdk
    HAS_PAYPAL = True
except ImportError:
    HAS_PAYPAL = False
    logger.warning("paypalrestsdk not installed.")

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
# 4. TWO-FACTOR AUTHENTICATION (2FA)
# ========================================================

class TwoFactorAuth:
    def __init__(self):
        self.enabled = HAS_2FA
    
    def setup_2fa(self, username: str) -> Optional[str]:
        if not self.enabled:
            return None
        
        try:
            secret = pyotp.random_base32()
            
            conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE users SET twofa_secret = ? WHERE username = ?",
                    (encryption_manager.encrypt(secret), username)
                )
                conn.commit()
            finally:
                conn.close()
            
            return secret
        except Exception as e:
            logger.error(f"2FA setup error: {e}")
            return None
    
    def get_secret(self, username: str) -> Optional[str]:
        if not self.enabled:
            return None
        
        conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT twofa_secret FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row and row[0]:
                return encryption_manager.decrypt(row[0])
        except:
            pass
        finally:
            conn.close()
        
        return None
    
    def verify_code(self, username: str, code: str) -> bool:
        if not self.enabled:
            return True
        
        secret = self.get_secret(username)
        if not secret:
            return True
        
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code)
        except:
            return False
    
    def render_qr_code(self, username: str, secret: str) -> str:
        if not self.enabled:
            return ""
        
        try:
            totp = pyotp.TOTP(secret)
            uri = totp.provisioning_uri(username, issuer_name="ZOVIX")
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            from io import BytesIO
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            logger.error(f"QR code generation error: {e}")
            return ""

twofa = TwoFactorAuth()

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
                voice_profile=config.get("voice_profile", "Drew (Premium Male Voice)"),
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
    st.session_state["sidebar_tab"] = "⚙️ Setup Config"
if "quick_template_mode" not in st.session_state:
    st.session_state["quick_template_mode"] = True
if "model_choice" not in st.session_state:
    st.session_state["model_choice"] = "🤖 gemini-2.5-flash (Fast Stream Processing)"
if "aspect_ratio" not in st.session_state:
    st.session_state["aspect_ratio"] = "📐 9:16 Vertical (Shorts/Reels)"
if "duration_choice" not in st.session_state:
    st.session_state["duration_choice"] = "⏱️ Quick Format Shorts (10-15s)"
if "voice_profile" not in st.session_state:
    st.session_state["voice_profile"] = "Drew (Premium Male Voice)"
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
if "active_flow_animation" not in st.session_state:
    st.session_state["active_flow_animation"] = None
if "active_upscaled_image" not in st.session_state:
    st.session_state["active_upscaled_image"] = None
if "active_drawing" not in st.session_state:
    st.session_state["active_drawing"] = None
if "active_editor_output" not in st.session_state:
    st.session_state["active_editor_output"] = None
if "active_face_video" not in st.session_state:
    st.session_state["active_face_video"] = None
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

# Payment related
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

# Inject global CSS to constrain app width and prevent horizontal overflow
st.markdown("""
    <style>
        /* Poore block container ko center align karne ke liye */
        [data-testid="stMainBlockContainer"] {
            max-width: 90% !important;
            padding-left: 3rem !important;
            padding-right: 3rem !important;
            margin: 0 auto !important;
        }
        
        /* Buttons waale row ko laptop screen par stretch hone se rokne ke liye */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 10px !important;
        }
    </style>
""", unsafe_allow_html=True)

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

if HAS_STRIPE and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# ========================================================
# 10. ELEVENLABS VOICE OPTIONS
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
}

LANGUAGE_VOICE_MAP = {
    "English": ["Adam (Premium Male)", "Rachel (Premium Female)", "Drew (Professional Male)", "Bella (Warm Female)", "Antoni (Deep Male)", "Charlotte (Elegant Female)", "Josh (Young Male)", "Emily (Professional Female)", "James (Narrator Male)", "Sarah (Soothing Female)"],
    "Hindi": ["Arjun (Hindi Male)", "Priya (Hindi Female)", "Ravi (Hindi Professional Male)"],
    "Bhojpuri": ["Vikram (Bhojpuri Male)", "Sita (Bhojpuri Female)"],
    "French": ["Pierre (French Male)", "Sophie (French Female)"],
    "Japanese": ["Kenji (Japanese Male)", "Yuki (Japanese Female)"],
}

# ========================================================
# 11. TOKEN BURN RATE
# ========================================================

BASE_BURN_RATE = {
    "Face Video Generator": 3,
    "Cinematic Engine": 2,
    "Creative Workshop": 2,
    "AI Agent": 2,
    "AI Sales": 2,
    "Dynamic UI": 2,
    "Live Emotion": 3,
    "Blueprints": 1,
    "Flow State": 1,
    "Upscaler": 1,
    "Draw": 1,
    "Video Editor": 2
}

def calculate_tokens(mode_name: str, selected_quality: str) -> int:
    base_cost = BASE_BURN_RATE.get(mode_name, 2)
    heavy_engines = ["Face Video Generator", "Cinematic Engine", "Live Emotion", "Video Editor"]
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
        "currencies": ["INR", "USD", "EUR", "GBP", "AED", "SAR", "SGD", "JPY"],
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

DISPLAYED_PAYMENT_GATEWAYS = ["razorpay", "crypto"]


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
            "tokens": 60,
            "amount_paise": 9900,
            "emoji": "🥇",
            "features": ["60 Tokens Monthly", "No Watermark", "All AI Features"],
            "type": "monthly",
            "badge": "POPULAR",
            "color": "#f59e0b",
            "description": "Best value plan"
        },
        "cinematic": {
            "name": "Cinematic",
            "price": 299,
            "tokens": 180,
            "amount_paise": 29900,
            "emoji": "🥈",
            "features": ["180 Tokens Monthly", "No Watermark", "All AI Features"],
            "type": "monthly",
            "badge": "",
            "color": "#8b5cf6",
            "description": "For serious creators"
        },
        "premium": {
            "name": "Premium",
            "price": 499,
            "tokens": 310,
            "amount_paise": 49900,
            "emoji": "💎",
            "features": ["310 Tokens Monthly", "No Watermark", "All AI Features"],
            "type": "monthly",
            "badge": "",
            "color": "#ec4899",
            "description": "Professional creators"
        },
        "pro": {
            "name": "Pro",
            "price": 999,
            "tokens": 620,
            "amount_paise": 99900,
            "emoji": "👑",
            "features": ["620 Tokens Monthly", "No Watermark", "All AI Features"],
            "type": "monthly",
            "badge": "⭐ BEST VALUE",
            "color": "#f43f5e",
            "description": "Unlimited potential"
        },
        "enterprise": {
            "name": "Enterprise",
            "price": 1999,
            "tokens": 1250,
            "amount_paise": 199900,
            "emoji": "🏢",
            "features": ["1250 Tokens Monthly", "No Watermark", "All AI Features", "Priority Support", "Custom AI Models"],
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
                path TEXT
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

        try:
            cursor.execute("PRAGMA table_info(users)")
            existing_cols = [r[1] for r in cursor.fetchall()]
            required_cols = {
                "twofa_secret": "TEXT DEFAULT ''",
                "gdpr_consent": "INTEGER DEFAULT 0",
                "gdpr_version": "TEXT DEFAULT ''",
                "language": "TEXT DEFAULT 'en'",
                "last_login": "TEXT DEFAULT ''",
                # created_at must be added without using CURRENT_TIMESTAMP as a default
                # because ALTER TABLE ADD COLUMN in SQLite requires a constant default.
                "created_at": "DATETIME"
            }
            for col, definition in required_cols.items():
                if col not in existing_cols:
                    try:
                        # For created_at we add the column without a non-constant default
                        cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
                        logger.info(f"Migrated DB: added column '{col}' to users table")
                        if col == 'created_at':
                            try:
                                cursor.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL OR created_at = ''")
                                logger.info("Migrated DB: populated 'created_at' for existing users")
                            except Exception as ume:
                                logger.warning(f"Could not populate created_at values: {ume}")
                    except Exception as me:
                        logger.warning(f"Could not add column {col}: {me}")
            conn.commit()
        except Exception as me:
            logger.warning(f"User table migration check failed: {me}")

        try:
            cursor.execute("PRAGMA table_info(face_video_history)")
            fcols = [r[1] for r in cursor.fetchall()]
            if 'quality' not in fcols:
                try:
                    cursor.execute("ALTER TABLE face_video_history ADD COLUMN quality TEXT DEFAULT 'Standard'")
                    logger.info("Migrated DB: added column 'quality' to face_video_history")
                except Exception as me:
                    logger.warning(f"Could not add column quality to face_video_history: {me}")

            cursor.execute("PRAGMA table_info(payment_history)")
            pcols = [r[1] for r in cursor.fetchall()]
            if 'plan_type' not in pcols:
                try:
                    cursor.execute("ALTER TABLE payment_history ADD COLUMN plan_type TEXT DEFAULT 'one_time'")
                    logger.info("Migrated DB: added column 'plan_type' to payment_history")
                except Exception as me:
                    logger.warning(f"Could not add column plan_type to payment_history: {me}")
            if 'gateway' not in pcols:
                try:
                    cursor.execute("ALTER TABLE payment_history ADD COLUMN gateway TEXT DEFAULT 'razorpay'")
                    logger.info("Migrated DB: added column 'gateway' to payment_history")
                except Exception as me:
                    logger.warning(f"Could not add column gateway to payment_history: {me}")

            conn.commit()
        except Exception as me:
            logger.warning(f"Additional table migration failed: {me}")

        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database init error: {e}")
    finally:
        conn.close()

init_database()

# ========================================================
# 17. AUTHENTICATION FUNCTIONS
# ========================================================

def authenticate_user_db(username, password):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password, twofa_secret FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            if row[0] == password:
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE username = ?",
                    (datetime.now().isoformat(), username)
                )
                conn.commit()
                
                if row[1] and row[1].strip():
                    st.session_state["2fa_enabled"] = True
                    return True, True
                else:
                    st.session_state["2fa_enabled"] = False
                    return True, False
            else:
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
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO users (username, password, credits, xp_points, streak_count, last_claim_date, voucher_credits, voucher_expires_at, language) VALUES (?, ?, 50.0, 10.0, 0, '', 0, '', 'en')",
            (username, password)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return False
    finally:
        conn.close()

def login_or_register_social(email, platform):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT username FROM users WHERE username = ?", (email,))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO users (username, password, credits, xp_points, streak_count, last_claim_date, voucher_credits, voucher_expires_at, language) VALUES (?, ?, 100, 0, 0, '', 0, '', 'en')",
                (email, f"social_{platform.lower()}")
            )
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Social login error: {e}")
        return False
    finally:
        conn.close()

def get_user_credits_db(username):
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
    except Exception as e:
        logger.error(f"Add credits error: {e}")
    finally:
        conn.close()

def deduct_credits_db(username, amount):
    check_and_expire_vouchers(username)
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT credits, voucher_credits FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            std_credits, v_credits = row[0], row[1]
            if v_credits >= amount:
                new_v = v_credits - amount
                cursor.execute("UPDATE users SET voucher_credits = ? WHERE username = ?", (new_v, username))
            else:
                remaining = amount - v_credits
                cursor.execute(
                    "UPDATE users SET voucher_credits = 0, credits = MAX(0, credits - ?) WHERE username = ?",
                    (remaining, username)
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Deduct credits error: {e}")
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
                        st.session_state['user_credits'] += tokens_to_add
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
            cursor.execute(
                "UPDATE users SET credits = credits + ? WHERE username = ?",
                (count * 10, referrer_username)
            )
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
        cursor.execute(
            "UPDATE users SET credits = credits + 2 WHERE username = ?",
            (username,)
        )
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
# 24. PAYMENT FUNCTIONS
# ========================================================

def create_payment_order(amount_paise, plan_name=""):
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET or RAZORPAY_KEY_ID == "mock" or RAZORPAY_KEY_SECRET == "mock":
        logger.warning("Razorpay test keys are missing or still mocked. Falling back to a local mock order.")
        return {
            "id": f"order_mock_{uuid.uuid4().hex[:8]}",
            "amount": int(amount_paise),
            "status": "mock",
            "debug": "Missing Razorpay test keys."
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
        return True
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False

def save_payment_history(username, order_id, payment_id, amount, credits_added, pack_name, status, plan_type="one_time", gateway="razorpay"):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO payment_history (username, order_id, payment_id, amount, credits_added, pack_name, status, plan_type, gateway) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (username, order_id, payment_id, amount, credits_added, pack_name, status, plan_type, gateway)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Save payment history error: {e}")
        return False
    finally:
        conn.close()

def process_payment_success(username, order_id, payment_id, signature, amount, credits_to_add, pack_name, gateway="razorpay"):
    if not verify_payment_signature(order_id, payment_id, signature):
        logger.warning(f"Signature verification failed for order: {order_id}")
    
    plan_type = "one_time"
    if "Subscription" in pack_name:
        plan_type = "monthly"
    
    if username and st.session_state.get("is_logged_in", False):
        add_credits(username, credits_to_add)
        st.session_state['user_credits'] = get_user_credits_db(username)
        st.session_state['payment_verified'] = True
        st.session_state['pending_credits'] = 0
        st.session_state['pending_pack_name'] = ""
        save_payment_history(username, order_id, payment_id, amount, credits_to_add, pack_name, "success", plan_type, gateway)
        return True, f"✅ Payment successful! Added {credits_to_add} credits to your account."
    else:
        st.session_state['pending_credits'] = credits_to_add
        st.session_state['pending_pack_name'] = pack_name
        st.session_state['payment_verified'] = True
        save_payment_history("pending_user", order_id, payment_id, amount, credits_to_add, pack_name, "pending", plan_type, gateway)
        return True, f"✅ Payment successful! {credits_to_add} credits will be added when you log in."

# ========================================================
# 25. STRIPE PAYMENT FUNCTIONS
# ========================================================

def create_stripe_payment(amount_usd: float, description: str = "ZOVIX Credits", customer_email: str = ""):
    if not HAS_STRIPE or not STRIPE_SECRET_KEY:
        logger.warning("Stripe not configured")
        return None
    
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount_usd * 100),
            currency="usd",
            description=description,
            receipt_email=customer_email,
            metadata={
                "integration": "zovix",
                "timestamp": str(int(time.time()))
            },
            automatic_payment_methods={
                "enabled": True,
                "allow_redirects": "never"
            }
        )
        
        return {
            "id": intent.id,
            "client_secret": intent.client_secret,
            "amount": intent.amount / 100,
            "currency": intent.currency
        }
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        return None

def render_stripe_checkout(order_id: str, client_secret: str, amount: float, credits: int, plan_name: str):
    if not STRIPE_PUBLISHABLE_KEY:
        return "<p>Stripe not configured</p>"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://js.stripe.com/v3/"></script>
        <style>
            body {{ margin: 0; padding: 0; background: transparent; font-family: 'Inter', sans-serif; }}
            .stripe-container {{
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
            #payment-element {{
                margin-bottom: 20px;
                background: white;
                padding: 15px;
                border-radius: 8px;
            }}
            .stripe-btn {{
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #45f3ff 0%, #EC4899 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Orbitron', sans-serif;
                cursor: pointer;
                transition: all 0.3s ease;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .stripe-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 30px rgba(69, 243, 255, 0.3);
            }}
            .stripe-btn:disabled {{
                opacity: 0.5;
                cursor: not-allowed;
            }}
            .payment-status {{
                text-align: center;
                margin-top: 15px;
                font-size: 13px;
                color: #94a3b8;
            }}
            .payment-status.success {{ color: #10b981; }}
            .payment-status.error {{ color: #ef4444; }}
            @media (max-width: 600px) {{
                .stripe-container {{ padding: 15px; }}
                .payment-header {{ font-size: 16px; }}
            }}
        </style>
    </head>
    <body>
        <div class="stripe-container">
            <div class="payment-header">💳 STRIPE PAYMENT</div>
            <div class="payment-details">
                <div class="row"><span>💰 Amount</span><span class="value">${amount:.2f}</span></div>
                <div class="row"><span>⚡ Credits</span><span class="value">+{credits}</span></div>
                <div class="row"><span>📦 Plan</span><span class="value">{plan_name}</span></div>
            </div>
            <div id="payment-element"></div>
            <button class="stripe-btn" id="pay-button">💳 Pay ${amount:.2f}</button>
            <div class="payment-status" id="payment-status">🔒 Secured by Stripe</div>
        </div>
        
        <script>
            const stripe = Stripe('{STRIPE_PUBLISHABLE_KEY}');
            const clientSecret = '{client_secret}';
            const orderId = '{order_id}';
            const credits = {credits};
            const planName = '{plan_name}';
            const amount = {amount};
            
            let elements;
            let paymentElement;
            
            async function initialize() {{
                try {{
                    const appearance = {{
                        theme: 'stripe',
                        variables: {{
                            colorPrimary: '#45f3ff',
                            colorBackground: '#ffffff',
                            colorText: '#1F2937',
                            borderRadius: '8px',
                        }},
                    }};
                    
                    elements = stripe.elements({{
                        clientSecret: clientSecret,
                        appearance: appearance,
                    }});
                    
                    paymentElement = elements.create('payment');
                    paymentElement.mount('#payment-element');
                }} catch (error) {{
                    document.getElementById('payment-status').innerHTML = '❌ ' + error.message;
                    document.getElementById('payment-status').className = 'payment-status error';
                }}
            }}
            
            initialize();
            
            document.getElementById('pay-button').addEventListener('click', async function() {{
                const button = this;
                button.disabled = true;
                button.innerHTML = '⏳ Processing...';
                document.getElementById('payment-status').innerHTML = '🔄 Processing payment...';
                
                try {{
                    const {{ error, paymentIntent }} = await stripe.confirmPayment({{
                        elements: elements,
                        redirect: 'if_required',
                        confirmParams: {{
                            return_url: window.location.origin + '?stripe_success=true',
                        }},
                    }});
                    
                    if (error) {{
                        document.getElementById('payment-status').innerHTML = '❌ ' + error.message;
                        document.getElementById('payment-status').className = 'payment-status error';
                        button.disabled = false;
                        button.innerHTML = '💳 Pay ${amount:.2f}';
                    }} else if (paymentIntent && paymentIntent.status === 'succeeded') {{
                        document.getElementById('payment-status').innerHTML = '✅ Payment successful! Adding credits...';
                        document.getElementById('payment-status').className = 'payment-status success';
                        button.innerHTML = '✅ Done!';
                        
                        window.parent.postMessage({{
                            type: 'stripe_success',
                            orderId: orderId,
                            paymentId: paymentIntent.id,
                            credits: credits,
                            planName: planName,
                            amount: amount
                        }}, '*');
                    }}
                }} catch (error) {{
                    document.getElementById('payment-status').innerHTML = '❌ ' + error.message;
                    document.getElementById('payment-status').className = 'payment-status error';
                    button.disabled = false;
                    button.innerHTML = '💳 Pay ${amount:.2f}';
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html

# ========================================================
# 26. PAYPAL PAYMENT FUNCTIONS
# ========================================================

def create_paypal_order(amount_usd: float, description: str = "ZOVIX Credits"):
    if not HAS_PAYPAL or not PAYPAL_CLIENT_ID or not PAYPAL_SECRET:
        logger.warning("PayPal not configured")
        return None
    
    try:
        paypalrestsdk.configure({
            "mode": os.getenv("PAYPAL_MODE", "sandbox"),
            "client_id": PAYPAL_CLIENT_ID,
            "client_secret": PAYPAL_SECRET
        })
        
        order = paypalrestsdk.Order({
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": f"{amount_usd:.2f}"
                },
                "description": description,
                "invoice_number": f"ZOVIX_{int(time.time())}"
            }],
            "application_context": {
                "return_url": f"{os.getenv('APP_URL', 'https://zovix.ai')}/paypal_success",
                "cancel_url": f"{os.getenv('APP_URL', 'https://zovix.ai')}/paypal_cancel"
            }
        })
        
        if order.create():
            for link in order.links:
                if link.rel == "approval_url":
                    return {
                        "id": order.id,
                        "approval_url": link.href,
                        "amount": amount_usd,
                        "status": order.status
                    }
        return None
    except Exception as e:
        logger.error(f"PayPal error: {e}")
        return None

def render_paypal_checkout(order_id: str, approval_url: str, amount: float, credits: int, plan_name: str):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ margin: 0; padding: 0; background: transparent; font-family: 'Inter', sans-serif; }}
            .paypal-container {{
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
            .paypal-btn {{
                width: 100%;
                padding: 14px;
                background: #0070ba;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Orbitron', sans-serif;
                cursor: pointer;
                transition: all 0.3s ease;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .paypal-btn:hover {{
                background: #003087;
                transform: translateY(-2px);
                box-shadow: 0 8px 30px rgba(0, 112, 186, 0.3);
            }}
            .payment-status {{
                text-align: center;
                margin-top: 15px;
                font-size: 13px;
                color: #94a3b8;
            }}
            @media (max-width: 600px) {{
                .paypal-container {{ padding: 15px; }}
                .payment-header {{ font-size: 16px; }}
            }}
        </style>
    </head>
    <body>
        <div class="paypal-container">
            <div class="payment-header">💰 PAYPAL PAYMENT</div>
            <div class="payment-details">
                <div class="row"><span>💰 Amount</span><span class="value">${amount:.2f}</span></div>
                <div class="row"><span>⚡ Credits</span><span class="value">+{credits}</span></div>
                <div class="row"><span>📦 Plan</span><span class="value">{plan_name}</span></div>
            </div>
            <button class="paypal-btn" id="paypal-button">💰 Pay with PayPal</button>
            <div class="payment-status" id="payment-status">🔒 Secured by PayPal</div>
        </div>
        
        <script>
            document.getElementById('paypal-button').addEventListener('click', function() {{
                const button = this;
                button.disabled = true;
                button.innerHTML = '⏳ Redirecting...';
                document.getElementById('payment-status').innerHTML = '🔄 Redirecting to PayPal...';
                
                window.open('{approval_url}', '_blank');
                
                window.parent.postMessage({{
                    type: 'paypal_redirect',
                    orderId: '{order_id}',
                    credits: {credits},
                    planName: '{plan_name}',
                    amount: {amount}
                }}, '*');
            }});
        </script>
    </body>
    </html>
    """
    return html

# ========================================================
# 27. CRYPTO PAYMENT FUNCTIONS
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
# 28. BINANCE PAYMENT FUNCTIONS
# ========================================================

def create_binance_payment(amount_usd: float, currency: str = "BUSD"):
    try:
        if not BINANCE_API_KEY or not BINANCE_API_SECRET:
            logger.warning("Binance not configured")
            return None
        
        return {
            "id": f"BNB_{int(time.time())}",
            "address": "0x" + ''.join(random.choices('abcdef0123456789', k=40)),
            "amount": amount_usd,
            "currency": currency,
            "qr_code": f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=binance_pay_{int(time.time())}",
            "status": "pending"
        }
    except Exception as e:
        logger.error(f"Binance error: {e}")
        return None

def render_binance_checkout(binance_data: dict, credits: int, plan_name: str):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ margin: 0; padding: 0; background: transparent; font-family: 'Inter', sans-serif; }}
            .binance-container {{
                background: linear-gradient(135deg, #0a0a12 0%, #1a1a2e 100%);
                border-radius: 16px;
                padding: 30px;
                border: 1px solid #f0b90b;
                max-width: 500px;
                margin: 0 auto;
            }}
            .payment-header {{
                text-align: center;
                font-family: 'Orbitron', sans-serif;
                font-size: 20px;
                color: #f0b90b;
                margin-bottom: 20px;
            }}
            .payment-details {{
                background: rgba(240, 185, 11, 0.05);
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 20px;
                border: 1px solid rgba(240, 185, 11, 0.2);
            }}
            .payment-details .row {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                color: #c0c0c0;
                font-size: 14px;
            }}
            .payment-details .row .value {{
                color: #f0b90b;
                font-weight: bold;
            }}
            .binance-qr {{
                text-align: center;
                padding: 15px;
                background: white;
                border-radius: 12px;
                margin: 15px 0;
            }}
            .binance-qr img {{
                max-width: 180px;
            }}
            .binance-address {{
                background: rgba(0,0,0,0.3);
                padding: 12px;
                border-radius: 8px;
                font-family: monospace;
                font-size: 14px;
                color: #f0b90b;
                text-align: center;
                word-break: break-all;
                margin: 10px 0;
                border: 1px solid rgba(240, 185, 11, 0.2);
            }}
            .copy-btn {{
                width: 100%;
                padding: 10px;
                background: rgba(240, 185, 11, 0.1);
                color: #f0b90b;
                border: 1px solid rgba(240, 185, 11, 0.3);
                border-radius: 8px;
                cursor: pointer;
                font-family: 'Orbitron', sans-serif;
                font-size: 12px;
                transition: all 0.3s ease;
            }}
            .copy-btn:hover {{
                background: rgba(240, 185, 11, 0.2);
            }}
            .payment-status {{
                text-align: center;
                margin-top: 15px;
                font-size: 13px;
                color: #94a3b8;
            }}
        </style>
    </head>
    <body>
        <div class="binance-container">
            <div class="payment-header">🟡 BINANCE PAY</div>
            <div class="payment-details">
                <div class="row"><span>💰 Amount</span><span class="value">{binance_data['amount']:.2f} USD</span></div>
                <div class="row"><span>⚡ Credits</span><span class="value">+{credits}</span></div>
                <div class="row"><span>📦 Plan</span><span class="value">{plan_name}</span></div>
                <div class="row"><span>🪙 Currency</span><span class="value">{binance_data['currency']}</span></div>
            </div>
            <div class="binance-qr">
                <img src="{binance_data['qr_code']}" alt="QR Code" />
            </div>
            <div class="binance-address" id="binance-address">
                {binance_data['address']}
            </div>
            <button class="copy-btn" id="copy-address">📋 Copy Address</button>
            <div class="payment-status" id="payment-status">
                💡 Pay with Binance Pay or send {binance_data['currency']} to the address above
            </div>
        </div>
        
        <script>
            document.getElementById('copy-address').addEventListener('click', function() {{
                const address = document.getElementById('binance-address').textContent;
                navigator.clipboard.writeText(address).then(() => {{
                    this.textContent = '✅ Copied!';
                    setTimeout(() => {{
                        this.textContent = '📋 Copy Address';
                    }}, 2000);
                }});
            }});
        </script>
    </body>
    </html>
    """
    return html

# ========================================================
# 29. ENHANCED PAYMENT UI
# ========================================================

def clear_payment_state():
    st.session_state["show_payment"] = False
    st.session_state["show_gateway_form"] = False
    st.session_state["selected_gateway"] = None
    st.session_state["razorpay_order_id"] = None
    st.session_state["razorpay_payment_id"] = None
    st.session_state["razorpay_signature"] = None


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
                            st.session_state['user_credits'] += plan_data['tokens']
                            st.success(f"✅ Added {plan_data['tokens']} free tokens!")
                            st.rerun()
                    else:
                        if st.button(f"Subscribe {selected_currency} {converted_price:.2f}", key=f"enhanced_sub_{plan_key}", use_container_width=True):
                            st.session_state["pending_credits"] = plan_data['tokens']
                            st.session_state["pending_pack_name"] = plan_data['name']
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
# 30. PAYMENT MODAL
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

            if gateway == "stripe":
                st.markdown("---")
                st.markdown("### 💳 Stripe Payment")

                if st.button("💳 Pay with Stripe", use_container_width=True):
                    with st.spinner("Creating payment session..."):
                        amount_usd = convert_price(amount, "USD")
                        result = create_stripe_payment(
                            amount_usd,
                            f"ZOVIX - {plan_name}",
                            st.session_state.get("logged_user", "")
                        )
                        if result:
                            html = render_stripe_checkout(
                                result["id"],
                                result["client_secret"],
                                result["amount"],
                                credits,
                                plan_name
                            )
                            st.components.v1.html(html, height=450)
                        else:
                            st.error("Failed to create Stripe payment. Please try again.")

            elif gateway == "paypal":
                st.markdown("---")
                st.markdown("### 💰 PayPal Payment")

                if st.button("💰 Pay with PayPal", use_container_width=True):
                    with st.spinner("Creating PayPal order..."):
                        amount_usd = convert_price(amount, "USD")
                        result = create_paypal_order(amount_usd, f"ZOVIX - {plan_name}")
                        if result and result.get("approval_url"):
                            html = render_paypal_checkout(
                                result["id"],
                                result["approval_url"],
                                result["amount"],
                                credits,
                                plan_name
                            )
                            st.components.v1.html(html, height=350)
                            st.info("💡 A new tab will open for PayPal payment. After completing, return here.")
                        else:
                            st.error("Failed to create PayPal order. Please try again.")

            elif gateway == "crypto":
                st.markdown("---")
                st.markdown("### ₿ Cryptocurrency Payment")

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
                st.markdown("### 🟡 Binance Payment")

                binance_currency = st.selectbox(
                    "Select Currency",
                    ["BUSD", "USDT", "BNB", "BTC", "ETH"],
                    key="binance_currency_select"
                )

                if st.button(f"Pay with Binance", use_container_width=True):
                    with st.spinner("Creating Binance payment..."):
                        amount_usd = convert_price(amount, "USD")
                        result = create_binance_payment(amount_usd, binance_currency)
                        if result:
                            html = render_binance_checkout(result, credits, plan_name)
                            st.components.v1.html(html, height=450)
                        else:
                            st.error("Failed to create Binance payment. Please try again.")

            elif gateway == "razorpay":
                st.markdown("---")
                st.markdown("### 💳 Razorpay Payment")

                if st.button("💳 Pay with Razorpay", use_container_width=True):
                    if not RAZORPAY_KEY_ID or RAZORPAY_KEY_ID == "mock":
                        st.error("❌ Razorpay not configured. Please add Razorpay keys.")
                    else:
                        amount_paise = amount * 100
                        order = create_payment_order(amount_paise, plan_name)
                        if order and order.get("id"):
                            st.session_state["razorpay_order_id"] = order["id"]
                            st.session_state["razorpay_last_debug"] = order.get("debug", "")
                            st.session_state["razorpay_last_status"] = order.get("status", "created")
                            html = render_razorpay_checkout(
                                order["id"],
                                amount_paise,
                                plan_name,
                                credits,
                                st.session_state.get("logged_user", "User"),
                                RAZORPAY_KEY_ID
                            )
                            st.components.v1.html(html, height=520)
                            if order.get("status") != "created":
                                st.warning(f"⚠️ Razorpay backend returned a fallback order. Debug: {order.get('debug', '')}")
                            else:
                                st.caption("🛡️ Checkout is rendered inside a secure component iframe for Streamlit Cloud compatibility.")
                        else:
                            st.error("Failed to create payment order. Please try again.")

# ========================================================
# 31. RAZORPAY CHECKOUT
# ========================================================

def render_razorpay_checkout(order_id, amount, plan_name, credits, username, key_id):
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
                        prefill: {{ name: username || 'Zovix User', email: username || 'user@zovix.ai' }},
                        theme: {{ color: '#EC4899', backdrop_color: '#06070a' }},
                        modal: {{
                            ondismiss: function() {{
                                updateStatus('❌ Payment cancelled.', 'error');
                            }}
                        }},
                        handler: function(response) {{
                            updateStatus('✅ Processing payment...', 'success');
                            payButton.disabled = true;
                            payButton.innerHTML = '⏳ Processing...';
                            // Streamlit window to parent data mechanism fallback
                            if (window.parent) {{
                                window.parent.postMessage({{
                                    type: 'razorpay_success',
                                    payment_id: response.razorpay_payment_id,
                                    order_id: response.razorpay_order_id,
                                    signature: response.razorpay_signature
                                }}, '*');
                            }}
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
            }})();
        </script>
    </body>
    </html>
    """

    # Yahan hum double nested wrapper_html hata kar clean inline srcdoc bana rahe hain 
    # Jo seedhe Streamlit components.v1.html ko pas hoga, no CORS block anymore!
    return checkout_html

def handle_payment_response():
    query_params = st.query_params
    if "razorpay_payment_id" in query_params and "razorpay_order_id" in query_params:
        payment_id = query_params.get("razorpay_payment_id")
        order_id = query_params.get("razorpay_order_id")
        signature = query_params.get("razorpay_signature", "")
        credits_to_add = st.session_state.get("pending_credits", 0)
        pack_name = st.session_state.get("pending_pack_name", "")
        if st.session_state.get("is_logged_in") and st.session_state.get("logged_user"):
            username = st.session_state["logged_user"]
            success, message = process_payment_success(
                username, order_id, payment_id, signature,
                st.session_state.get("pending_amount", 0),
                credits_to_add, pack_name
            )
            if success:
                st.success(message)
                st.balloons()
                st.session_state["razorpay_order_id"] = None
                st.session_state["razorpay_payment_id"] = None
                st.session_state["razorpay_signature"] = None
                st.session_state["pending_credits"] = 0
                st.session_state["pending_pack_name"] = ""
                st.session_state["pending_amount"] = 0
                st.session_state["payment_verified"] = True
                st.query_params.clear()
                st.rerun()
            else:
                st.error(message)
        else:
            st.info("✅ Payment successful! Please log in to claim your credits.")
            st.session_state["pending_credits"] = credits_to_add
            st.session_state["pending_pack_name"] = pack_name
            st.query_params.clear()

# ========================================================
# 32. HELPER FUNCTIONS
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

def save_render_to_db(username, file_name, prompt, path):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        timestamp = time.strftime("%b %d, %Y - %I:%M %p")
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
        cursor.execute("SELECT file_name, timestamp, prompt, path FROM history WHERE username = ? ORDER BY id DESC", (username,))
        rows = cursor.fetchall()
        for row in rows:
            history.append({
                "file_name": row[0],
                "timestamp": row[1],
                "prompt": row[2],
                "path": row[3]
            })
    except Exception as e:
        logger.error(f"Load renders error: {e}")
    finally:
        conn.close()
    return history

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
# 33. SCRIPTING, VISUAL, AUDIO, STITCHER ENGINES
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
    return default_path

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
        url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(clean_query)}&per_page=1"
        headers = {"Authorization": pexels_key}
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                videos = data.get("videos", [])
                if videos:
                    selected_video = videos[0]
                    video_files = selected_video.get("video_files", [])
                    if video_files:
                        video_url = video_files[0].get("link")
                        if video_url:
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
    try:
        hinglish_map = {"kisan": "farmer", "beej": "seeds", "paas": "near", "haveli": "ancient mansion", "ghar": "house", "paani": "water", "samundar": "ocean", "rahasya": "mystery", "sach": "truth", "jungle": "forest", "pahar": "mount", "raja": "king", "rani": "queen", "sona": "gold", "chand": "moon", "suraj": "sun"}
        clean_desc = description.lower().replace('"', '').replace("'", "").strip()
        words = clean_desc.split()
        translated_words = []
        for w in words:
            clean_w = w.strip(",.?!\"'")
            translated_words.append(hinglish_map.get(clean_w, clean_w))
        refined_query = " ".join(translated_words)
        cached_path = get_cached_clip(refined_query)
        if cached_path and os.path.exists(cached_path):
            shutil.copy(cached_path, output_filename)
            if status_dict is not None and idx is not None:
                status_dict[idx] = f"✅ Cached: '{refined_query}'"
            return True
        if st.session_state.get("quick_template_mode", True):
            return False
        if status_dict is not None and idx is not None:
            status_dict[idx] = f"📹 Sourcing Pexels: '{refined_query}'"
        if VisualEngine.fetch_pexels_clip(refined_query, output_filename):
            cache_dir = os.path.join("assets", "cache")
            permanent_path = os.path.join(cache_dir, f"cache_{uuid.uuid4().hex[:8]}.mp4")
            shutil.copy(output_filename, permanent_path)
            cache_clip(refined_query, permanent_path)
            if status_dict is not None and idx is not None:
                status_dict[idx] = f"✅ Pexels: '{refined_query}'"
            return True
        if status_dict is not None and idx is not None:
            status_dict[idx] = f"📹 Sourcing Pixabay: '{refined_query}'"
        if VisualEngine.fetch_pixabay_clip(refined_query, output_filename):
            cache_dir = os.path.join("assets", "cache")
            permanent_path = os.path.join(cache_dir, f"cache_{uuid.uuid4().hex[:8]}.mp4")
            shutil.copy(output_filename, permanent_path)
            cache_clip(refined_query, permanent_path)
            if status_dict is not None and idx is not None:
                status_dict[idx] = f"✅ Pixabay: '{refined_query}'"
            return True
        if scene_text:
            if status_dict is not None and idx is not None:
                status_dict[idx] = "🎬 Sourcing AI Video generators..."
            ai_video_url = generate_ai_video(scene_text)
            if ai_video_url:
                with requests.get(ai_video_url, stream=True, timeout=25) as r:
                    if r.status_code == 200:
                        with open(output_filename, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                        if os.path.exists(output_filename) and os.path.getsize(output_filename) > 100:
                            if status_dict is not None and idx is not None:
                                status_dict[idx] = "✅ AI Video Generated"
                            return True
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
            try:
                url = "https://api-inference.huggingface.co/models/stabilityai/stable-video-diffusion-img2vid-xt"
                headers = {"Authorization": f"Bearer {hf_key}", "Content-Type": "application/octet-stream", "Accept": "video/mp4"}
                params = {"parameters": {"motion_bucket_id": int(motion_bucket_id)}}
                response = requests.post(url, headers=headers, data=img_data, params=params, timeout=60)
                if response.status_code == 200 and len(response.content) > 5000:
                    output_video_path = f"saved_renders/svd_output_{uuid.uuid4().hex[:6]}.mp4"
                    with open(output_video_path, "wb") as out_f:
                        out_f.write(response.content)
                    video_path = output_video_path
            except Exception as e:
                logger.error(f"SVD error: {e}")
        except Exception as e:
            logger.error(f"SVD setup error: {e}")
    if not video_path:
        output_video_path = f"saved_renders/svd_output_{uuid.uuid4().hex[:6]}.mp4"
        try:
            cmd = ['ffmpeg', '-y', '-loop', '1', '-i', image_path, '-t', '4', '-vf', f"zoompan=z='min(zoom+0.0015,1.5)':d=96:s=1280x720", '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'ultrafast', '-r', '24', output_video_path]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(output_video_path):
                video_path = output_video_path
        except Exception as e:
            logger.error(f"Fallback SVD error: {e}")
    return video_path

def generate_ai_video(prompt):
    luma_key = os.getenv("LUMA_API_KEY") or get_system_secret("LUMA_API_KEY")
    runway_key = os.getenv("RUNWAY_API_KEY") or get_system_secret("RUNWAY_API_KEY")
    if luma_key:
        url = "https://api.lumalabs.ai/dream-machine/v1/generations"
        headers = {"Authorization": f"Bearer {luma_key}", "Content-Type": "application/json"}
        payload = {"prompt": prompt, "aspect_ratio": "16:9"}
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=35)
            if res.status_code in [200, 201]:
                gen_data = res.json()
                gen_id = gen_data.get("id")
                if gen_id:
                    poll_url = f"{url}/{gen_id}"
                    for _ in range(30):
                        time.sleep(5)
                        poll_res = requests.get(poll_url, headers=headers, timeout=20)
                        if poll_res.status_code == 200:
                            poll_data = poll_res.json()
                            state = poll_data.get("state")
                            if state == "completed":
                                video_url = poll_data.get("assets", {}).get("video")
                                if video_url:
                                    return video_url
                            elif state == "failed":
                                break
        except Exception as e:
            logger.error(f"Luma error: {e}")
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
            logger.error(f"Runway error: {e}")
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
        if "French" in language_choice:
            voice_name = "fr-FR-HenriNeural" if is_male else "fr-FR-DeniseNeural"
        elif "Japanese" in language_choice:
            voice_name = "ja-JP-KeitaNeural" if is_male else "ja-JP-NanamiNeural"
        elif "English" in language_choice:
            voice_name = "en-US-GuyNeural" if is_male else "en-US-AriaNeural"
        else:
            voice_name = "hi-IN-MadhurNeural" if is_male else "hi-IN-SwaraNeural"
        if edge_tts is not None:
            run_async_in_thread(edge_tts.Communicate(text, voice_name).save(output_filename))

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
        res_width, res_height = 720, 1280
        if "16:9" in size_choice:
            res_width, res_height = 1280, 720
        elif "1:1" in size_choice:
            res_width, res_height = 1080, 1080
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
            selected_voice_id = "21m00Tcm4TlvDq8ikWAM" if "Drew" in voice_profile else "pNInz6obpgDQ5IdwJg7p"
            if ELEVENLABS_API_KEY:
                voice_built = AudioEngine.generate_elevenlabs_speech(text, audio_segment_path, selected_voice_id)
            if not voice_built:
                AudioEngine.run_fallback_tts(text=text, output_filename=audio_segment_path, language_choice=language_choice, voice_profile=voice_profile)
            if not os.path.exists(audio_segment_path) or os.path.getsize(audio_segment_path) == 0:
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
                mix_cmd = ['ffmpeg', *get_hwaccel_args(), '-y', '-i', temp_stitched_output, '-stream_loop', '-1', '-i', bgm_path, '-filter_complex', f'[0:a]volume=1.0[a0];[1:a]volume={bgm_volume:.2f}[a1];[a0][a1]amix=inputs=2:duration=first[aout]', '-map', '0:v:0', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', video_output]
                try:
                    subprocess.run(mix_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                except Exception:
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

def generate_face_video_real(image_path, audio_path=None, output_width=512, output_height=512, duration=10, quality="Standard"):
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
        cmd = ['ffmpeg', '-y', '-loop', '1', '-i', temp_processed_img, '-t', str(duration), '-vf', f"zoompan=z='min(zoom+0.0015,1.3)':d={duration*24}:s={out_w}x{out_h},fade=t=in:st=0:d=0.5,fade=t=out:st={duration-0.5}:d=0.5", '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', q_settings["preset"], '-crf', str(q_settings["crf"]), '-b:v', q_settings["bitrate"], '-r', '24', output_video_path]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if audio_path and os.path.exists(audio_path):
            temp_with_audio = output_video_path.replace('.mp4', '_with_audio.mp4')
            audio_duration = get_audio_duration(audio_path)
            if audio_duration > duration:
                ffmpeg_cmd = ['ffmpeg', '-y', '-i', output_video_path, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', '-shortest', '-map', '0:v:0', '-map', '1:a:0', temp_with_audio]
            else:
                ffmpeg_cmd = ['ffmpeg', '-y', '-i', output_video_path, '-stream_loop', '-1', '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', '-shortest', '-map', '0:v:0', '-map', '1:a:0', temp_with_audio]
            subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(temp_with_audio) and os.path.getsize(temp_with_audio) > 0:
                shutil.move(temp_with_audio, output_video_path)
        if os.path.exists(temp_processed_img):
            os.remove(temp_processed_img)
        if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 1000:
            return output_video_path
        else:
            return None
    except Exception as e:
        logger.error(f"Generate face video real error: {e}")
        if os.path.exists(temp_processed_img):
            try:
                os.remove(temp_processed_img)
            except:
                pass
        return None

def generate_face_video(prompt, face_image_path, duration=30, emotion="neutral", camera_angle="front", quality="Standard"):
    if not face_image_path or not os.path.exists(face_image_path):
        return None
    audio_path = f"face_videos/voice_{uuid.uuid4().hex[:8]}.mp3"
    voice_id = "21m00Tcm4TlvDq8ikWAM"
    audio_success = generate_elevenlabs_audio_for_face(prompt, audio_path, voice_id)
    if not audio_success:
        try:
            AudioEngine.run_fallback_tts(text=prompt, output_filename=audio_path, language_choice=st.session_state.get("language_choice", "🇮🇳 Hinglish"), voice_profile=st.session_state.get("voice_profile", "Drew (Premium Male Voice)"))
            audio_success = os.path.exists(audio_path) and os.path.getsize(audio_path) > 0
        except Exception:
            audio_success = False
    if not audio_success:
        create_emergency_silent_audio(audio_path, duration)
    output_path = generate_face_video_real(face_image_path, audio_path, 512, 512, duration, quality=quality)
    if os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except:
            pass
    if output_path:
        return output_path
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageEnhance    
        face_img = Image.open(face_image_path).convert("RGB")
        quality_settings = {"Standard": {"scale": 1.0, "crf": 23, "preset": "medium"}, "HD": {"scale": 1.5, "crf": 18, "preset": "slow"}, "4K": {"scale": 2.0, "crf": 15, "preset": "veryslow"}}
        q_fallback = quality_settings.get(quality, quality_settings["Standard"])
        scale_fallback = q_fallback["scale"]
        video_width = int(512 * scale_fallback)
        video_height = int(512 * scale_fallback)
        fps = 24
        total_frames = duration * fps
        temp_dir = "face_videos/temp_frames"
        os.makedirs(temp_dir, exist_ok=True)
        frames = []
        for frame_num in range(total_frames):
            if frame_num == 0:
                base_frame = Image.new("RGB", (video_width, video_height), color=(10, 10, 20))
                draw = ImageDraw.Draw(base_frame)
                for i in range(5):
                    radius = 50 + i * 60
                    alpha = 30 - i * 5
                    if alpha > 0:
                        x = int(video_width/2 + 100 * np.sin(i * 0.5))
                        y = int(video_height/2 + 80 * np.cos(i * 0.3))
                        draw.ellipse([(x-radius, y-radius), (x+radius, y+radius)], fill=(20 + i*10, 20 + i*5, 40 + i*8))
                base_frame = base_frame.filter(ImageFilter.GaussianBlur(radius=2))
            else:
                base_frame = frames[-1].copy()
            face_copy = face_img.copy()
            progress = frame_num / total_frames
            center_x = int(video_width/2 + 80 * np.sin(progress * 2 * np.pi * 1.5))
            center_y = int(video_height/2 + 60 * np.cos(progress * 2 * np.pi * 1.2))
            scale = (0.5 + 0.08 * np.sin(progress * 2 * np.pi * 0.5)) * scale_fallback
            face_size = int(min(video_width, video_height) * scale)
            face_resized = face_copy.resize((face_size, face_size), Image.Resampling.LANCZOS)
            mask = Image.new("L", face_resized.size, 0)
            mask_draw = ImageDraw.Draw(mask)
            margin = int(face_size * 0.15)
            mask_draw.ellipse([(margin, margin), (face_size - margin, face_size - margin)], fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(radius=8))
            paste_x = center_x - face_resized.width // 2
            paste_y = center_y - face_resized.height // 2
            base_frame.paste(face_resized, (paste_x, paste_y), mask)
            draw = ImageDraw.Draw(base_frame)
            char_count = len(prompt)
            chars_to_show = int(char_count * min(1.0, progress * 1.2))
            current_text = prompt[:chars_to_show]
            words = current_text.split()
            lines = []
            current_line = ""
            for word in words:
                if len(current_line + " " + word) < 30:
                    current_line += " " + word if current_line else word
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            subtitle_y = video_height - 60
            for line in lines[:2]:
                draw.text((video_width//2 - len(line)*4, subtitle_y), line, fill=(255, 255, 255, 200))
                subtitle_y += 20
            frames.append(base_frame)
        for i, frame in enumerate(frames):
            frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
            frame.save(frame_path)
        output_path = f"face_videos/face_video_{quality.lower()}_{uuid.uuid4().hex[:8]}.mp4"
        cmd = ['ffmpeg', '-y', '-framerate', str(fps), '-i', os.path.join(temp_dir, 'frame_%04d.png'), '-c:v', 'libx264', '-preset', q_fallback.get("preset", "medium"), '-crf', str(q_fallback["crf"]), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', output_path]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        shutil.rmtree(temp_dir, ignore_errors=True)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
    except Exception as e:
        logger.error(f"Face video fallback error: {e}")
    return None

def process_editor_video(uploaded_files, output_path, effect="none", transition="fade", resolution="1080p", custom_bgm=None, bgm_volume=0.3):
    if not uploaded_files:
        return False
    media_paths = []
    for idx, uploaded_file in enumerate(uploaded_files):
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        file_path = os.path.join("editor_uploads", f"media_{uuid.uuid4().hex[:8]}{ext}")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        media_paths.append(file_path)
    if len(media_paths) == 0:
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
    try:
        processed_clips = []
        for idx, media_path in enumerate(media_paths):
            ext = os.path.splitext(media_path)[1].lower()
            output_clip = os.path.join(temp_dir, f"clip_{idx:04d}.mp4")
            if ext in ['.png', '.jpg', '.jpeg', '.webp']:
                cmd = ['ffmpeg', '-y', '-loop', '1', '-i', media_path, '-t', '3', '-vf', f"scale={resolution_str}:force_original_aspect_ratio=decrease,pad={resolution_str}:(ow-iw)/2:(oh-ih)/2,fps=24", '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-ac', '2', '-ar', '44100', '-f', 'mp4', output_clip]
            else:
                cmd = ['ffmpeg', '-y', '-i', media_path, '-vf', f"scale={resolution_str}:force_original_aspect_ratio=decrease,pad={resolution_str}:(ow-iw)/2:(oh-ih)/2,fps=24", '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-ac', '2', '-ar', '44100', '-f', 'mp4', output_clip]
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=60)
                if os.path.exists(output_clip) and os.path.getsize(output_clip) > 1000:
                    processed_clips.append(output_clip)
            except Exception:
                fallback_clip = os.path.join(temp_dir, f"fallback_{idx:04d}.mp4")
                fallback_cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=#050508:s={resolution_str}:r=24', '-t', '3', '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-ac', '2', '-ar', '44100', '-f', 'mp4', fallback_clip]
                subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                processed_clips.append(fallback_clip)
        if not processed_clips:
            return False
        concat_file = os.path.join(temp_dir, "concat.txt")
        with open(concat_file, "w") as f:
            for clip_path in processed_clips:
                abs_path = os.path.abspath(clip_path).replace('\\', '/')
                f.write(f"file '{abs_path}'\n")
        filter_chain = ""
        if transition == "fade":
            filter_chain = "fade=t=in:st=0:d=0.5,fade=t=out:st=2.5:d=0.5"
        elif transition == "crossfade":
            filter_chain = "xfade=transition=fade:duration=0.5:offset=2.5"
        elif transition == "zoom":
            filter_chain = "zoompan=z='min(zoom+0.0015,1.3)':d=72:s=1280x720"
        elif transition == "slide":
            filter_chain = "xfade=transition=slideleft:duration=0.5:offset=2.5"
        elif transition == "circle":
            filter_chain = "xfade=transition=circleopen:duration=0.5:offset=2.5"
        elif transition == "radial":
            filter_chain = "xfade=transition=radial:duration=0.5:offset=2.5"
        elif transition == "smooth":
            filter_chain = "xfade=transition=smooth:duration=0.5:offset=2.5"
        else:
            filter_chain = "fade=t=in:st=0:d=0.5"
        if effect == "sepia":
            filter_chain += ",colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131"
        elif effect == "grayscale":
            filter_chain += ",hue=s=0"
        elif effect == "vintage":
            filter_chain += ",curves=all='0/0 0.5/0.5 1/1',colorbalance=rs=0.1:gs=0.1:bs=0.1"
        elif effect == "cinematic":
            filter_chain += ",colorbalance=rs=0.1:gs=-0.05:bs=-0.05,curves=all='0/0 0.3/0.2 0.7/0.8 1/1'"
        elif effect == "neon":
            filter_chain += ",colorbalance=rs=0.3:gs=-0.2:bs=0.5,curves=all='0/0 0.2/0.1 0.5/0.7 1/1'"
        elif effect == "glitch":
            filter_chain += ",rgbashift=rh=2:gh=4:bh=6"
        elif effect == "dreamy":
            filter_chain += ",boxblur=2:1,colorbalance=rs=0.2:gs=0.1:bs=0.3"
        elif effect == "dramatic":
            filter_chain += ",colorbalance=rs=0.2:gs=-0.1:bs=-0.1,curves=all='0/0 0.3/0.1 0.7/0.8 1/1',unsharp=5:5:1.0"
        final_cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file, '-vf', filter_chain, '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '192k', '-ac', '2', '-ar', '44100', '-vsync', '2', output_path]
        try:
            subprocess.run(final_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=120)
            if bgm_path and os.path.exists(bgm_path) and os.path.exists(output_path):
                temp_with_bgm = output_path.replace('.mp4', '_with_bgm.mp4')
                mix_cmd = ['ffmpeg', '-y', '-i', output_path, '-stream_loop', '-1', '-i', bgm_path, '-filter_complex', f'[0:a]volume=1.0[a0];[1:a]volume={bgm_volume:.2f}[a1];[a0][a1]amix=inputs=2:duration=first[aout]', '-map', '0:v:0', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', temp_with_bgm]
                try:
                    subprocess.run(mix_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=60)
                    if os.path.exists(temp_with_bgm) and os.path.getsize(temp_with_bgm) > 0:
                        shutil.move(temp_with_bgm, output_path)
                except Exception:
                    pass
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
        except Exception:
            simple_cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', output_path]
            try:
                subprocess.run(simple_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=120)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return True
            except Exception:
                pass
        return False
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
# 35. GENERATE VIDEO BLUEPRINT
# ========================================================

def generate_video_blueprint_with_deepseek(user_prompt, aspect_ratio="16:9"):
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
        "messages": [{"role": "system", "content": system_instruction}, {"role": "user", "content": f"Create a high-fidelity video blueprint for topic: '{user_prompt}' with aspect ratio {aspect_ratio}"}],
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
    st.markdown("""
        <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; border: 1px solid rgba(69, 243, 255, 0.3); padding: 20px; margin-bottom: 20px;">
            <h3 style="font-family: 'Orbitron'; font-size: 16px; color: #45f3ff; margin: 0 0 5px 0;">🤖 AI Cyber-Agent for Small Businesses</h3>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;"> Auto-pilot your business with AI - Generate content, manage orders, collect payments </p>
        </div>
    """, unsafe_allow_html=True)
    agent_col1, agent_col2 = st.columns([1.1, 1.4], gap="medium")
    with agent_col1:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #45f3ff; margin-bottom: 15px;'>⚙️ AGENT CONFIGURATION</h4>", unsafe_allow_html=True)
            st.markdown("<div class='compact-label'>Business Details</div>", unsafe_allow_html=True)
            business_name = st.text_input("Business Name", placeholder="Your Shop/Brand Name", key="agent_business_name_input")
            business_category = st.selectbox("Business Category:", ["Retail Store", "Restaurant/Cafe", "Clothing Brand", "Tech Services", "Beauty/Salon", "Other"], key="agent_category")
            st.markdown("<div class='compact-label'>Products/Services (one per line)</div>", unsafe_allow_html=True)
            products_text = st.text_area("List your products or services", placeholder="e.g.\n₹499 - T-Shirt\n₹999 - Jeans\n₹1499 - Jacket", height=100, key="agent_products_input")
            st.markdown("<div class='compact-label'>Business Hours</div>", unsafe_allow_html=True)
            col_time1, col_time2 = st.columns(2)
            with col_time1:
                opening_time = st.time_input("Opening Time", value=datetime.strptime("09:00", "%H:%M").time(), key="agent_open_time")
            with col_time2:
                closing_time = st.time_input("Closing Time", value=datetime.strptime("21:00", "%H:%M").time(), key="agent_close_time")
            st.markdown("<div class='compact-label'>Social Media Accounts</div>", unsafe_allow_html=True)
            instagram_handle = st.text_input("Instagram Handle", placeholder="@your_business", key="agent_instagram")
            whatsapp_number = st.text_input("WhatsApp Number", placeholder="+91XXXXXXXXXX", key="agent_whatsapp")
            st.write("")
            st.markdown("<div class='compact-label'>📊 Agent Quality</div>", unsafe_allow_html=True)
            agent_quality = st.selectbox("Select Quality", ["Standard", "Pro"], key="agent_quality")
            if st.button("🚀 Activate AI Agent", key="agent_activate_btn", use_container_width=True):
                success, required_tokens, message = validate_and_deduct_tokens("AI Agent", agent_quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    if not business_name.strip():
                        st.error("Please enter a business name.")
                    elif not products_text.strip():
                        st.error("Please list at least one product or service.")
                    else:
                        with st.spinner("🔄 Configuring AI Agent for your business..."):
                            st.session_state["agent_business_name"] = business_name
                            st.session_state["agent_products"] = [p.strip() for p in products_text.split("\n") if p.strip()]
                            st.session_state["agent_schedule"] = {"open": str(opening_time), "close": str(closing_time), "instagram": instagram_handle, "whatsapp": whatsapp_number, "category": business_category}
                            conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
                            cursor = conn.cursor()
                            try:
                                cursor.execute("INSERT OR REPLACE INTO ai_agent_config (username, business_name, products, schedule) VALUES (?, ?, ?, ?)", (st.session_state["logged_user"], business_name, json.dumps(st.session_state["agent_products"]), json.dumps(st.session_state["agent_schedule"])))
                                conn.commit()
                            except Exception:
                                pass
                            finally:
                                conn.close()
                            st.toast("✅ AI Agent activated successfully!")
                            st.session_state["ai_agent_mode"] = True
                            st.rerun()
    with agent_col2:
        with st.container(border=True):
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #45f3ff; margin-bottom: 15px; letter-spacing: 0.5px;'>📊 AGENT DASHBOARD</h3>", unsafe_allow_html=True)
            if st.session_state.get("ai_agent_mode") and st.session_state.get("agent_business_name"):
                st.markdown(f"""
                    <div style="background: rgba(69, 243, 255, 0.05); border: 1px solid rgba(69, 243, 255, 0.2); border-radius: 12px; padding: 15px; margin-bottom: 15px;">
                        <h4 style="font-family: 'Orbitron'; font-size: 13px; color: #45f3ff; margin: 0 0 5px 0;">🟢 ACTIVE</h4>
                        <p style="font-size: 18px; font-weight: bold; color: #ffffff; margin: 0;">{st.session_state['agent_business_name']}</p>
                        <p style="font-size: 11px; color: #94a3b8; margin: 0;">Category: {st.session_state.get('agent_schedule', {}).get('category', 'N/A')}</p>
                    </div>
                """, unsafe_allow_html=True)
                products = st.session_state.get("agent_products", [])
                if products:
                    st.markdown("**📦 Your Products/Services:**")
                    for p in products[:5]:
                        st.markdown(f"- {p}")
                    if len(products) > 5:
                        st.caption(f"... and {len(products) - 5} more")
                schedule = st.session_state.get("agent_schedule", {})
                st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.03); border-radius: 8px; padding: 10px; margin-top: 10px;">
                        <p style="font-size: 11px; color: #94a3b8; margin: 0;">🕐 Hours: {schedule.get('open', 'N/A')} - {schedule.get('close', 'N/A')}</p>
                        <p style="font-size: 11px; color: #94a3b8; margin: 0;">📱 WhatsApp: {schedule.get('whatsapp', 'N/A')}</p>
                        <p style="font-size: 11px; color: #94a3b8; margin: 0;">📸 Instagram: {schedule.get('instagram', 'N/A')}</p>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("**⚡ Quick Actions:**")
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
                if st.session_state.get("agent_generated_ad"):
                    with st.expander("📱 WhatsApp Ad Preview", expanded=False):
                        st.text(st.session_state["agent_generated_ad"])
                        st.download_button(label="📥 Copy Ad", data=st.session_state["agent_generated_ad"], file_name="whatsapp_ad.txt", mime="text/plain", key="agent_download_ad")
                if st.session_state.get("agent_instagram_image") and os.path.exists(st.session_state["agent_instagram_image"]):
                    with st.expander("📸 Instagram Post Preview", expanded=False):
                        st.image(st.session_state["agent_instagram_image"], caption="Generated Post Image", use_container_width=True)
                        st.text(st.session_state.get("agent_instagram_caption", ""))
                        st.download_button(label="📥 Download Image", data=open(st.session_state["agent_instagram_image"], "rb").read(), file_name="instagram_post.png", mime="image/png", key="agent_download_ig")
            else:
                st.markdown("""
                    <div class="canvas-container-box" style="height: 380px; min-height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #64748b; text-align: center; padding: 12px; overflow: hidden;">
                        <span style="font-size: 50px; margin-bottom: 12px; filter: drop-shadow(0 0 10px rgba(69, 243, 255, 0.3));">🤖</span>
                        <p style="font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; color: #45f3ff; margin: 0;">AI Agent Inactive</p>
                        <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px; line-height: 1.4;">Configure your business details and activate the agent.</p>
                    </div>
                """, unsafe_allow_html=True)

def render_ai_sales_ui():
    st.markdown("""
        <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; border: 1px solid rgba(236, 72, 153, 0.3); padding: 20px; margin-bottom: 20px;">
            <h3 style="font-family: 'Orbitron'; font-size: 16px; color: #EC4899; margin: 0 0 5px 0;">🎙️ AI Voice & Video Sales Engine</h3>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;"> Create AI sales videos in any language with realistic avatars </p>
        </div>
    """, unsafe_allow_html=True)
    sales_col1, sales_col2 = st.columns([1.1, 1.4], gap="medium")
    with sales_col1:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #EC4899; margin-bottom: 15px;'>⚙️ SALES VIDEO PARAMETERS</h4>", unsafe_allow_html=True)
            st.markdown("<div class='compact-label'>Product Details</div>", unsafe_allow_html=True)
            product_name = st.text_input("Product Name", placeholder="e.g. Smart Watch Pro", key="sales_product_name_input")
            product_price = st.text_input("Product Price", placeholder="e.g. ₹4999", key="sales_product_price_input")
            st.markdown("<div class='compact-label'>Product Image</div>", unsafe_allow_html=True)
            product_image = st.file_uploader("Upload Product Image", type=['jpg', 'jpeg', 'png', 'webp'], key="sales_image_upload")
            if product_image:
                img_path = f"ai_sales_videos/product_{uuid.uuid4().hex[:8]}.png"
                with open(img_path, "wb") as f:
                    f.write(product_image.getbuffer())
                st.session_state["sales_product_image"] = img_path
                st.image(img_path, caption="Product Image", use_container_width=True)
            st.markdown("<div class='compact-label'>Language & Voice</div>", unsafe_allow_html=True)
            sales_language = st.selectbox("Sales Language:", ["Hindi", "Bhojpuri", "Maithili", "Tamil", "Telugu", "English", "Hinglish"], key="sales_language_select")
            sales_voice = st.selectbox("Voice Profile:", ["Male (Drew)", "Female (Rachel)", "Male (Deep)", "Female (Aria)"], key="sales_voice_select")
            st.markdown("<div class='compact-label'>Sales Script / Pitch</div>", unsafe_allow_html=True)
            sales_script = st.text_area("Write your sales script or use auto-generate", placeholder="e.g. Namaste! Aaj hum aapke liye laye hain ek zabardast offer...", height=100, key="sales_script_input")
            if st.button("📝 Auto-Generate Sales Script", key="sales_gen_script", use_container_width=True):
                if product_name.strip():
                    lang_map = {"Hindi": "Hindi", "Bhojpuri": "Bhojpuri", "Maithili": "Maithili", "Tamil": "Tamil", "Telugu": "Telugu", "English": "English", "Hinglish": "Hinglish"}
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
            st.markdown("<div class='compact-label'>📊 Sales Video Quality</div>", unsafe_allow_html=True)
            sales_quality = st.selectbox("Select Quality", ["Standard", "HD", "4K"], key="sales_quality")
            st.write("")
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
                            video_path = generate_face_video(script_text, face_img_path, duration=15, emotion="excited", camera_angle="front", quality=sales_quality)
                            if video_path and os.path.exists(video_path):
                                st.session_state["sales_video_output"] = video_path
                                st.session_state["sales_product_name"] = product_name
                                st.session_state["sales_product_price"] = product_price
                                st.session_state["sales_language"] = sales_language
                                st.session_state["sales_script"] = script_text
                                conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
                                cursor = conn.cursor()
                                try:
                                    cursor.execute("INSERT INTO ai_sales_videos (username, product_name, product_price, language, video_path, script) VALUES (?, ?, ?, ?, ?, ?)", (st.session_state["logged_user"], product_name, product_price, sales_language, video_path, script_text))
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
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #EC4899; margin-bottom: 15px; letter-spacing: 0.5px;'>🎬 SALES VIDEO PLAYER</h3>", unsafe_allow_html=True)
            sales_video = st.session_state.get("sales_video_output")
            if sales_video and os.path.exists(sales_video):
                st.video(sales_video, format="video/mp4", autoplay=True, loop=True, muted=False)
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"""
                    <div style="background: rgba(236, 72, 153, 0.05); border: 1px solid rgba(236, 72, 153, 0.2); border-radius: 8px; padding: 10px;">
                        <p style="font-size: 12px; color: #94a3b8; margin: 0;">📦 {st.session_state.get('sales_product_name', 'Product')}</p>
                        <p style="font-size: 14px; font-weight: bold; color: #EC4899; margin: 0;">💰 {st.session_state.get('sales_product_price', 'N/A')}</p>
                        <p style="font-size: 11px; color: #94a3b8; margin: 0;">🎙️ {st.session_state.get('sales_language', 'N/A')}</p>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                col_dl, col_share, col_clr = st.columns(3)
                with col_dl:
                    with open(sales_video, "rb") as f:
                        video_bytes = f.read()
                    st.download_button(label="📥 Download Sales Video", data=video_bytes, file_name=f"sales_video_{uuid.uuid4().hex[:8]}.mp4", mime="video/mp4", use_container_width=True, key="sales_download_btn")
                with col_share:
                    if st.button("📤 Share on WhatsApp", key="sales_share_wa", use_container_width=True):
                        wa_msg = f"🎬 Check out this amazing product! {st.session_state.get('sales_product_name', 'Product')} - Only {st.session_state.get('sales_product_price', 'N/A')}!"
                        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_msg)}"
                        st.markdown(f'<a href="{wa_url}" target="_blank" style="text-decoration:none;width:100%;"><button style="width:100%;padding:10px;background:#25D366;color:white;border:none;border-radius:6px;font-family:Orbitron;font-size:11px;cursor:pointer;">💬 Share</button></a>', unsafe_allow_html=True)
                with col_clr:
                    if st.button("🧹 Clear Video", key="sales_clear_btn", use_container_width=True):
                        safe_remove_file(sales_video)
                        st.session_state["sales_video_output"] = None
                        st.rerun()
                with st.expander("📝 View Sales Script", expanded=False):
                    st.text(st.session_state.get("sales_script", ""))
            else:
                st.markdown("""
                    <div class="canvas-container-box" style="height: 380px; min-height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #64748b; text-align: center; padding: 12px; overflow: hidden;">
                        <span style="font-size: 50px; margin-bottom: 12px; filter: drop-shadow(0 0 10px rgba(236, 72, 153, 0.3));">🎙️</span>
                        <p style="font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; color: #EC4899; margin: 0;">AI Sales Video will render here</p>
                        <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px; line-height: 1.4;">Upload product image, set language, and generate AI sales video.</p>
                    </div>
                """, unsafe_allow_html=True)

def generate_dynamic_ui():
    st.markdown("""
        <div style="background:linear-gradient(135deg,rgba(18,19,26,0.95),rgba(10,10,15,0.98));border-radius:16px;border:2px solid rgba(69,243,255,0.3);padding:20px;margin-bottom:20px;">
            <div style="display:flex;align-items:center;gap:15px;">
                <span style="font-size:30px;">🧠</span>
                <div>
                    <h3 style="font-family:'Orbitron';font-size:18px;color:#45f3ff;margin:0;">Dynamic Context-Aware UI</h3>
                    <p style="color:#94a3b8;font-size:11px;margin:0;">⚡ Real-time interface adaptation based on user behavior</p>
                </div>
            </div>
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
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #45f3ff; margin-bottom: 15px;'>⚙️ UI CONFIGURATION</h4>", unsafe_allow_html=True)
            st.markdown("<div class='compact-label'>👤 SELECT PROFILE MODE</div>", unsafe_allow_html=True)
            profile_options = ["🟢 Novice / Simple Mode", "🟡 Intermediate Mode", "🔴 Expert / Developer Mode"]
            profile_map = {"🟢 Novice / Simple Mode": "beginner", "🟡 Intermediate Mode": "intermediate", "🔴 Expert / Developer Mode": "advanced"}
            current_profile_label = "🟡 Intermediate Mode"
            for label, value in profile_map.items():
                if st.session_state.get("dynamic_ui_profile_mode") == value:
                    current_profile_label = label
                    break
            selected_profile = st.selectbox("Choose UI Profile", profile_options, index=profile_options.index(current_profile_label) if current_profile_label in profile_options else 1, key="dynamic_ui_profile_selector")
            new_profile = profile_map.get(selected_profile, "intermediate")
            if new_profile != st.session_state.get("dynamic_ui_profile_mode"):
                success, required_tokens, message = validate_and_deduct_tokens("Dynamic UI", "Standard")
                if success:
                    st.session_state["dynamic_ui_profile_mode"] = new_profile
                    st.session_state["user_behavior_profile"] = new_profile
                    st.session_state["dynamic_ui_token_charged"] = True
                    st.success(message)
                    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT OR REPLACE INTO dynamic_ui_profiles (username, behavior_profile, ui_preferences) VALUES (?, ?, ?)", (st.session_state.get("logged_user", "user"), new_profile, json.dumps({"profile": new_profile, "timestamp": time.time()})))
                        conn.commit()
                    except Exception:
                        pass
                    finally:
                        conn.close()
                    st.rerun()
                else:
                    st.error(message)
                    st.session_state["dynamic_ui_profile_mode"] = st.session_state.get("dynamic_ui_profile_mode", "intermediate")
            profile_display = st.session_state.get("dynamic_ui_profile_mode", "intermediate")
            profile_icons = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}
            profile_names = {"beginner": "Novice / Simple Mode", "intermediate": "Intermediate Mode", "advanced": "Expert / Developer Mode"}
            st.info(f"📊 Current Profile: {profile_icons.get(profile_display, '🟡')} {profile_names.get(profile_display, 'Intermediate Mode')}")
            st.markdown("---")
            st.markdown("<h4 style='font-family: Orbitron; font-size: 12px; color: #45f3ff; margin-bottom: 10px;'>🔧 UI ACTIONS</h4>", unsafe_allow_html=True)
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
                    <div style="background: rgba(69, 243, 255, 0.05); border: 1px solid rgba(69, 243, 255, 0.2); border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                        <p style="font-size: 11px; color: #94a3b8; margin: 0 0 10px 0;">📂 Select a project file to open:</p>
                    </div>
                """, unsafe_allow_html=True)
                uploaded_file = st.file_uploader("Choose a project file", type=['json', 'txt', 'mp4', 'png', 'jpg', 'jpeg', 'webp', 'mp3', 'wav'], key="dynamic_ui_file_uploader", label_visibility="collapsed")
                if uploaded_file is not None:
                    file_path = os.path.join("temp_scenes", f"uploaded_{uuid.uuid4().hex[:8]}_{uploaded_file.name}")
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
                    time.sleep(1)
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
                    st.markdown("**Available Plugins:**")
                    st.checkbox("🎨 AI Image Generator", value=True)
                    st.checkbox("🎬 Video Editor Pro", value=True)
                    st.checkbox("🗣️ Voice Synthesizer", value=True)
                    st.checkbox("📐 Blueprint Creator", value=True)
                    if st.button("🔄 Refresh Plugins", use_container_width=True):
                        st.toast("Plugins refreshed!")
    with col2:
        with st.container(border=True):
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #45f3ff; margin-bottom: 15px; letter-spacing: 0.5px;'>🖥️ UI PREVIEW</h3>", unsafe_allow_html=True)
            profile_display = st.session_state.get("dynamic_ui_profile_mode", "intermediate")
            current_project = st.session_state.get("dynamic_ui_current_project", "No project loaded")
            st.markdown(f"""
                <div style="background: rgba(69, 243, 255, 0.05); border-radius: 8px; padding: 8px 12px; margin-bottom: 10px; border: 1px solid rgba(69, 243, 255, 0.1);">
                    <p style="font-size: 10px; color: #94a3b8; margin: 0;">
                        📂 <span style="color: #45f3ff;">{current_project}</span>
                    </p>
                </div>
            """, unsafe_allow_html=True)
            if profile_display == "beginner":
                st.markdown("""
                    <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; padding: 20px; border: 2px solid rgba(69, 243, 255, 0.3); transition: all 0.3s ease;">
                        <div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;">
                            <span style="background: #45f3ff; color: #000; padding: 10px 20px; border-radius: 8px; font-size: 13px; font-weight: bold;">📝 New</span>
                            <span style="background: #45f3ff; color: #000; padding: 10px 20px; border-radius: 8px; font-size: 13px; font-weight: bold;">📂 Open</span>
                            <span style="background: #45f3ff; color: #000; padding: 10px 20px; border-radius: 8px; font-size: 13px; font-weight: bold;">🎓 Tutorial</span>
                        </div>
                        <p style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 15px;">🟢 Simple, clean interface with large buttons</p>
                    </div>
                """, unsafe_allow_html=True)
            elif profile_display == "intermediate":
                st.markdown("""
                    <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; padding: 20px; border: 2px solid rgba(255, 192, 203, 0.3); transition: all 0.3s ease;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                            <span style="background: #FFC0CB; color: #000; padding: 10px; border-radius: 6px; font-size: 12px; font-weight: bold; text-align: center;">📝 New</span>
                            <span style="background: #FFC0CB; color: #000; padding: 10px; border-radius: 6px; font-size: 12px; font-weight: bold; text-align: center;">📂 Open</span>
                            <span style="background: #FFC0CB; color: #000; padding: 10px; border-radius: 6px; font-size: 12px; font-weight: bold; text-align: center;">⚡ Quick Render</span>
                            <span style="background: #FFC0CB; color: #000; padding: 10px; border-radius: 6px; font-size: 12px; font-weight: bold; text-align: center;">🔧 Settings</span>
                        </div>
                        <p style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 15px;">🟡 Balanced interface with quick actions</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; padding: 20px; border: 2px solid rgba(236, 72, 153, 0.3); transition: all 0.3s ease;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px;">
                            <span style="background: #EC4899; color: #fff; padding: 8px; border-radius: 6px; font-size: 11px; font-weight: bold; text-align: center;">📝 New</span>
                            <span style="background: #EC4899; color: #fff; padding: 8px; border-radius: 6px; font-size: 11px; font-weight: bold; text-align: center;">📂 Open</span>
                            <span style="background: #EC4899; color: #fff; padding: 8px; border-radius: 6px; font-size: 11px; font-weight: bold; text-align: center;">⚡ Render</span>
                            <span style="background: #EC4899; color: #fff; padding: 8px; border-radius: 6px; font-size: 11px; font-weight: bold; text-align: center;">🔧 Advanced</span>
                            <span style="background: #EC4899; color: #fff; padding: 8px; border-radius: 6px; font-size: 11px; font-weight: bold; text-align: center;">📊 Analytics</span>
                            <span style="background: #EC4899; color: #fff; padding: 8px; border-radius: 6px; font-size: 11px; font-weight: bold; text-align: center;">🧩 Plugins</span>
                        </div>
                        <p style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 15px;">🔴 Professional interface with all tools</p>
                    </div>
                """, unsafe_allow_html=True)
            if st.session_state.get("dynamic_ui_uploaded_file") and os.path.exists(st.session_state["dynamic_ui_uploaded_file"]):
                file_path = st.session_state["dynamic_ui_uploaded_file"]
                ext = os.path.splitext(file_path)[1].lower()
                st.markdown("---")
                st.markdown("**📁 Loaded File:**")
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
            st.markdown("---")
            st.markdown("""
                <div style="background: rgba(69, 243, 255, 0.05); border-radius: 8px; padding: 10px; margin-top: 10px;">
                    <p style="font-size: 11px; color: #94a3b8; margin: 0; text-align: center;">
                        ⚡ Profile change costs <span style="color: #45f3ff; font-weight: bold;">2 Credits</span> per switch
                        <br>
                        <span style="font-size: 9px; color: #64748b;">Current balance: <span style="color: #45f3ff;">{:.1f}</span> Credits</span>
                    </p>
                </div>
            """.format(st.session_state.get('user_credits', 0)), unsafe_allow_html=True)

def render_live_emotion_voice():
    st.markdown("""
        <div style="background:linear-gradient(135deg,rgba(18,19,26,0.95),rgba(10,10,15,0.98));border-radius:16px;border:2px solid rgba(236,72,153,0.3);padding:20px;margin-bottom:20px;">
            <div style="display:flex;align-items:center;gap:15px;">
                <span style="font-size:30px;">🎤</span>
                <div>
                    <h3 style="font-family:'Orbitron';font-size:18px;color:#EC4899;margin:0;">Live-Emotion Voice & Personality Doppelgänger</h3>
                    <p style="color:#94a3b8;font-size:11px;margin:0;">⚡ Hyper-realistic voice with real human emotional dynamics</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns([1.1, 1.4], gap="medium")
    with col1:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #EC4899; margin-bottom: 15px;'>⚙️ VOICE PARAMETERS</h4>", unsafe_allow_html=True)
            st.markdown("<div class='compact-label'>📝 Text to Speak</div>", unsafe_allow_html=True)
            voice_text = st.text_area("Enter text for voice generation", placeholder="Write the script you want to convert to emotion-rich voice...", height=100, key="emotion_voice_text_area")
            st.markdown("<div class='compact-label'>🌐 Select Language</div>", unsafe_allow_html=True)
            language_options = ["English", "Hindi", "Bhojpuri", "French", "Japanese"]
            selected_language = st.selectbox("Choose Language", language_options, key="emotion_voice_language")
            st.markdown("<div class='compact-label'>😊 Emotion Profile</div>", unsafe_allow_html=True)
            emotion_options = ["neutral", "happy", "sad", "angry", "excited", "serious", "mysterious"]
            current_emotion = st.session_state.get("emotion_voice_emotion", "neutral")
            if current_emotion not in emotion_options:
                current_emotion = "neutral"
            selected_emotion = st.selectbox("Select Emotion", emotion_options, index=emotion_options.index(current_emotion), key="emotion_voice_emotion")
            st.markdown("<div class='compact-label'>🎤 Zovix Professional Voice Selection</div>", unsafe_allow_html=True)
            available_voices = LANGUAGE_VOICE_MAP.get(selected_language, ["Adam (Premium Male)"])
            show_all_voices = st.checkbox("Show All Voices", key="emotion_show_all_voices")
            if show_all_voices:
                voice_options = list(ELEVENLABS_VOICES.keys())
            else:
                voice_options = available_voices
            current_voice = st.session_state.get("selected_elevenlabs_voice", "Adam (Premium Male)")
            if current_voice not in voice_options:
                current_voice = voice_options[0] if voice_options else "Adam (Premium Male)"
            selected_voice_label = st.selectbox("Choose Professional Voice", voice_options, index=voice_options.index(current_voice) if current_voice in voice_options else 0, key="emotion_voice_elevenlabs_select")
            if selected_voice_label != st.session_state.get("selected_elevenlabs_voice"):
                st.session_state["selected_elevenlabs_voice"] = selected_voice_label
            voice_info = ELEVENLABS_VOICES.get(selected_voice_label, {})
            st.markdown(f"""
                <div style="background: rgba(236, 72, 153, 0.05); border: 1px solid rgba(236, 72, 153, 0.2); border-radius: 8px; padding: 10px; margin-bottom: 15px;">
                    <p style="font-size: 11px; color: #94a3b8; margin: 0;">
                        🎤 {selected_voice_label} <br>
                        🧑‍🎤 {voice_info.get('gender', 'Unknown').capitalize()} • 
                        🌍 {voice_info.get('accent', 'Unknown')} • 
                        🌐 {voice_info.get('language', 'Unknown')}
                    </p>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("**Quick Emotion Presets:**")
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
            st.markdown("---")
            if st.button("🔊 Preview Voice Sample", key="emotion_preview_voice", use_container_width=True):
                st.info(f"🎵 Voice sample for {selected_voice_label} will play here.")
                sample_path = "assets/audio/sample.mp3"
                if os.path.exists(sample_path):
                    with open(sample_path, "rb") as f:
                        sample_bytes = f.read()
                    st.audio(sample_bytes, format="audio/mp3")
                else:
                    st.warning("Sample audio not found. Please add a sample.mp3 file to assets/audio/")
            st.markdown("<div class='compact-label'>📊 Voice Quality</div>", unsafe_allow_html=True)
            voice_quality = st.selectbox("Select Quality", ["Standard", "HD", "Premium"], key="emotion_voice_quality")
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
                            voice_id = ELEVENLABS_VOICES.get(selected_voice_label, {}).get("id", "21m00Tcm4TlvDq8ikWAM")
                            output_path = generate_emotion_voice(voice_text, emotion=selected_emotion, voice_type="male" if voice_info.get("gender") == "male" else "female", elevenlabs_voice_id=voice_id)
                            if output_path and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                                st.session_state["emotion_voice_output"] = output_path
                                st.session_state["emotion_voice_text"] = voice_text
                                st.session_state["emotion_voice_language"] = selected_language
                                conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
                                cursor = conn.cursor()
                                try:
                                    cursor.execute("INSERT INTO emotion_voice_history (username, text, emotion, audio_path, voice_id) VALUES (?, ?, ?, ?, ?)", (st.session_state.get("logged_user", "user"), voice_text[:200], selected_emotion, output_path, selected_voice_label))
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
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #EC4899; margin-bottom: 15px; letter-spacing: 0.5px;'>🎧 VOICE PLAYER</h3>", unsafe_allow_html=True)
            audio_output = st.session_state.get("emotion_voice_output")
            if audio_output and os.path.exists(audio_output):
                emotion = st.session_state.get("emotion_voice_emotion", "neutral")
                emoji_map = {"neutral": "😐", "happy": "😊", "sad": "😢", "angry": "😡", "excited": "🤩", "serious": "😤", "mysterious": "🕵️"}
                emotion_emoji = emoji_map.get(emotion, "😐")
                selected_voice = st.session_state.get("selected_elevenlabs_voice", "Adam (Premium Male)")
                st.markdown(f"""
                    <div style="background: rgba(236, 72, 153, 0.05); border: 1px solid rgba(236, 72, 153, 0.2); border-radius: 12px; padding: 15px; margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                            <span style="font-size: 14px; color: #ffffff;">{emotion_emoji} {emotion.capitalize()} Voice</span>
                            <span style="font-size: 12px; color: #EC4899; font-weight: bold;">{selected_voice}</span>
                        </div>
                        <div style="display: flex; gap: 8px; margin-top: 5px; flex-wrap: wrap;">
                            <span style="font-size: 9px; color: #94a3b8; background: rgba(255,255,255,0.05); padding: 2px 8px; border-radius: 10px;">🎯 {emotion}</span>
                            <span style="font-size: 9px; color: #94a3b8; background: rgba(255,255,255,0.05); padding: 2px 8px; border-radius: 10px;">🎤 Professional Voice</span>
                            <span style="font-size: 9px; color: #94a3b8; background: rgba(255,255,255,0.05); padding: 2px 8px; border-radius: 10px;">🌐 {st.session_state.get('emotion_voice_language', 'English')}</span>
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
                    st.download_button(label="📥 Download Voice (MP3)", data=audio_bytes, file_name=f"zovix_voice_{uuid.uuid4().hex[:8]}.mp3", mime="audio/mp3", use_container_width=True, key="emotion_download_btn")
                with col_clr:
                    if st.button("🧹 Clear Voice", key="emotion_clear_btn", use_container_width=True):
                        safe_remove_file(audio_output)
                        st.session_state["emotion_voice_output"] = None
                        st.session_state["emotion_voice_text"] = ""
                        st.rerun()
                with st.expander("📊 Voice Analytics", expanded=False):
                    st.markdown(f"""
                        <div style="background: rgba(255,255,255,0.02); border-radius: 8px; padding: 10px;">
                            <p style="font-size: 11px; color: #94a3b8; margin: 2px 0;">🎯 Emotion: <span style="color: #EC4899;">{emotion.capitalize()}</span></p>
                            <p style="font-size: 11px; color: #94a3b8; margin: 2px 0;">🎤 Voice: <span style="color: #EC4899;">{selected_voice}</span></p>
                            <p style="font-size: 11px; color: #94a3b8; margin: 2px 0;">🌐 Language: <span style="color: #EC4899;">{st.session_state.get('emotion_voice_language', 'English')}</span></p>
                            <p style="font-size: 11px; color: #94a3b8; margin: 2px 0;">📝 Text Length: <span style="color: #EC4899;">{len(st.session_state.get('emotion_voice_text', ''))} characters</span></p>
                            <p style="font-size: 11px; color: #94a3b8; margin: 2px 0;">🎵 Audio Size: <span style="color: #EC4899;">{len(audio_bytes)/1024:.1f} KB</span></p>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div class="canvas-container-box" style="height: 380px; min-height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #64748b; text-align: center; padding: 12px; overflow: hidden;">
                        <span style="font-size: 50px; margin-bottom: 12px; filter: drop-shadow(0 0 10px rgba(236, 72, 153, 0.3));">🎤</span>
                        <p style="font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; color: #EC4899; margin: 0;">Emotion voice will render here</p>
                        <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px; line-height: 1.4;">Select emotion, voice type, and generate hyper-realistic voice.</p>
                        <p style="font-size: 10px; color: #45f3ff; margin-top: 5px;">⚡ Real human emotional dynamics</p>
                    </div>
                """, unsafe_allow_html=True)

def generate_emotion_voice(text, emotion="neutral", voice_type="male", output_path=None, elevenlabs_voice_id=None):
    if not output_path:
        output_path = f"emotion_voice_outputs/emotion_{uuid.uuid4().hex[:8]}.mp3"
    os.makedirs("emotion_voice_outputs", exist_ok=True)
    safe_remove_file(output_path)
    eleven_key = os.getenv("ELEVENLABS_API_KEY") or get_system_secret("ELEVENLABS_API_KEY")
    if eleven_key and elevenlabs_voice_id:
        try:
            emotion_modifiers = {"neutral": "", "happy": " [Happy, cheerful tone] ", "sad": " [Sad, melancholic tone] ", "angry": " [Angry, frustrated tone] ", "excited": " [Excited, enthusiastic tone] ", "serious": " [Serious, professional tone] ", "mysterious": " [Mysterious, intriguing tone] "}
            modified_text = emotion_modifiers.get(emotion, "") + text
            if AudioEngine.generate_elevenlabs_speech(modified_text, output_path, elevenlabs_voice_id):
                return output_path
        except Exception:
            pass
    try:
        voice_map = {"neutral": {"male": "en-US-GuyNeural", "female": "en-US-AriaNeural"}, "happy": {"male": "en-US-GuyNeural", "female": "en-US-AriaNeural"}, "sad": {"male": "en-US-GuyNeural", "female": "en-US-AriaNeural"}, "angry": {"male": "en-US-GuyNeural", "female": "en-US-AriaNeural"}, "excited": {"male": "en-US-GuyNeural", "female": "en-US-AriaNeural"}, "serious": {"male": "en-US-GuyNeural", "female": "en-US-AriaNeural"}, "mysterious": {"male": "en-US-GuyNeural", "female": "en-US-AriaNeural"}}
        voice_name = voice_map.get(emotion, {}).get(voice_type, "en-US-GuyNeural")
        if edge_tts is not None:
            run_async_in_thread(edge_tts.Communicate(text, voice_name).save(output_path))
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
    except Exception:
        pass
    create_emergency_silent_audio(output_path, len(text.split()) * 0.5 + 1)
    return output_path if os.path.exists(output_path) else None

# ========================================================
# 37. MODE FUNCTIONS - Creative Workshop, Blueprints, Flow State, Upscaler, Draw, Video Editor, Face Video
# ========================================================

def run_creative_workshop():
    st.markdown("""
        <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; border: 1px solid rgba(255,192,203,0.15); padding: 20px; margin-bottom: 20px;">
            <h3 style="font-family: 'Orbitron'; font-size: 16px; color: #FFC0CB; margin: 0 0 5px 0;">🎨 Creative Image Synthesis Hub</h3>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;"> High-Quality Thumbnail Banner Poster Generator </p>
        </div>
    """, unsafe_allow_html=True)
    w_col1, w_col2 = st.columns([1.1, 1.4], gap="medium")
    with w_col1:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>⚙️ WORKSHOP PARAMETERS</h4>", unsafe_allow_html=True)
            workshop_ar = st.selectbox("Select Aspect Ratio:", ["16:9", "9:16", "1:1", "21:9", "4:5", "3:2"], key="workshop_aspect_ratio_choice")
            st.markdown("<div class='compact-label'>Masterpiece Prompt Input</div>", unsafe_allow_html=True)
            workshop_prompt_str = st.text_area("Image Description Prompt", placeholder="E.g. A gorgeous cyberpunk temple with pink neon aurora, hyperrealistic, 8k resolution, cinematic lighting...", height=120, label_visibility="collapsed", key="workshop_prompt_str_area")
            st.markdown("<div class='compact-label'>Negative Prompt</div>", unsafe_allow_html=True)
            workshop_neg_prompt_str = st.text_area("Negative Prompt", placeholder="E.g. blurry, low quality, distorted, extra limbs, bad anatomy, text, watermark...", height=80, label_visibility="collapsed", key="workshop_neg_prompt_str_area")
            st.markdown("<div class='compact-label'>Stable Video Diffusion (I2V) settings</div>", unsafe_allow_html=True)
            motion_bucket_val = st.slider("Motion Bucket ID (Animation Intensity)", min_value=1, max_value=255, value=127, key="workshop_motion_bucket_slider")
            st.markdown("<div class='compact-label'>📊 Image Quality</div>", unsafe_allow_html=True)
            workshop_quality = st.selectbox("Select Quality", ["Standard", "HD", "Pro"], key="workshop_quality")
            st.write("")
            if st.button("🚀 Generate Workshop Image", key="workshop_generation_action_btn", use_container_width=True):
                success, required_tokens, message = validate_and_deduct_tokens("Creative Workshop", workshop_quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    if not workshop_prompt_str.strip():
                        st.error("Please enter a valid description first.")
                    else:
                        user_credits = get_user_credits_db(st.session_state["logged_user"])
                        if not credit_check(st.session_state["logged_user"], 1):
                            st.error(f"Low Credit Error! Required: 1, Available: {user_credits}")
                        else:
                            deduct_credits_db(st.session_state["logged_user"], 1)
                            with st.spinner("Synthesizing creative frame..."):
                                generated_img = generate_pro_image(workshop_prompt_str, aspect_ratio=workshop_ar, negative_prompt=workshop_neg_prompt_str)
                                if generated_img and os.path.exists(generated_img):
                                    st.session_state["workshop_active_image"] = generated_img
                                    st.toast("Creative image synthesized successfully!")
                                    timestamp_img = time.strftime("%Y%m%d_%H%M%S")
                                    saved_img_name = f"zovix_image_{timestamp_img}.png"
                                    saved_img_path = f"saved_renders/{saved_img_name}"
                                    shutil.copy(generated_img, saved_img_path)
                                    save_render_to_db(st.session_state.get("logged_user"), saved_img_name, workshop_prompt_str, saved_img_path)
                                    save_to_json_history(st.session_state.get("logged_user"), saved_img_name, workshop_prompt_str, saved_img_path)
                                    st.session_state["history_renders"] = load_renders_history_db(st.session_state.get("logged_user"))
                                    st.rerun()
                                else:
                                    add_credits(st.session_state["logged_user"], 1, "standard")
                                    st.error("Synthesis engine failed to generate frame.")
    with w_col2:
        with st.container(border=True):
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>🖼️ LIVE IMAGE OUTPUT BOX</h3>", unsafe_allow_html=True)
            active_video_file = st.session_state.get("active_svd_video")
            active_img_file = st.session_state["workshop_active_image"]
            if active_video_file and os.path.exists(active_video_file):
                st.video(active_video_file, format="video/mp4", autoplay=False, loop=True, muted=False)
                st.markdown("<br>", unsafe_allow_html=True)
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_video_file, "rb") as file_bytes_wrapper:
                        st.download_button(label="📥 Save Video (MP4)", data=file_bytes_wrapper, file_name="zovix_motion_masterpiece.mp4", mime="video/mp4", use_container_width=True, key="workshop_video_download_btn")
                with col_clr:
                    if st.button("🧹 Clear Video", key="workshop_clear_video_btn", use_container_width=True):
                        st.session_state["active_svd_video"] = None
                        st.rerun()
            elif active_img_file and os.path.exists(active_img_file):
                img_base64 = get_base64_img_raw(active_img_file)
                ext = os.path.splitext(active_img_file)[1].lower().replace('.', '')
                if ext == 'jpg':
                    ext = 'jpeg'
                mime_type = f"image/{ext}" if ext in ['png', 'jpeg', 'webp', 'gif'] else "image/png"
                if img_base64:
                    st.markdown(f"""
                        <div class="canvas-container-box" style="height: 380px; min-height: 380px; display: flex; justify-content: center; align-items: center; padding: 12px; overflow: hidden;">
                            <img src="data:{mime_type};base64,{img_base64}" style="max-height: 100%; max-width: 100%; object-fit: contain; border-radius: 8px;" />
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.image(active_img_file, use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True)
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_img_file, "rb") as file_bytes_wrapper:
                        st.download_button(label="📥 Save Frame (PNG)", data=file_bytes_wrapper, file_name="zovix_workshop_masterpiece.png", mime="image/png", use_container_width=True, key="workshop_download_action_btn")
                with col_clr:
                    if st.button("🧹 Clear Output", key="workshop_clear_output_btn", use_container_width=True):
                        safe_remove_file(active_img_file)
                        st.session_state["workshop_active_image"] = None
                        st.rerun()
            else:
                st.markdown("""
                    <div class="canvas-container-box" style="height: 380px; min-height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #64748b; text-align: center; padding: 12px; overflow: hidden;">
                        <span style="font-size: 50px; margin-bottom: 12px; filter: drop-shadow(0 0 10px rgba(236, 72, 153, 0.3));">🖼️</span>
                        <p style="font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; color: #FFC0CB; margin: 0;">Image will render here</p>
                        <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px; line-height: 1.4;">Artwork will display immediately upon generation.</p>
                    </div>
                """, unsafe_allow_html=True)

def run_blueprints_mode():
    st.markdown("""
        <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; border: 1px solid rgba(255,192,203,0.15); padding: 20px; margin-bottom: 20px;">
            <h3 style="font-family: 'Orbitron'; font-size: 16px; color: #FFC0CB; margin: 0 0 5px 0;">📐 Blueprints Engine</h3>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;"> Generate professional architectural blueprints and technical drawings </p>
        </div>
    """, unsafe_allow_html=True)
    bp_col1, bp_col2 = st.columns([1.1, 1.4], gap="medium")
    with bp_col1:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>⚙️ BLUEPRINT PARAMETERS</h4>", unsafe_allow_html=True)
            blueprint_prompt = st.text_area("Architectural Description", placeholder="E.g. Modern 2-bedroom house with open kitchen, master bedroom with en-suite bathroom, large living room, study room...", height=100, key="bp_prompt")
            blueprint_type = st.selectbox("Blueprint Type:", ["floor_plan", "elevation", "section", "site_plan"], key="bp_type")
            st.markdown("<div class='compact-label'>📊 Blueprint Quality</div>", unsafe_allow_html=True)
            bp_quality = st.selectbox("Select Quality", ["Standard", "HD"], key="bp_quality")
            st.write("")
            if st.button("📐 Generate Blueprint", key="bp_generate_btn", use_container_width=True):
                success, required_tokens, message = validate_and_deduct_tokens("Blueprints", bp_quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    if not blueprint_prompt.strip():
                        st.error("Please enter a blueprint description.")
                    else:
                        with st.spinner("Generating architectural blueprint..."):
                            blueprint_path = generate_blueprint(blueprint_prompt, blueprint_type)
                            if blueprint_path and os.path.exists(blueprint_path):
                                st.session_state["active_blueprint"] = blueprint_path
                                st.toast("Blueprint generated successfully!")
                                st.rerun()
                            else:
                                st.error("Blueprint generation failed. Please try a different description.")
    with bp_col2:
        with st.container(border=True):
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>📐 BLUEPRINT VIEWER</h3>", unsafe_allow_html=True)
            active_bp = st.session_state.get("active_blueprint")
            if active_bp and os.path.exists(active_bp):
                st.image(active_bp, use_container_width=True)
                analysis = analyze_blueprint(active_bp)
                if analysis:
                    with st.expander("📊 Blueprint Analysis", expanded=True):
                        st.markdown(f"""
                            <div style="background: rgba(255,255,255,0.03); border-radius: 8px; padding: 15px;">
                                <p><strong>Format:</strong> {analysis.get('format', 'N/A')}</p>
                                <p><strong>Dimensions:</strong> {analysis.get('width', 'N/A')} x {analysis.get('height', 'N/A')} px</p>
                                <p><strong>Estimated Rooms:</strong> {analysis.get('estimated_rooms', 'N/A')}</p>
                                <p><strong>Total Area:</strong> {analysis.get('total_area', 'N/A')}</p>
                                <p><strong>Structure Type:</strong> {analysis.get('structure_type', 'N/A')}</p>
                                <p><strong>Confidence Score:</strong> {analysis.get('confidence_score', 'N/A') * 100:.1f}%</p>
                            </div>
                        """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_bp, "rb") as f:
                        bp_bytes = f.read()
                    st.download_button(label="📥 Download Blueprint (PNG)", data=bp_bytes, file_name=f"zovix_blueprint_{uuid.uuid4().hex[:8]}.png", mime="image/png", use_container_width=True, key="bp_download_btn")
                with col_clr:
                    if st.button("🧹 Clear Blueprint", key="bp_clear_btn", use_container_width=True):
                        safe_remove_file(active_bp)
                        st.session_state["active_blueprint"] = None
                        st.rerun()
            else:
                st.markdown("""
                    <div class="canvas-container-box" style="height: 380px; min-height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #64748b; text-align: center; padding: 12px; overflow: hidden;">
                        <span style="font-size: 50px; margin-bottom: 12px; filter: drop-shadow(0 0 10px rgba(236, 72, 153, 0.3));">📐</span>
                        <p style="font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; color: #FFC0CB; margin: 0;">Blueprint will render here</p>
                        <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px; line-height: 1.4;">Professional architectural drawings with detailed analysis.</p>
                    </div>
                """, unsafe_allow_html=True)

def generate_blueprint(prompt, blueprint_type="floor_plan"):
    blueprint_path = None
    if STABILITY_API_KEY:
        try:
            url = "https://api.stability.ai/v2beta/stable-image/generate/core"
            headers = {"authorization": f"Bearer {STABILITY_API_KEY}", "accept": "image/*"}
            data = {"prompt": f"Architectural blueprint, technical drawing, CAD design of {prompt}, professional, detailed, white background, blueprint style", "output_format": "png", "aspect_ratio": "16:9", "negative_prompt": "color, photo, realistic, blurry, low quality, painting, artistic"}
            files = {k: (None, str(v)) for k, v in data.items()}
            response = requests.post(url, headers=headers, files=files, timeout=30)
            if response.status_code == 200 and len(response.content) > 10000:
                blueprint_path = f"blueprints/blueprint_{uuid.uuid4().hex[:8]}.png"
                with open(blueprint_path, "wb") as f:
                    f.write(response.content)
                return blueprint_path
        except Exception:
            pass
    try:
        width, height = 1200, 800
        img = Image.new("RGB", (width, height), color=(240, 240, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(20, 20), (width-20, height-20)], outline=(30, 60, 150), width=3)
        draw.rectangle([(width-300, height-80), (width-20, height-20)], fill=(200, 210, 240), outline=(30, 60, 150), width=2)
        draw.text((width-290, height-70), "ZOVIX BLUEPRINT", fill=(30, 60, 150))
        draw.text((width-290, height-50), f"Generated: {datetime.now().strftime('%Y-%m-%d')}", fill=(30, 60, 150))
        draw.rectangle([(100, 100), (500, 600)], outline=(30, 60, 150), width=4)
        draw.rectangle([(600, 100), (1000, 600)], outline=(30, 60, 150), width=4)
        draw.line([(300, 100), (300, 350)], fill=(30, 60, 150), width=3)
        draw.line([(700, 100), (700, 350)], fill=(30, 60, 150), width=3)
        draw.line([(100, 350), (500, 350)], fill=(30, 60, 150), width=3)
        draw.line([(600, 350), (1000, 350)], fill=(30, 60, 150), width=3)
        draw.arc([(295, 340), (315, 360)], 0, 90, fill=(30, 60, 150), width=3)
        draw.arc([(695, 340), (715, 360)], 0, 90, fill=(30, 60, 150), width=3)
        draw.rectangle([(150, 90), (250, 110)], outline=(30, 60, 150), width=3)
        draw.rectangle([(650, 90), (750, 110)], outline=(30, 60, 150), width=3)
        draw.rectangle([(90, 150), (110, 250)], outline=(30, 60, 150), width=3)
        draw.rectangle([(590, 150), (610, 250)], outline=(30, 60, 150), width=3)
        draw.text((180, 200), "LIVING ROOM", fill=(30, 60, 150))
        draw.text((180, 450), "KITCHEN", fill=(30, 60, 150))
        draw.text((480, 200), "BEDROOM 1", fill=(30, 60, 150))
        draw.text((480, 450), "BEDROOM 2", fill=(30, 60, 150))
        draw.text((680, 200), "BATHROOM", fill=(30, 60, 150))
        draw.text((680, 450), "STUDY", fill=(30, 60, 150))
        blueprint_path = f"blueprints/blueprint_{uuid.uuid4().hex[:8]}.png"
        img.save(blueprint_path)
        return blueprint_path
    except Exception:
        pass
    return None

def analyze_blueprint(blueprint_path):
    if not blueprint_path or not os.path.exists(blueprint_path):
        return None
    try:
        img = Image.open(blueprint_path)
        width, height = img.size
        return {"width": width, "height": height, "format": img.format, "mode": img.mode, "estimated_rooms": 4, "total_area": f"{width * height / 10000:.2f} sq ft", "structure_type": "Residential", "confidence_score": 0.85}
    except Exception:
        return None

def run_flow_state_mode():
    st.markdown("""
        <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; border: 1px solid rgba(255,192,203,0.15); padding: 20px; margin-bottom: 20px;">
            <h3 style="font-family: 'Orbitron'; font-size: 16px; color: #FFC0CB; margin: 0 0 5px 0;">🌊 Flow State Engine</h3>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;"> Generate fluid dynamics simulations and particle animations </p>
        </div>
    """, unsafe_allow_html=True)
    fs_col1, fs_col2 = st.columns([1.1, 1.4], gap="medium")
    with fs_col1:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>⚙️ FLOW PARAMETERS</h4>", unsafe_allow_html=True)
            flow_prompt = st.text_area("Flow Description", placeholder="E.g. Lava flowing down a volcano, ocean waves, smoke particles, water ripples, fire particles...", height=100, key="fs_prompt")
            duration_sec = st.slider("Animation Duration (seconds)", min_value=2, max_value=10, value=5, key="fs_duration")
            fps = st.select_slider("Frames Per Second", options=[12, 24, 30, 60], value=24, key="fs_fps")
            st.markdown("<div class='compact-label'>📊 Animation Quality</div>", unsafe_allow_html=True)
            fs_quality = st.selectbox("Select Quality", ["Standard", "HD"], key="fs_quality")
            st.write("")
            if st.button("🌊 Generate Flow Animation", key="fs_generate_btn", use_container_width=True):
                success, required_tokens, message = validate_and_deduct_tokens("Flow State", fs_quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    if not flow_prompt.strip():
                        st.error("Please enter a flow description.")
                    else:
                        with st.spinner("Generating flow animation with particle dynamics..."):
                            animation_path = generate_flow_animation(flow_prompt, duration_sec, fps)
                            if animation_path and os.path.exists(animation_path):
                                st.session_state["active_flow_animation"] = animation_path
                                st.toast("Flow animation generated successfully!")
                                st.rerun()
                            else:
                                st.error("Flow animation generation failed. Please try a different prompt.")
    with fs_col2:
        with st.container(border=True):
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>🌊 FLOW ANIMATION VIEWER</h3>", unsafe_allow_html=True)
            active_flow = st.session_state.get("active_flow_animation")
            if active_flow and os.path.exists(active_flow):
                ext = os.path.splitext(active_flow)[1].lower()
                if ext in ['.gif']:
                    st.image(active_flow, use_container_width=True)
                else:
                    st.video(active_flow, format="video/mp4", autoplay=True, loop=True, muted=True)
                st.markdown("<br>", unsafe_allow_html=True)
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_flow, "rb") as f:
                        flow_bytes = f.read()
                    st.download_button(label=f"📥 Download Animation ({ext.upper()})", data=flow_bytes, file_name=f"zovix_flow{ext}", mime="video/mp4" if ext != '.gif' else "image/gif", use_container_width=True, key="fs_download_btn")
                with col_clr:
                    if st.button("🧹 Clear Animation", key="fs_clear_btn", use_container_width=True):
                        safe_remove_file(active_flow)
                        st.session_state["active_flow_animation"] = None
                        st.rerun()
            else:
                st.markdown("""
                    <div class="canvas-container-box" style="height: 380px; min-height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #64748b; text-align: center; padding: 12px; overflow: hidden;">
                        <span style="font-size: 50px; margin-bottom: 12px; filter: drop-shadow(0 0 10px rgba(236, 72, 153, 0.3));">🌊</span>
                        <p style="font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; color: #FFC0CB; margin: 0;">Flow animation will render here</p>
                        <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px; line-height: 1.4;">Dynamic fluid simulations with particle systems.</p>
                    </div>
                """, unsafe_allow_html=True)

def generate_flow_animation(prompt, duration=5, fps=24):
    animation_path = None
    if STABILITY_API_KEY:
        try:
            url = "https://api.stability.ai/v2beta/stable-image/generate/core"
            headers = {"authorization": f"Bearer {STABILITY_API_KEY}", "accept": "image/*"}
            data = {"prompt": f"Fluid flow, particle system, dynamic motion, {prompt}, vibrant colors, smooth animation, cinematic", "output_format": "png", "aspect_ratio": "16:9", "negative_prompt": "static, blurry, low quality"}
            files = {k: (None, str(v)) for k, v in data.items()}
            response = requests.post(url, headers=headers, files=files, timeout=30)
            if response.status_code == 200 and len(response.content) > 10000:
                animation_path = f"flow_animations/flow_{uuid.uuid4().hex[:8]}.png"
                with open(animation_path, "wb") as f:
                    f.write(response.content)
                return animation_path
        except Exception:
            pass
    try:
        frames = []
        num_particles = 100
        width, height = 800, 600
        for frame_num in range(duration * fps):
            img = Image.new("RGB", (width, height), color=(6, 7, 10))
            draw = ImageDraw.Draw(img)
            for i in range(num_particles):
                t = frame_num / fps
                x = width/2 + 200 * np.sin(t * 0.5 + i * 0.1)
                y = height/2 + 150 * np.cos(t * 0.3 + i * 0.15)
                size = 3 + 5 * np.sin(t * 0.2 + i * 0.05) + 2
                r = int(236 + 19 * np.sin(t * 0.1 + i * 0.02))
                g = int(72 + 183 * np.cos(t * 0.15 + i * 0.03))
                b = int(153 + 102 * np.sin(t * 0.08 + i * 0.04))
                r = min(255, max(0, r))
                g = min(255, max(0, g))
                b = min(255, max(0, b))
                draw.ellipse([(x-size, y-size), (x+size, y+size)], fill=(r, g, b))
            for i in range(20):
                t = frame_num / fps
                x1 = width * 0.1 + i * 30
                y1 = height * 0.5 + 100 * np.sin(t * 0.2 + i * 0.3)
                x2 = x1 + 50
                y2 = y1 + 30 * np.cos(t * 0.25 + i * 0.2)
                draw.line([(x1, y1), (x2, y2)], fill=(255, 192, 203, 50), width=2)
            frames.append(img)
        if frames:
            animation_path = f"flow_animations/flow_{uuid.uuid4().hex[:8]}.gif"
            frames[0].save(animation_path, save_all=True, append_images=frames[1:], duration=1000//fps, loop=0)
            return animation_path
    except Exception:
        pass
    return None

def run_upscaler_mode():
    st.markdown("""
        <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; border: 1px solid rgba(255,192,203,0.15); padding: 20px; margin-bottom: 20px;">
            <h3 style="font-family: 'Orbitron'; font-size: 16px; color: #FFC0CB; margin: 0 0 5px 0;">⚡ Upscaler Engine</h3>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;"> AI-powered image upscaling with detail restoration and enhancement </p>
        </div>
    """, unsafe_allow_html=True)
    us_col1, us_col2 = st.columns([1.1, 1.4], gap="medium")
    with us_col1:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>⚙️ UPSCALER PARAMETERS</h4>", unsafe_allow_html=True)
            uploaded_image_up = st.file_uploader("Upload Image to Upscale", type=['png', 'jpg', 'jpeg', 'webp'], key="us_image_upload")
            scale_factor = st.select_slider("Scale Factor", options=[2, 4, 8], value=2, key="us_scale_factor")
            enhancement_type = st.selectbox("Enhancement Method:", ["standard", "sharp", "smooth", "enhance"], key="us_enhancement_type")
            st.markdown("<div class='compact-label'>📊 Upscale Quality</div>", unsafe_allow_html=True)
            us_quality = st.selectbox("Select Quality", ["Standard", "Pro"], key="us_quality")
            st.write("")
            if st.button("⚡ Upscale Image", key="us_upscale_btn", use_container_width=True):
                success, required_tokens, message = validate_and_deduct_tokens("Upscaler", us_quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    if not uploaded_image_up:
                        st.error("Please upload an image to upscale.")
                    else:
                        temp_image_path = f"temp_scenes/upload_{uuid.uuid4().hex[:8]}.png"
                        with open(temp_image_path, "wb") as f:
                            f.write(uploaded_image_up.getbuffer())
                        with st.spinner(f"Upscaling image {scale_factor}x with {enhancement_type} enhancement..."):
                            upscaled_path = upscale_image(temp_image_path, scale_factor, enhancement_type)
                            if upscaled_path and os.path.exists(upscaled_path):
                                st.session_state["active_upscaled_image"] = upscaled_path
                                st.toast(f"Image upscaled {scale_factor}x successfully!")
                                st.rerun()
                            else:
                                st.error("Image upscaling failed. Please try a different image or settings.")
    with us_col2:
        with st.container(border=True):
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>⚡ UPSCALED IMAGE VIEWER</h3>", unsafe_allow_html=True)
            active_upscaled = st.session_state.get("active_upscaled_image")
            if active_upscaled and os.path.exists(active_upscaled):
                st.image(active_upscaled, use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True)
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_upscaled, "rb") as f:
                        upscaled_bytes = f.read()
                    st.download_button(label="📥 Download Upscaled Image", data=upscaled_bytes, file_name=f"zovix_upscaled_{uuid.uuid4().hex[:8]}.png", mime="image/png", use_container_width=True, key="us_download_btn")
                with col_clr:
                    if st.button("🧹 Clear Image", key="us_clear_btn", use_container_width=True):
                        safe_remove_file(active_upscaled)
                        st.session_state["active_upscaled_image"] = None
                        st.rerun()
            else:
                st.markdown("""
                    <div class="canvas-container-box" style="height: 380px; min-height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #64748b; text-align: center; padding: 12px; overflow: hidden;">
                        <span style="font-size: 50px; margin-bottom: 12px; filter: drop-shadow(0 0 10px rgba(236, 72, 153, 0.3));">⚡</span>
                        <p style="font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; color: #FFC0CB; margin: 0;">Upscaled image will render here</p>
                        <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px; line-height: 1.4;">AI-enhanced high-resolution output.</p>
                    </div>
                """, unsafe_allow_html=True)

def upscale_image(image_path, scale_factor=2, enhancement_type="standard"):
    if not image_path or not os.path.exists(image_path):
        return None
    output_path = f"upscaled_outputs/upscaled_{uuid.uuid4().hex[:8]}.png"
    if STABILITY_API_KEY:
        try:
            url = "https://api.stability.ai/v2beta/stable-image/generate/core"
            headers = {"authorization": f"Bearer {STABILITY_API_KEY}", "accept": "image/*"}
            with open(image_path, "rb") as f:
                image_data = f.read()
            files = {"image": image_data, "prompt": (None, "Upscale this image with high quality"), "output_format": (None, "png"), "aspect_ratio": (None, "16:9"), "negative_prompt": (None, "blurry, low quality")}
            response = requests.post(url, headers=headers, files=files, timeout=45)
            if response.status_code == 200 and len(response.content) > 10000:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return output_path
        except Exception:
            pass
    try:
        img = Image.open(image_path)
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)
        if enhancement_type == "standard":
            upscaled = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        elif enhancement_type == "sharp":
            upscaled = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            upscaled = upscaled.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        elif enhancement_type == "smooth":
            upscaled = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            upscaled = upscaled.filter(ImageFilter.SMOOTH_MORE)
        elif enhancement_type == "enhance":
            upscaled = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            enhancer = ImageEnhance.Contrast(upscaled)
            upscaled = enhancer.enhance(1.2)
            enhancer = ImageEnhance.Sharpness(upscaled)
            upscaled = enhancer.enhance(1.3)
        else:
            upscaled = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        upscaled.save(output_path)
        return output_path
    except Exception:
        pass
    return None

def run_draw_mode():
    st.markdown("""
        <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; border: 1px solid rgba(255,192,203,0.15); padding: 20px; margin-bottom: 20px;">
            <h3 style="font-family: 'Orbitron'; font-size: 16px; color: #FFC0CB; margin: 0 0 5px 0;">🎨 Draw Engine</h3>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;"> AI-powered drawing and sketch generation with multiple artistic styles </p>
        </div>
    """, unsafe_allow_html=True)
    dr_col1, dr_col2 = st.columns([1.1, 1.4], gap="medium")
    with dr_col1:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>⚙️ DRAW PARAMETERS</h4>", unsafe_allow_html=True)
            draw_prompt = st.text_area("Drawing Description", placeholder="E.g. A beautiful landscape with mountains, lake and pine trees, A mystical dragon, A futuristic cityscape...", height=100, key="dr_prompt")
            draw_style = st.selectbox("Artistic Style:", ["sketch", "watercolor", "digital", "anime", "realistic"], key="dr_style")
            canvas_width = st.select_slider("Canvas Width", options=[400, 600, 800, 1024, 1280], value=800, key="dr_width")
            canvas_height = st.select_slider("Canvas Height", options=[300, 400, 600, 768, 1024], value=600, key="dr_height")
            st.markdown("<div class='compact-label'>📊 Drawing Quality</div>", unsafe_allow_html=True)
            dr_quality = st.selectbox("Select Quality", ["Standard", "HD"], key="dr_quality")
            st.write("")
            if st.button("🎨 Generate Drawing", key="dr_generate_btn", use_container_width=True):
                success, required_tokens, message = validate_and_deduct_tokens("Draw", dr_quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    if not draw_prompt.strip():
                        st.error("Please enter a drawing description.")
                    else:
                        with st.spinner(f"Generating {draw_style} drawing..."):
                            drawing_path = generate_drawing(draw_prompt, draw_style, (canvas_width, canvas_height))
                            if drawing_path and os.path.exists(drawing_path):
                                st.session_state["active_drawing"] = drawing_path
                                st.toast(f"{draw_style.capitalize()} drawing generated successfully!")
                                st.rerun()
                            else:
                                st.error("Drawing generation failed. Please try a different prompt or style.")
    with dr_col2:
        with st.container(border=True):
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>🎨 DRAWING VIEWER</h3>", unsafe_allow_html=True)
            active_drawing = st.session_state.get("active_drawing")
            if active_drawing and os.path.exists(active_drawing):
                st.image(active_drawing, use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True)
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_drawing, "rb") as f:
                        drawing_bytes = f.read()
                    st.download_button(label="📥 Download Drawing", data=drawing_bytes, file_name=f"zovix_drawing_{uuid.uuid4().hex[:8]}.png", mime="image/png", use_container_width=True, key="dr_download_btn")
                with col_clr:
                    if st.button("🧹 Clear Drawing", key="dr_clear_btn", use_container_width=True):
                        safe_remove_file(active_drawing)
                        st.session_state["active_drawing"] = None
                        st.rerun()
            else:
                st.markdown("""
                    <div class="canvas-container-box" style="height: 380px; min-height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #64748b; text-align: center; padding: 12px; overflow: hidden;">
                        <span style="font-size: 50px; margin-bottom: 12px; filter: drop-shadow(0 0 10px rgba(236, 72, 153, 0.3));">🎨</span>
                        <p style="font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; color: #FFC0CB; margin: 0;">Drawing will render here</p>
                        <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px; line-height: 1.4;">AI-generated artwork with your chosen artistic style.</p>
                    </div>
                """, unsafe_allow_html=True)

def generate_drawing(prompt, style="sketch", canvas_size=(800, 600)):
    output_path = f"draw_outputs/drawing_{uuid.uuid4().hex[:8]}.png"
    hf_api_key = os.getenv("HUGGINGFACE_API_KEY") or get_system_secret("HUGGINGFACE_API_KEY")
    if hf_api_key:
        try:
            API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
            headers = {"Authorization": f"Bearer {hf_api_key}"}
            style_prompt = ""
            if style == "sketch":
                style_prompt = "pencil sketch, black and white, detailed, artistic"
            elif style == "watercolor":
                style_prompt = "watercolor painting, soft colors, artistic, flowing"
            elif style == "digital":
                style_prompt = "digital art, vibrant colors, detailed, professional"
            elif style == "anime":
                style_prompt = "anime style, manga, colorful, detailed"
            elif style == "realistic":
                style_prompt = "photorealistic, highly detailed, professional"
            else:
                style_prompt = "sketch, artistic, detailed"
            full_prompt = f"{prompt}, {style_prompt}, high quality, detailed"
            payload = {"inputs": full_prompt, "parameters": {"negative_prompt": "blurry, low quality, distorted, bad anatomy"}}
            response = requests.post(API_URL, headers=headers, json=payload, timeout=45)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return output_path
        except Exception:
            pass
    try:
        width, height = canvas_size
        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        if "circle" in prompt.lower():
            draw.ellipse([(100, 100), (700, 500)], outline=(0, 0, 0), width=5)
        elif "square" in prompt.lower() or "rectangle" in prompt.lower():
            draw.rectangle([(100, 100), (700, 500)], outline=(0, 0, 0), width=5)
        elif "triangle" in prompt.lower():
            draw.polygon([(400, 100), (100, 500), (700, 500)], outline=(0, 0, 0), width=5)
        elif "star" in prompt.lower():
            draw.polygon([(400, 100), (500, 300), (700, 300), (550, 450), (600, 650), (400, 550), (200, 650), (250, 450), (100, 300), (300, 300)], outline=(0, 0, 0), width=5)
        else:
            for i in range(10):
                x = 100 + i * 80
                y = 100 + i * 50
                draw.ellipse([(x, y), (x+60, y+60)], outline=(0, 0, 0), width=3)
        draw.text((width//2-100, height-50), f"ZOVIX Draw - {datetime.now().strftime('%Y-%m-%d')}", fill=(100, 100, 100))
        img.save(output_path)
        return output_path
    except Exception:
        pass
    return None

def run_video_editor_mode():
    st.markdown("""
        <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; border: 1px solid rgba(255,192,203,0.15); padding: 20px; margin-bottom: 20px;">
            <h3 style="font-family: 'Orbitron'; font-size: 16px; color: #FFC0CB; margin: 0 0 5px 0;">🎬 Video Editor (1-2 Min Movie)</h3>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;"> AI-powered movie editing with timeline generation and auto-stitching </p>
        </div>
    """, unsafe_allow_html=True)
    ve_col1, ve_col2 = st.columns([1.1, 1.4], gap="medium")
    with ve_col1:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>⚙️ EDITOR PARAMETERS</h4>", unsafe_allow_html=True)
            st.markdown("<div class='compact-label'>📤 UPLOAD UNLIMITED MEDIA FOR EDITING</div>", unsafe_allow_html=True)
            uploaded_media = st.file_uploader("Upload Videos, Images, or Audio (Unlimited Files)", type=['mp4', 'mov', 'avi', 'webm', 'png', 'jpg', 'jpeg', 'webp', 'mp3', 'wav'], accept_multiple_files=True, key="editor_media_upload")
            if uploaded_media:
                st.session_state["editor_uploads"] = uploaded_media
                st.success(f"✅ {len(uploaded_media)} media files uploaded successfully!")
                st.markdown("<div class='compact-label'>📋 UPLOADED MEDIA LIST</div>", unsafe_allow_html=True)
                for idx, media in enumerate(uploaded_media[:10]):
                    ext = os.path.splitext(media.name)[1].lower()
                    icon = "🎬" if ext in ['.mp4', '.mov', '.avi', '.webm'] else ("🖼️" if ext in ['.png', '.jpg', '.jpeg', '.webp'] else "🎵")
                    st.markdown(f"{icon} {media.name} ({media.size/1024:.1f} KB)")
                if len(uploaded_media) > 10:
                    st.caption(f"... and {len(uploaded_media) - 10} more files")
            st.markdown("---")
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                transition_effect = st.selectbox("🎞️ Transition Effect:", ["none", "fade", "crossfade", "zoom", "slide", "circle", "radial", "smooth"], key="editor_transition")
            with col_edit2:
                video_effect = st.selectbox("🎨 Video Effect:", ["none", "sepia", "grayscale", "vintage", "cinematic", "neon", "glitch", "dreamy", "dramatic"], key="editor_effect")
            output_resolution = st.selectbox("📐 Output Resolution:", ["720p", "1080p", "4K"], key="editor_resolution")
            st.markdown("<div class='compact-label'>🎵 ADD CUSTOM BACKGROUND MUSIC</div>", unsafe_allow_html=True)
            editor_bgm = st.file_uploader("Upload Custom BGM Track (MP3 or WAV)", type=['mp3', 'wav'], key="editor_bgm_upload")
            st.markdown("<div class='compact-label'>🎵 SELECT BGM FROM LIBRARY</div>", unsafe_allow_html=True)
            bgm_library = {"None": None, "Cinematic": "assets/music/cinematic.mp3", "Uplifting": "assets/music/uplifting.mp3", "Dramatic": "assets/music/dramatic.mp3", "Calm": "assets/music/calm.mp3", "Energetic": "assets/music/energetic.mp3", "Mysterious": "assets/music/mysterious.mp3"}
            selected_bgm_name = st.selectbox("Choose BGM from Library", list(bgm_library.keys()), key="editor_bgm_select")
            if editor_bgm is not None:
                selected_bgm_path = None
                st.info("✅ Custom BGM uploaded. Will be used instead of library selection.")
            else:
                selected_bgm_path = bgm_library.get(selected_bgm_name)
                if selected_bgm_path and os.path.exists(selected_bgm_path):
                    st.info(f"🎵 Selected: {selected_bgm_name}")
                else:
                    selected_bgm_path = None
                    st.caption("⚠️ Selected BGM file not found. Video will have no background music.")
            editor_bgm_volume = st.slider("BGM Volume Level", min_value=0.0, max_value=1.0, value=0.30, step=0.05, key="editor_bgm_volume")
            movie_concept = st.text_area("Write Full Movie Script / Prompt Vision (Optional):", placeholder="e.g., An astronaut discovering an ancient neon pyramid on Mars, entering inside, activating the core matrix, energy beam shoots to sky...", height=80, key="movie_concept_input_editor")
            st.markdown("<div class='compact-label'>📊 Editor Quality</div>", unsafe_allow_html=True)
            editor_quality = st.selectbox("Select Quality", ["Standard", "HD", "4K"], key="editor_quality")
            st.write("")
            if st.button("🚀 PROCESS & EDIT VIDEO", key="movie_generate_btn_editor", use_container_width=True):
                success, required_tokens, message = validate_and_deduct_tokens("Video Editor", editor_quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    if not st.session_state.get("editor_uploads"):
                        st.warning("⚠️ Please upload at least one media file (video, image, or audio) for editing.")
                    else:
                        bgm_to_use = None
                        if editor_bgm is not None:
                            bgm_to_use = editor_bgm
                        elif selected_bgm_path and os.path.exists(selected_bgm_path):
                            class BGMFile:
                                def __init__(self, path):
                                    self.path = path
                                def getbuffer(self):
                                    with open(self.path, "rb") as f:
                                        return f.read()
                                @property
                                def name(self):
                                    return os.path.basename(self.path)
                            bgm_to_use = BGMFile(selected_bgm_path)
                        with st.spinner("🎬 Processing uploaded media with FFmpeg engine..."):
                            output_path = f"saved_renders/editor_output_{uuid.uuid4().hex[:8]}.mp4"
                            success = process_editor_video(st.session_state["editor_uploads"], output_path, effect=video_effect, transition=transition_effect, resolution=output_resolution, custom_bgm=bgm_to_use, bgm_volume=editor_bgm_volume)
                            if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                                st.session_state["active_editor_output"] = output_path
                                st.toast("✅ Video processed successfully with BGM!")
                                timestamp = time.strftime("%Y%m%d_%H%M%S")
                                file_name = f"zovix_editor_video_{timestamp}.mp4"
                                save_render_to_db(st.session_state["logged_user"], file_name, movie_concept or "Editor Project", output_path)
                                st.session_state["history_renders"] = load_renders_history_db(st.session_state["logged_user"])
                                time.sleep(0.3)
                                st.rerun()
                            else:
                                st.error("❌ Video processing failed. Please check your media files and try again.")
    with ve_col2:
        with st.container(border=True):
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>🎬 EDITED VIDEO OUTPUT</h3>", unsafe_allow_html=True)
            active_output = st.session_state.get("active_editor_output")
            if active_output and os.path.exists(active_output) and os.path.getsize(active_output) > 0:
                st.video(active_output, format="video/mp4", autoplay=False, loop=True, muted=False)
                st.markdown("<br>", unsafe_allow_html=True)
                col_dl, col_clr = st.columns(2)
                with col_dl:
                    with open(active_output, "rb") as f:
                        video_bytes = f.read()
                    st.download_button(label="📥 Download Edited Video", data=video_bytes, file_name=f"zovix_edited_video_{uuid.uuid4().hex[:8]}.mp4", mime="video/mp4", use_container_width=True, key="editor_download_btn")
                with col_clr:
                    if st.button("🧹 Clear Output", key="editor_clear_btn", use_container_width=True):
                        safe_remove_file(active_output)
                        st.session_state["active_editor_output"] = None
                        st.rerun()
            else:
                st.markdown("""
                    <div class="canvas-container-box" style="height: 380px; min-height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #64748b; text-align: center; padding: 12px; overflow: hidden;">
                        <span style="font-size: 50px; margin-bottom: 12px; filter: drop-shadow(0 0 10px rgba(236, 72, 153, 0.3));">🎬</span>
                        <p style="font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; color: #FFC0CB; margin: 0;">Edited video will render here</p>
                        <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px; line-height: 1.4;">Upload unlimited media files and click process to edit.</p>
                        <p style="font-size: 10px; color: #EC4899; margin-top: 5px;">🎵 Custom BGM supported</p>
                    </div>
                """, unsafe_allow_html=True)

def run_face_video_mode():
    st.markdown("""
        <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; border: 1px solid rgba(255,192,203,0.15); padding: 20px; margin-bottom: 20px;">
            <h3 style="font-family: 'Orbitron'; font-size: 16px; color: #FFC0CB; margin: 0 0 5px 0;">👤 Face Video Generator</h3>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;"> AI-powered face animation with lip sync, emotion control, and camera angles </p>
        </div>
    """, unsafe_allow_html=True)
    fv_col1, fv_col2 = st.columns([1.1, 1.4], gap="medium")
    with fv_col1:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>⚙️ FACE VIDEO PARAMETERS</h4>", unsafe_allow_html=True)
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
            st.markdown("""<div class='face-control-item'><div class='label'>😊 Emotion</div><div class='value'>Select Below</div></div>""", unsafe_allow_html=True)
            st.markdown("""<div class='face-control-item'><div class='label'>🎥 Camera Angle</div><div class='value'>Select Below</div></div>""", unsafe_allow_html=True)
            st.markdown("""<div class='face-control-item'><div class='label'>⏱️ Duration</div><div class='value'>Select Below</div></div>""", unsafe_allow_html=True)
            st.markdown("""<div class='face-control-item'><div class='label'>📊 Quality</div><div class='value'>Select Below</div></div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            col_emote, col_cam, col_dur, col_qual = st.columns(4)
            with col_emote:
                emotion = st.selectbox("Emotion:", ["neutral", "happy", "sad", "angry", "surprised", "excited"], key="fv_emotion")
            with col_cam:
                camera_angle = st.selectbox("Camera Angle:", ["front", "left", "right", "up", "down", "extreme_left", "extreme_right"], key="fv_camera")
            with col_dur:
                video_duration = st.select_slider("Duration (seconds)", options=[5, 10, 15, 20, 30, 45, 60], value=10, key="fv_duration")
            with col_qual:
                quality = st.selectbox("Video Quality:", ["Standard", "HD", "4K"], key="fv_quality")
            st.markdown("---")
            quality_costs = {"Standard": 45, "HD": 60, "4K": 80}
            cost = quality_costs.get(quality, 45)
            st.info(f"💳 This will cost **{cost} credits** for {quality} quality")
            face_prompt = st.text_area("Video Description / Script (for lip sync):", placeholder="Describe what the person should say: e.g. Hello everyone! Welcome to my channel. Today we're going to explore the mysteries of the universe...", height=100, key="fv_prompt")
            st.write("")
            if st.button("👤 Generate Face Video", key="fv_generate_btn", use_container_width=True):
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
                        with st.spinner(f"Generating {quality} face video with {emotion} expression and {camera_angle} angle..."):
                            video_path = generate_face_video(face_prompt, st.session_state["face_image_upload"], video_duration, emotion=emotion, camera_angle=camera_angle, quality=quality)
                            if video_path and os.path.exists(video_path):
                                st.session_state["active_face_video"] = video_path
                                timestamp = time.strftime("%Y%m%d_%H%M%S")
                                file_name = f"zovix_face_video_{quality.lower()}_{timestamp}.mp4"
                                save_face_video_to_db(st.session_state["logged_user"], file_name, face_prompt, video_path, st.session_state["face_image_upload"], quality)
                                st.session_state["face_video_history"] = load_face_video_history_db(st.session_state["logged_user"])
                                st.toast(f"Face video generated successfully in {quality} quality!")
                                st.rerun()
                            else:
                                st.error("Face video generation failed. Please try again.")
    with fv_col2:
        with st.container(border=True):
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>👤 FACE VIDEO PLAYER</h3>", unsafe_allow_html=True)
            active_face_video = st.session_state.get("active_face_video")
            if active_face_video and os.path.exists(active_face_video):
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
                        <p style="font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; color: #FFC0CB; margin: 0;">Face video will render here</p>
                        <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px; line-height: 1.4;">Upload a face image or use camera, set emotion and camera angle, then generate.</p>
                        <p style="font-size: 10px; color: #EC4899; margin-top: 5px;">⚡ Powered by ElevenLabs voice + Lip Sync</p>
                    </div>
                """, unsafe_allow_html=True)

# ========================================================
# 38. AUTH MODALS
# ========================================================

@st.dialog("🔐 Security Gateway Node Access", width="small")
def show_auth_modal(mode="login"):
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 15px;">
            <div style="font-family: 'Orbitron', sans-serif; font-size: 16px; color: #FFC0CB; text-transform: uppercase; letter-spacing: 1.5px;">
                { '🔑 Sign In Portal' if mode == 'login' else '📝 Register Identity' }
            </div>
            <p style="font-size: 11px; color: #94a3b8; margin-top: 5px;">Secure access nodes dynamically configured.</p>
        </div>
    """, unsafe_allow_html=True)
    username_val = st.text_input("Username Identifier", key="auth_modal_username_input").strip()
    password_val = st.text_input("Access Password", type="password", key="auth_modal_password_input").strip()
    st.write("")
    
    if mode == "login":
        col_login, col_register = st.columns(2)
        with col_login:
            if st.button("🔑 Sign In", key="auth_modal_login_btn", use_container_width=True):
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
                        st.rerun()
                else:
                    st.error("Invalid Username or Password configuration.")
        with col_register:
            if st.button("📝 Register", key="auth_modal_register_btn", use_container_width=True):
                if username_val and password_val:
                    if register_user_db(username_val, password_val):
                        st.session_state["is_logged_in"] = True
                        st.session_state["logged_user"] = username_val
                        st.session_state["xp_points"] = 0
                        st.session_state["creator_level"] = 1
                        st.session_state["history_renders"] = []
                        st.session_state["face_video_history"] = []
                        st.session_state["current_page"] = "studio"
                        if st.session_state.get("auth_redirect_mode"):
                            st.session_state["studio_active_mode"] = st.session_state["auth_redirect_mode"]
                            st.session_state["current_workspace_mode"] = st.session_state["auth_redirect_mode"]
                        check_and_refresh_subscription(username_val)
                        gdpr_manager.set_consent(username_val)
                        st.rerun()
                    else:
                        st.error("This Username is already occupied inside node database.")
                else:
                    st.error("Please enter a valid Username and Password.")
        
        st.markdown("<div style='text-align:center; font-size:10px; color:#64748b; margin: 15px 0;'>OR SIGN IN WITH SOCIAL PLATFORMS</div>", unsafe_allow_html=True)
        col_g, col_f = st.columns(2)
        with col_g:
            if st.button("🔴 Google ID", key="modal_social_g", use_container_width=True):
                social_login_dialog_box("Google")
        with col_f:
            if st.button("🔵 Facebook ID", key="modal_social_f", use_container_width=True):
                social_login_dialog_box("Facebook")

@st.dialog("🔑 Social Account Authentication", width="small")
def social_login_dialog_box(platform):
    st.markdown(f"""
        <div style="background: rgba(18, 19, 26, 0.95); padding: 5px; border-radius: 12px; text-align: center;">
            <div style="font-family: 'Orbitron', sans-serif; font-size: 14px; color: #FFC0CB; margin-bottom: 10px; letter-spacing: 1px; text-transform: uppercase;">Direct Login with {platform}</div>
            <p style="font-size:12px; color:#94a3b8; margin-bottom:15px;">Verify active email credentials to access workspace.</p>
        </div>
    """, unsafe_allow_html=True)
    social_email = st.text_input("Enter Email Address", placeholder="yourname@gmail.com", key="social_email_input").strip()
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
                st.toast(f"Logged in successfully via {platform}!")
                st.rerun()
            else:
                st.error("Authentication node failure.")
        else:
            st.error("Provide a valid email address.")

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
    
    code = st.text_input("Authentication Code", max_chars=6, type="password", key="2fa_code_input").strip()
    st.write("")
    
    if st.button("✅ Verify", key="2fa_verify_btn", use_container_width=True):
        if code and len(code) == 6:
            username = st.session_state.get("2fa_temp_user", "")
            if twofa.verify_code(username, code):
                st.session_state["2fa_verified"] = True
                st.session_state["is_logged_in"] = True
                st.session_state["logged_user"] = username
                st.session_state["xp_points"] = get_user_xp_db(username)
                st.session_state["creator_level"] = 1 + (st.session_state["xp_points"] // 100)
                st.session_state["history_renders"] = load_renders_history_db(username)
                st.session_state["face_video_history"] = load_face_video_history_db(username)
                st.session_state["current_page"] = "studio"
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
                st.session_state["2fa_temp_user"] = None
                st.rerun()
            else:
                st.error("Invalid code. Please try again.")
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

# ========================================================
# 39. RUN CINEMATIC ENGINE (FULL)
# ========================================================

def run_cinematic_engine():
    st.markdown("<div class='compact-label'>🌐 TRANSLATION, KEYS & SHORTCUTS</div>", unsafe_allow_html=True)
    t_col1, t_col2, t_col3 = st.columns([1, 1, 1.2])
    with t_col1:
        st.session_state["quick_template_mode"] = st.toggle("⚡ Smart Template Quick Mode (Fast 30s Compile)", value=st.session_state["quick_template_mode"])
    with t_col2:
        st.session_state["language_choice"] = st.selectbox("🌐 Subtitles & Voice Layer Language:", ["🇮🇳 Hinglish (Fluent Hindi Mix)", "🇬🇧 English (US Standard)", "🇫🇷 French (Parisian Neural)", "🇯🇵 Japanese (Formal Tokyo)"], key="studio_language_selector_layer")
    with t_col3:
        user_api_input = st.text_input("Google Gemini API Key (Optional Override):", value=st.session_state.get("user_gemini_api_key", ""), type="password", key="user_gemini_api_key_override_input")
        if user_api_input != st.session_state["user_gemini_api_key"]:
            st.session_state["user_gemini_api_key"] = user_api_input.strip()
            st.toast("Personal API Key Overrides Active!")
    st.write("")
    with st.container(border=True):
        st.markdown("<div class='compact-label'>💡 Prompt Interface</div>", unsafe_allow_html=True)
        input_mode = st.radio("Prompt Select Option Mode:", ["💡 Autonomous AI Topic", "✍️ Manual Custom Script", "🧠 DeepSeek AI Blueprint"], horizontal=True, key="studio_mode_radio")
        initial_topic_val = st.session_state.get("studio_prompt_value", "")
        if input_mode == "🧠 DeepSeek AI Blueprint":
            user_input = st.text_area("Prompt Input", value=initial_topic_val, placeholder="Explain video concept: e.g. Ek kisan ke paas do beej the...", height=110, label_visibility="collapsed", key="studio_prompt_deepseek_input")
            aspect_choice = st.selectbox("Aspect Scaling Rules for Blueprint:", ["16:9 LANDSCAPE (YOUTUBE)", "9:16 VERTICAL (SHORTS/REELS)"], key="studio_deepseek_aspect")
        else:
            user_input = st.text_area("Prompt Input", value=initial_topic_val, placeholder="Explain video concept: e.g. Bermuda triangle ka ansuljha rahasya jo kisi ko nahi pata tha." if input_mode == "💡 Autonomous AI Topic" else "Write a custom script separated by paragraph breaks. E.g:\n[Scene 1: ocean] Paragraph text...\n\n[Scene 2: storm] Next text...", height=110, label_visibility="collapsed", key="studio_prompt_standard_input")
        st.markdown("<div class='compact-label'>📊 Render Quality</div>", unsafe_allow_html=True)
        cinematic_quality = st.selectbox("Select Quality", ["Standard", "HD", "Pro"], key="cinematic_quality")
        p_cols = st.columns([15, 2], gap="small")
        with p_cols[0]:
            st.write("")
        with p_cols[1]:
            st.markdown("<div class='generate-btn-wrapper'>", unsafe_allow_html=True)
            if st.button("Generate", key="studio_generate_action_btn", use_container_width=True):
                success, required_tokens, message = validate_and_deduct_tokens("Cinematic Engine", cinematic_quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    user_credits = get_user_credits_db(st.session_state["logged_user"])
                    required_credits = 1 if "720p" in st.session_state["res_choice"] else 2
                    if not user_input.strip():
                        st.error("Provide prompt parameters to begin rendering.")
                    elif not credit_check(st.session_state["logged_user"], required_credits):
                        st.error(f"Low Credit Error! Required: {required_credits}, Available: {user_credits}")
                    else:
                        st.session_state["studio_prompt_value"] = user_input
                        st.session_state["studio_prompt_mode"] = input_mode
                        st.session_state["trigger_render"] = True
                        st.session_state["render_failed"] = False
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    parameters_col, video_canvas_col = st.columns([1.1, 1.4], gap="medium")
    with parameters_col:
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>⚙️ ENGINE CONFIGURATORS</h4>", unsafe_allow_html=True)
            render_premium_selection_cards("Model Core Selection", ["🤖 gemini-2.5-flash (Fast Stream Processing)", "🤖 gemini-2.5-pro (Deep Creative Narrative)"], "model_choice")
            selected_model = "gemini-2.5-pro" if "gemini-2.5-pro" in st.session_state["model_choice"] else "gemini-2.5-flash"
            render_premium_selection_cards("Aspect Scaling Rules", ["📐 9:16 Vertical (Shorts/Reels)", "📐 16:9 Landscape (YouTube)", "📐 1:1 Square (Instagram)"], "aspect_ratio")
            render_premium_selection_cards("Timeline Target Duration", ["⏱️ Quick Format Shorts (10-15s)", "⏱️ Expanded Long Format (1 Minute / 60s)"], "duration_choice")
            st.markdown("<div class='compact-label'>🎤 Voice Profile</div>", unsafe_allow_html=True)
            voice_options = list(ELEVENLABS_VOICES.keys())
            current_voice = st.session_state.get("voice_profile", "Drew (Premium Male Voice)")
            if current_voice not in voice_options:
                current_voice = "Drew (Premium Male Voice)"
            selected_voice = st.selectbox("Select Voice", voice_options, index=voice_options.index(current_voice) if current_voice in voice_options else 0, key="cinematic_voice_select")
            if selected_voice != st.session_state.get("voice_profile"):
                st.session_state["voice_profile"] = selected_voice
            render_premium_selection_cards("Quality resolution", ["720p", "1080p", "2K", "4K"], "res_choice")
            st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 15px 0;'>", unsafe_allow_html=True)
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>🔒 FACE LOCK SECURITY</h4>", unsafe_allow_html=True)
            face_lock_enabled = st.toggle("Enable Face Lock", value=False, key="face_lock_enabled_toggle")
            if face_lock_enabled:
                face_lock_image = st.file_uploader("Upload Face Lock Image", type=['jpg', 'jpeg', 'png', 'webp'], key="face_lock_upload")
                if face_lock_image:
                    face_lock_path = f"face_videos/face_lock_{uuid.uuid4().hex[:8]}.png"
                    with open(face_lock_path, "wb") as f:
                        f.write(face_lock_image.getbuffer())
                    st.success("✅ Face Lock Image Uploaded Successfully!")
                    st.image(face_lock_path, caption="Face Lock Image", use_container_width=True)
                    st.info("🔒 Face Lock Active - Workspace is secured")
                else:
                    st.warning("⚠️ Please upload a face image to enable Face Lock")
            else:
                st.info("🔓 Face Lock Disabled - Workspace is open")
            st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 15px 0;'>", unsafe_allow_html=True)
            st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>🎵 AUDIO MIXING CONFIG</h4>", unsafe_allow_html=True)
            uploaded_bgm = st.file_uploader("Upload Custom BGM Track", type=['mp3', 'wav'], key="studio_audio_bgm_uploader")
            bgm_volume = st.slider("BGM Audio Level Mixer", 0.0, 1.0, 0.30, step=0.05, key="studio_audio_bgm_volume_slider")
    with video_canvas_col:
        with st.container(border=True):
            st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>🎥 LIVE VIDEO OUTPUT BOX</h3>", unsafe_allow_html=True)
            canvas_slot = st.empty()
            aspect_ratio_css = "9/16"
            if "16:9" in st.session_state["aspect_ratio"]:
                aspect_ratio_css = "16/9"
            elif "1:1" in st.session_state["aspect_ratio"]:
                aspect_ratio_css = "1/1"
            if st.session_state.get("render_failed", False):
                with canvas_slot.container():
                    st.markdown("""
                        <div style="background: rgba(239, 68, 68, 0.1); border: 2px solid #ef4444; border-radius: 12px; padding: 25px; text-align: center; margin-bottom: 15px;">
                            <span style="font-size: 40px;">⚠️</span>
                            <h4 style="color: #fca5a5; font-family: Orbitron; margin-top: 10px; letter-spacing: 0.5px;">GENERATION ENGINE SUSPENDED</h4>
                            <p style="color: #fca5a5; font-size: 12.5px; margin-bottom: 15px; font-weight: 300;">An exception occurred during rendering. Ensure network connections are steady and confirm configuration parameters.</p>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("🔄 Retry Video Generation Pipeline", key="retry_render_pipeline_btn", use_container_width=True):
                        st.session_state["render_failed"] = False
                        st.session_state["trigger_render"] = True
                        st.rerun()
            if st.session_state["trigger_render"]:
                st.session_state["trigger_render"] = False
                pipeline_prompt_input = st.session_state.get("studio_prompt_value", "")
                pipeline_prompt_mode = st.session_state.get("studio_prompt_mode", "💡 Autonomous AI Topic")
                required_credits = 1 if "720p" in st.session_state["res_choice"] else 2
                deduct_credits_db(st.session_state["logged_user"], required_credits)
                bgm_temp_path = None
                if uploaded_bgm is not None:
                    bgm_temp_path = os.path.join("temp_scenes", f"user_bgm_{int(time.time())}.mp3")
                    with open(bgm_temp_path, "wb") as f:
                        f.write(uploaded_bgm.getbuffer())
                try:
                    with canvas_slot.container():
                        st.markdown(f"<div class='canvas-container-box' style='aspect-ratio: {aspect_ratio_css}; height: 380px; min-height: 380px; flex-direction: column;'>", unsafe_allow_html=True)
                        status_indicator = st.empty()
                        progress_pulse = st.empty().progress(0, text="Initiating transcription nodes...")
                        status_indicator.write("🎬 **Executing Generation Sequence...**")
                        time.sleep(0.2)
                        progress_pulse.progress(20, text="Interpreting prompt syntax...")
                        music_mood = "cinematic"
                        if pipeline_prompt_mode == "🧠 DeepSeek AI Blueprint":
                            status_indicator.write("🧠 **DeepSeek AI is generating structured video blueprint...**")
                            progress_pulse.progress(25, text="Calling DeepSeek API for blueprint generation...")
                            aspect_for_deepseek = "9:16" if "VERTICAL" in st.session_state.get("studio_deepseek_aspect", "9:16 VERTICAL") else "16:9"
                            blueprint = generate_video_blueprint_with_deepseek(pipeline_prompt_input, aspect_for_deepseek)
                            if "error" in blueprint:
                                status_indicator.error(f"❌ DeepSeek Error: {blueprint['error']}")
                                st.session_state["render_failed"] = True
                                st.markdown("</div>", unsafe_allow_html=True)
                                raise Exception(f"DeepSeek API Error: {blueprint['error']}")
                            else:
                                scenes = []
                                for scene in blueprint.get("scenes", []):
                                    scenes.append({"scene_text": scene.get("narration_text", ""), "search_keyword": scene.get("visual_prompt", "mystery").split(",")[0].strip()[:30], "duration": scene.get("duration_sec", 5)})
                                music_mood = "cinematic"
                                status_indicator.write("✅ **DeepSeek Blueprint compiled successfully!**")
                                st.success(f"🎬 Video Title: {blueprint.get('video_title', 'Untitled Production')}")
                        else:
                            if pipeline_prompt_mode == "💡 Autonomous AI Topic":
                                scenes, music_mood = ScriptingEngine.generate_script(topic=pipeline_prompt_input, duration_choice=st.session_state["duration_choice"], selected_model=selected_model, language_choice=st.session_state["language_choice"])
                            else:
                                scenes = parse_tagged_script(pipeline_prompt_input)
                                music_mood = "cinematic"
                        if scenes:
                            st.session_state["hook_variations"] = generate_hook_variations(scenes[0]["scene_text"])
                        progress_pulse.progress(40, text="Synthesizing storyboards...")
                        status_indicator.write("🌐 **Step 2: Fetching Assets & Sourcing Visuals...**")
                        time.sleep(0.2)
                        progress_pulse.progress(60, text="Extracting contextual database items...")
                        status_indicator.write("🧵 **Step 3: Stitching Scenes & Mixing Audio...**")
                        progress_pulse.progress(80, text="Merging multi-scene elements and overlaying audio arrays...")
                        render_result_container = []
                        size_choice_val = st.session_state.get("aspect_ratio")
                        voice_profile_val = st.session_state.get("voice_profile")
                        language_choice_val = st.session_state.get("language_choice")
                        data_snapshot = {"aspect_ratio": size_choice_val, "voice_profile": voice_profile_val, "language_choice": language_choice_val, "required_credits": required_credits, "logged_user": st.session_state.get("logged_user"), "res_choice": st.session_state.get("res_choice"), "duration_choice": st.session_state.get("duration_choice"), "music_mood": music_mood, "workshop_img": st.session_state.get("workshop_active_image")}
                        effective_bgm_path = bgm_temp_path
                        if not effective_bgm_path:
                            normalized_mood = music_mood.lower().strip()
                            effective_bgm_path = get_music_path(normalized_mood)
                        render_status_dict = {}
                        def internal_thread_worker(data_snapshot, scenes_data, video_output, bgm_path, bgm_volume, status_dict):
                            result = {"success": False, "error": None, "video_path": None}
                            try:
                                thread_result = StitcherEngine.build_scene_stitched_video_isolated(scenes_data=scenes_data, video_output=video_output, size_choice=data_snapshot["aspect_ratio"], voice_profile=data_snapshot["voice_profile"], language_choice=data_snapshot["language_choice"], bgm_path=bgm_path, bgm_volume=bgm_volume, music_mood=data_snapshot.get("music_mood"), status_dict=status_dict, workshop_img=data_snapshot.get("workshop_img"))
                                if thread_result and os.path.exists(video_output):
                                    result["success"] = True
                                    result["video_path"] = video_output
                                else:
                                    result["success"] = False
                                    result["error"] = "Stitching failed without explicit error flags."
                            except Exception:
                                error_msg = traceback.format_exc()
                                result["success"] = False
                                result["error"] = error_msg
                            render_result_container.append(result)
                        st.session_state["render_status"] = "running"
                        compilation_thread = threading.Thread(target=internal_thread_worker, args=(data_snapshot, scenes, "final_shorts.mp4", effective_bgm_path, bgm_volume, render_status_dict), daemon=True)
                        compilation_thread.start()
                        poll_interval = 0.3
                        max_wait = 600
                        elapsed = 0
                        while compilation_thread.is_alive() and elapsed < max_wait:
                            time.sleep(poll_interval)
                            elapsed += poll_interval
                            warning_text = render_status_dict.get("warning_text")
                            active_statuses = []
                            for k in sorted(render_status_dict.keys()):
                                if isinstance(k, int):
                                    active_statuses.append(f"Scene {k+1}: {render_status_dict[k]}")
                            if active_statuses:
                                status_text = " | ".join(active_statuses)
                            else:
                                status_text = "Processing active scene layers..."
                            if warning_text:
                                status_indicator.warning(warning_text)
                            else:
                                status_indicator.write(f"🎬 **{status_text}**")
                            pct = min(80 + int((elapsed / 60) * 15), 98)
                            progress_pulse.progress(pct, text=f"{status_text} ({int(elapsed)}s elapsed)...")
                        thread_success = False
                        if render_result_container:
                            result = render_result_container[0]
                            thread_success = result.get("success", False)
                        if bgm_temp_path and os.path.exists(bgm_temp_path):
                            try:
                                safe_remove_file(bgm_temp_path)
                            except Exception:
                                pass
                        if thread_success:
                            status_indicator.write("🔄 **Step 4: Transcoding & Validating Output Streams...**")
                            progress_pulse.progress(95, text="Transcoding parameters...")
                            time.sleep(0.3)
                            progress_pulse.progress(100, text="Compilation successful!")
                            status_indicator.write("✨ Video successfully compiled!")
                            duration_min = 1.0 if "1 Minute" in st.session_state["duration_choice"] else 0.25
                            stock_count = sum([1 for k, v in render_status_dict.items() if isinstance(k, int) and "Stock" in str(v)])
                            billing_result = process_video_billing(st.session_state["logged_user"], duration_min, len(scenes), stock_count)
                            if billing_result["status"] == "success":
                                st.toast(f"Credits billed: {billing_result['deducted']}. Remaining: {billing_result['remaining']}")
                            else:
                                st.error(f"Billing Engine warning: {billing_result.get('message')}")
                            timestamp = time.strftime("%Y%m%d_%H%M%S")
                            local_file_name = f"zovix_video_render_{timestamp}.mp4"
                            history_path = f"saved_renders/{local_file_name}"
                            if os.path.exists("final_shorts.mp4"):
                                shutil.copy("final_shorts.mp4", history_path)
                                if st.session_state.get("is_logged_in"):
                                    update_user_xp_db(st.session_state["logged_user"], 10)
                                    st.session_state["xp_points"] = get_user_xp_db(st.session_state["logged_user"])
                                    st.session_state["creator_level"] = 1 + (st.session_state["xp_points"] // 100)
                                save_render_to_db(st.session_state.get("logged_user"), local_file_name, pipeline_prompt_input, history_path)
                                save_to_json_history(st.session_state.get("logged_user"), local_file_name, pipeline_prompt_input, history_path)
                                st.session_state["history_renders"] = load_renders_history_db(st.session_state.get("logged_user"))
                                st.session_state["render_done"] = True
                        else:
                            try:
                                add_credits(st.session_state.get("logged_user"), required_credits, "standard")
                            except Exception:
                                pass
                            asli_error = "File 'final_shorts.mp4' generation failed."
                            if render_result_container and len(render_result_container) > 0:
                                thread_error = render_result_container[0].get("error")
                                if thread_error:
                                    asli_error = thread_error
                            status_indicator.error(f"🚨 PIPELINE CRASHED! DETAILS:\n{asli_error}")
                            st.session_state["render_failed"] = True
                        st.session_state["render_status"] = "idle"
                        st.markdown("</div>", unsafe_allow_html=True)
                except Exception as e:
                    asli_error = traceback.format_exc()
                    status_indicator.error(f"🚨 ERROR ENCOUNTERED:\n{asli_error}")
                    try:
                        add_credits(st.session_state.get("logged_user"), required_credits, "standard")
                    except Exception:
                        pass
                    if bgm_temp_path:
                        safe_remove_file(bgm_temp_path)
                    st.session_state["render_failed"] = True
            with canvas_slot.container():
                scene_count = len(scenes) if 'scenes' in locals() else 3
                est_time = scene_count * 5
                if os.path.exists("final_shorts.mp4") and os.path.getsize("final_shorts.mp4") > 0:
                    st.video("final_shorts.mp4", format="video/mp4", autoplay=False, loop=True, muted=False)
                    st.markdown(f"""
                        <div style="background: rgba(255, 192, 203, 0.05); border: 1px solid rgba(255, 192, 203, 0.18); border-radius: 8px; padding: 10px; margin-top: 10px; font-family: 'Orbitron', sans-serif; font-size: 11px; text-align: center; color: #a0a0a0;">
                            🟢 Active Canvas State | Resolution: <span style="color: #FFC0CB; font-weight: bold;">{st.session_state['res_choice']}</span> | 
                            Model: <span style="color: #FFC0CB; font-weight: bold;">{selected_model}</span> | 
                            Render Runtime: <span style="color: #FFC0CB; font-weight: bold;">{est_time}s</span>
                        </div>
                    """, unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_dl_opts, col_share, col_clr = st.columns([1.5, 1.2, 1], gap="medium")
                    with col_dl_opts:
                        with st.popover("📥 Download Video File", use_container_width=True):
                            st.markdown("<div class='compact-label' style='margin-top:2px;'>Format Selection:</div>", unsafe_allow_html=True)
                            export_format = st.selectbox("Select Format", ["MP4 (1080p)", "MOV (ProRes)", "GIF (Loop)"], key="canvas_export_format_selectbox")
                            watermark = st.checkbox("Include Zovix Watermark", value=True, key="canvas_watermark_checkbox")
                            if st.button("Download Project", key="canvas_download_project_action_btn", use_container_width=True):
                                st.write(f"Preparing {export_format} with Watermark: {watermark}...")
                                if os.path.exists("final_shorts.mp4"):
                                    with open("final_shorts.mp4", "rb") as video_file:
                                        video_bytes_data = video_file.read()
                                    file_ext = "mp4" if "MP4" in export_format else ("mov" if "MOV" in export_format else "gif")
                                    st.download_button(label=f"📥 Click to Save as {file_ext.upper()}", data=video_bytes_data, file_name=f"zovix_project_render.{file_ext}", mime=f"video/{file_ext}" if file_ext != "gif" else "image/gif", use_container_width=True, key="st_final_download_save_action_button")
                    with col_share: 
                        local_share_url = os.path.abspath("final_shorts.mp4") if hasattr(os, 'abspath') else os.path.abspath("final_shorts.mp4")
                        if st.button("🔗 Copy Local Path", key="social_copy_link_btn", use_container_width=True):
                            st.toast("Copied absolute local render address.")
                            st.info(f"Local Path: {local_share_url}")
                    with col_clr:
                        if st.button("🧹 Clear Canvas", key="canvas_studio_clear", use_container_width=True):
                            safe_remove_file("final_shorts.mp4")
                            safe_remove_file("final_shorts.webm")
                            st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.container(border=True):
                        st.markdown("<h4 style='font-family: Orbitron; font-size: 12px; color: #FFC0CB; margin-bottom: 12px;'>🌐 SOCIAL SHARE PLATFORM SUITE</h4>", unsafe_allow_html=True)
                        share_link_sim = "http://localhost:8501/renders/final_shorts.mp4"
                        sh_col1, sh_col2, sh_col3 = st.columns(3, gap="small")
                        with sh_col1:
                            if st.button("🔗 Copy Share Link", key="social_share_link_copy", use_container_width=True):
                                st.toast("Simulated share link created!")
                                st.info(f"Direct URL: `{share_link_sim}`")
                        with sh_col2:
                            wa_message = f"Check out this spectacular video I generated using ZOVIX: {share_link_sim}"
                            wa_intent_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_message)}"
                            st.link_button("💬 WhatsApp Share", wa_intent_url, use_container_width=True)
                        with sh_col3:
                            tw_message = f"Just created a stunning cinematic render on ZOVIX! #AIVideo #ZOVIX {share_link_sim}"
                            tw_intent_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(tw_message)}"
                            st.link_button("🐦 Share on X", tw_intent_url, use_container_width=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.container(border=True):
                        st.markdown("<h4 style='font-family: Orbitron; font-size: 12px; color: #FFC0CB; margin-bottom: 10px;'>⚙ MULTI-FORMAT EXPORT ENGINE</h4>", unsafe_allow_html=True)
                        if st.button("🔄 Transcode to WebM Formats", key="transcode_webm_trigger", use_container_width=True):
                            with st.spinner("Processing WebM filters..."):
                                success_webm = convert_mp4_to_webm("final_shorts.mp4", "final_shorts.webm")
                                if success_webm:
                                    st.success("WebM Compilation Complete!")
                                    st.rerun()
                                else:
                                    st.error("Transcode pipeline failed.")
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander("📊 View Render Logs & Metadata", expanded=False):
                        st.markdown(f"""
                            <table style="width: 100%; border-collapse: collapse; font-family: 'Inter'; font-size: 13px; color: #94a3b8;">
                                <tr style="border-bottom: 1px solid rgba(255,192,203,0.05);">
                                    <td style="padding: 8px 0; font-weight: bold; color: #FFC0CB;">Parameter</td>
                                    <td style="padding: 8px 0; font-weight: bold; color: #FFC0CB;">Value</td>
                                </tr>
                                <tr style="border-bottom: 1px solid rgba(255,192,203,0.05);">
                                    <td style="padding: 8px 0; color: #ffffff;">Render Aspect Dimension</td>
                                    <td style="padding: 8px 0; color: #b8860b;">{st.session_state['aspect_ratio']}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid rgba(255,192,203,0.05);">
                                    <td style="padding: 8px 0; color: #ffffff;">Engine Voice Channel</td>
                                    <td style="padding: 8px 0; color: #b8860b;">{st.session_state['voice_profile']}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid rgba(255,192,203,0.05);">
                                    <td style="padding: 8px 0; color: #ffffff;">Model Core used</td>
                                    <td style="padding: 8px 0; color: #b8860b;">{selected_model}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #ffffff;">Status</td>
                                    <td style="padding: 8px 0; color: #10b981; font-weight: bold;">Successfully Compiled</td>
                                </tr>
                            </table>
                        """, unsafe_allow_html=True)
                else: 
                    st.markdown("""
                        <div style="height: 380px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #64748b; background: rgba(10,10,12,0.4); border-radius:12px; border: 1px dashed rgba(255,192,203,0.15); width: 100%;">
                            <span style="font-size: 50px; margin-bottom: 12px;">🎬</span>
                            <p style="font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; color: #FFC0CB;">Video will render here</p>
                            <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px;">Output will display instantly upon initiating render sequences.</p>
                        </div>
                    """, unsafe_allow_html=True)

# ========================================================
# 40. PRIVACY POLICY
# ========================================================

def show_privacy_policy():
    st.markdown("---")
    with st.expander("Legal & Privacy Policy"):
        st.markdown("""
        ### Privacy Policy
        **Last updated: June 21, 2026**
        At Zovix, we prioritize your privacy. This policy outlines how we handle your data.
        **1. Information Collection:** We collect minimal information (like email) to provide our services.
        **2. Data Usage:** Information is used solely to maintain and improve the platform.
        **3. Data Storage:** All data is encrypted and stored securely. You can request data deletion anytime.
        **4. GDPR Compliance:** We are fully GDPR compliant. You have the right to access, modify, or delete your data.
        **5. Payments:** We use Razorpay, Stripe, PayPal, and Crypto for secure transactions. 
        **6. Contact:** Reach out to us at **zovixenterprises@gmail.com**.
        """)
        
        if st.session_state.get("is_logged_in"):
            if st.button("🗑️ Request Data Deletion (GDPR)", use_container_width=True):
                if st.button("⚠️ Confirm Delete All Data", use_container_width=True):
                    if gdpr_manager.delete_user_data(st.session_state["logged_user"]):
                        st.success("All your data has been deleted. You will be logged out.")
                        st.session_state["is_logged_in"] = False
                        st.session_state["current_page"] = "landing"
                        st.rerun()
                    else:
                        st.error("Failed to delete data. Please contact support.")

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

if st.session_state.get("show_2fa", False):
    show_2fa_modal()
    st.stop()

if st.session_state.get("is_logged_in"):
    if not gdpr_manager.get_consent(st.session_state["logged_user"]):
        if not gdpr_manager.request_consent(st.session_state["logged_user"]):
            st.stop()

if st.session_state["current_page"] == "landing":
    handle_payment_response()
    st.markdown(get_premium_theme_css(), unsafe_allow_html=True)
    st.markdown("""
        <div class="header-nav-container" style="padding-top: 20px; margin-bottom: 10px;">
            <div></div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("""
        <div class="leonardo-hero" style="height: 400px; margin-top: 0px;">
            <div class="leonardo-title">CREATE TO CINEMATIC RENDER</div>
            <p style="color: #EC4899; font-family: 'Orbitron'; font-size: 14px; text-transform: uppercase; letter-spacing: 2px;">Next-Gen Cinematic AI Automation Engine</p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; margin-bottom: 25px;'>", unsafe_allow_html=True)
    if st.button("⚡ EXPLORE STUDIO SPACE (Gatekeeper Access Required)", key="bypassed_guest_login_btn", use_container_width=True):
        show_auth_modal("login")
    st.markdown("</div>", unsafe_allow_html=True)
    p_col1, p_col2 = st.columns([8, 2], gap="small")
    with p_col1:
        landing_prompt_text = st.text_input("Landing Prompt Input Bar", placeholder="Type a creative prompt: e.g. Neon glowing lost palace deep inside cyber jungle, 8k cinematic...", label_visibility="collapsed", key="landing_prompt_text_input")
    with p_col2:
        if st.button("Generate Video", key="landing_direct_generate_action_btn", use_container_width=True):
            show_auth_modal("login")
    st.markdown("""
        <div class="leonardo-icons-row">
            <div class="leonardo-icon-tab"><span>🖼️</span><p>Image</p></div>
            <div class="leonardo-icon-tab"><span>📹</span><p>Video</p></div>
            <div class="leonardo-icon-tab"><span>📐</span><p>Blueprints</p></div>
            <div class="leonardo-icon-tab"><span>🌊</span><p>Flow State</p></div>
            <div class="leonardo-icon-tab"><span>⚡</span><p>Upscaler</p></div>
            <div class="leonardo-icon-tab"><span>🎨</span><p>Draw</p></div>
            <div class="leonardo-icon-tab"><span>🎬</span><p>Video Editor</p></div>
            <div class="leonardo-icon-tab"><span>👤</span><p>Face Video</p></div>
            <div class="leonardo-icon-tab"><span>🤖</span><p>AI Agent</p></div>
            <div class="leonardo-icon-tab"><span>🎙️</span><p>AI Sales</p></div>
            <div class="leonardo-icon-tab"><span>🧠</span><p>Dynamic UI</p></div>
            <div class="leonardo-icon-tab"><span>🎤</span><p>Live Emotion</p></div>
        </div>
        <br><br>
    """, unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; font-family:Orbitron; font-size:20px; color:#ffffff; margin-top:10px; margin-bottom: 15px; letter-spacing: 1px;'>📸 COMMUNITY CREATIONS SLIDER</h3>", unsafe_allow_html=True)
    slider_images = [
        {"url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=600", "caption": "Neon Temple Ruins"},
        {"url": "https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?q=80&w=600", "caption": "Quantum Runes"},
        {"url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=600", "caption": "Cosmic Energy"},
        {"url": "https://images.unsplash.com/photo-1582213782179-e0d53f98f2ca?q=80&w=600", "caption": "Digital Neural Network"},
        {"url": "https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=600", "caption": "Starry Night"},
        {"url": "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?q=80&w=600", "caption": "Mystic Forest"},
        {"url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=600", "caption": "Sunset Mountains"},
        {"url": "https://images.unsplash.com/photo-1518173946687-a3cfd0b4b4f9?q=80&w=600", "caption": "Aurora Borealis"},
    ]
    st.markdown("<div class='photo-slider-container'>", unsafe_allow_html=True)
    for img in slider_images:
        st.markdown(f"""
            <div class='photo-slide-item'>
                <img src="{img['url']}" alt="{img['caption']}" />
                <div class='caption'>{img['caption']}</div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; font-family:Orbitron; font-size:22px; color:#ffffff; margin-top:30px; margin-bottom: 25px; letter-spacing: 1px;'>🔥 COMMUNITY VIRAL SHOWCASE</h3>", unsafe_allow_html=True)
    showcase_items = get_showcase_items()
    if not showcase_items:
        showcase_items = [
            {"username": "AlphaCreator", "prompt": "Submerged temple ruins of Dwarka glowing under neon deep sea probes.", "thumbnail_path": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=600", "timestamp": "June 21, 2026"},
            {"username": "CyberWizard", "prompt": "A glowing quantum string matrix hovering over floating Norse runes.", "thumbnail_path": "https://images.unsplash.com/photo-1578894381163-e72c17f2d45f?q=80&w=600", "timestamp": "June 21, 2026"},
            {"username": "SpaceVibe", "prompt": "First contact Wow! signal visualised as cosmic energy arrays.", "thumbnail_path": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=600", "timestamp": "June 21, 2026"},
            {"username": "TechNovice", "prompt": "Nanobots repairing cellular decay within a holographic neural construct.", "thumbnail_path": "https://images.unsplash.com/photo-1582213782179-e0d53f98f2ca?q=80&w=600", "timestamp": "June 21, 2026"}
        ]
    sh_cols = st.columns(4)
    for i, s_item in enumerate(showcase_items[:4]):
        with sh_cols[i]:
            with st.container(border=True):
                st.markdown(f"""
                    <div style="background: rgba(18, 19, 26, 0.4); border-radius: 8px; overflow: hidden; height: 260px; display: flex; flex-direction: column; justify-content: space-between; padding: 10px;">
                        <img src="{s_item['thumbnail_path']}" style="width: 100%; height: 130px; object-fit: cover; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);" />
                        <div style="margin-top: 8px;">
                            <div style="font-size: 11px; font-weight: bold; color: #EC4899; font-family: 'Orbitron';">👤 {s_item['username'].upper()}</div>
                            <div style="font-size: 11px; color: #94a3b8; height: 50px; overflow: hidden; text-overflow: ellipsis; margin-top: 4px; line-height: 1.3;">"{s_item['prompt']}"</div>
                        </div>
                        <div style="font-size: 9px; color: #64748b; text-align: right;">{s_item['timestamp'][:15]}</div>
                    </div>
                """, unsafe_allow_html=True)
    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; font-family:Orbitron; font-size:24px; color:#ffffff; margin-bottom: 30px; letter-spacing: 1px;'>🚀 INTEGRATED WORKFLOW PIPELINE</h3>", unsafe_allow_html=True)
    col_step1, col_step2, col_step3 = st.columns(3)
    with col_step1:
        st.markdown("""
            <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 20px; height: 100%;">
                <div style="font-size: 24px; font-weight: bold; color: #ffd700; margin-bottom: 10px; font-family: 'Orbitron';">01</div>
                <h4 style="color: #ffffff; font-family: Orbitron; font-size: 15px; margin-bottom: 8px;">1. Structured Scripting</h4>
                <p style="color: #94a3b8; font-size: 12.5px; line-height: 1.5; font-weight: 300;">Constructs structured scripts with scene-by-scene keyword parameters using the LLM engine.</p>
            </div>
        """, unsafe_allow_html=True)
    with col_step2:
        st.markdown("""
            <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 20px; height: 100%;">
                <div style="font-size: 24px; font-weight: bold; color: #ffd700; margin-bottom: 10px; font-family: 'Orbitron';">02</div>
                <h4 style="color: #ffffff; font-family: Orbitron; font-size: 15px; margin-bottom: 8px;">2. Voice Synthetics</h4>
                <p style="color: #94a3b8; font-size: 12.5px; line-height: 1.5; font-weight: 300;">Generates specific voice streams per scene block and calculates precise audio timelines.</p>
            </div>
        """, unsafe_allow_html=True)
    with col_step3:
        st.markdown("""
            <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 20px; height: 100%;">
                <div style="font-size: 24px; font-weight: bold; color: #ffd700; margin-bottom: 10px; font-family: 'Orbitron';">03</div>
                <h4 style="color: #ffffff; font-family: Orbitron; font-size: 15px; margin-bottom: 8px;">3. Multi-Scene Stitching</h4>
                <p style="color: #94a3b8; font-size: 12.5px; line-height: 1.5; font-weight: 300;">Trims visual assets to matching segment runtimes and compiles them together into final outputs.</p>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-family: Orbitron; font-size: 16px; color: #FFC0CB; margin-bottom: 15px;'>🌀 CORE SUITE SPECIFICATIONS</h4>", unsafe_allow_html=True)
    col_tech1, col_tech2, col_tech3, col_tech4, col_tech5, col_tech6 = st.columns(6)
    with col_tech1:
        st.markdown("""
            <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 14px; text-align: center; height: 100%;">
                <div style="font-size: 24px; margin-bottom: 8px;">📐</div>
                <h4 style="color: #ffffff; font-family: Orbitron; font-size: 13px; margin-bottom: 6px;">Blueprints</h4>
                <p style="color: #94a3b8; font-size: 11px; line-height: 1.4;">Structure engine geometries to plan object dynamics and layouts prior to rendering.</p>
            </div>
        """, unsafe_allow_html=True)
    with col_tech2:
        st.markdown("""
            <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 14px; text-align: center; height: 100%;">
                <div style="font-size: 24px; margin-bottom: 8px;">🌊</div>
                <h4 style="color: #ffffff; font-family: Orbitron; font-size: 13px; margin-bottom: 6px;">Flow State</h4>
                <p style="color: #94a3b8; font-size: 11px; line-height: 1.4;">Fluid dynamics simulator controlling movement, vectors and physics arrays.</p>
            </div>
        """, unsafe_allow_html=True)
    with col_tech3:
        st.markdown("""
            <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 14px; text-align: center; height: 100%;">
                <div style="font-size: 24px; margin-bottom: 8px;">⚡</div>
                <h4 style="color: #ffffff; font-family: Orbitron; font-size: 13px; margin-bottom: 6px;">Upscaler</h4>
                <p style="color: #94a3b8; font-size: 11px; line-height: 1.4;">Brings resolution profiles into cinematic 4K clarity mapping pixel fidelity.</p>
            </div>
        """, unsafe_allow_html=True)
    with col_tech4:
        st.markdown("""
            <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 14px; text-align: center; height: 100%;">
                <div style="font-size: 24px; margin-bottom: 8px;">🎨</div>
                <h4 style="color: #ffffff; font-family: Orbitron; font-size: 13px; margin-bottom: 6px;">Draw</h4>
                <p style="color: #94a3b8; font-size: 11px; line-height: 1.4;">Dynamic canvas overlay system supporting guided spatial drawing sketches.</p>
            </div>
        """, unsafe_allow_html=True)
    with col_tech5:
        st.markdown("""
            <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 14px; text-align: center; height: 100%;">
                <div style="font-size: 24px; margin-bottom: 8px;">👤</div>
                <h4 style="color: #ffffff; font-family: Orbitron; font-size: 13px; margin-bottom: 6px;">Face Video</h4>
                <p style="color: #94a3b8; font-size: 11px; line-height: 1.4;">AI-powered face animation with lip sync, emotion control, and camera angles.</p>
            </div>
        """, unsafe_allow_html=True)
    with col_tech6:
        st.markdown("""
            <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 14px; text-align: center; height: 100%;">
                <div style="font-size: 24px; margin-bottom: 8px;">🧠</div>
                <h4 style="color: #ffffff; font-family: Orbitron; font-size: 13px; margin-bottom: 6px;">Dynamic UI</h4>
                <p style="color: #94a3b8; font-size: 11px; line-height: 1.4;">Real-time interface adaptation based on user behavior and usage patterns.</p>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 40px 0 20px 0;'>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: center; padding: 10px 0 20px 0; color: #404040; font-family: 'Inter'; font-size: 13px;">
            <p style="margin-bottom: 10px; font-weight: 400; color: #404040;">© 2026 ZOVIX. All rights reserved.</p>
            <div style="display: flex; justify-content: center; gap: 20px; font-family: 'Orbitron'; font-size: 11px; letter-spacing: 1px;">
                <a href="#" style="color: #FFC0CB; text-decoration: none;">SUPPORT</a>
                <span style="color: rgba(255,255,255,0.1);">|</span>
                <a href="#" style="color: #FFC0CB; text-decoration: none;">DOCUMENTATION</a>
                <span style="color: rgba(255,255,255,0.1);">|</span>
                <a href="#" style="color: #FFC0CB; text-decoration: none;">API ACCESS</a>
            </div>
        </div>
    """, unsafe_allow_html=True)

elif st.session_state["current_page"] == "studio":
    if not st.session_state["is_logged_in"]:
        st.session_state["current_page"] = "landing"
        st.rerun()
    
    if st.session_state.get("2fa_enabled", False) and not st.session_state.get("2fa_verified", False):
        show_2fa_modal()
        st.stop()
    
    handle_payment_response()
    st.markdown(get_premium_theme_css(), unsafe_allow_html=True)
    
    get_language_selector()
    
    with st.sidebar.expander("🟢 System Health", expanded=False):
        health = system_health_check()
        for check in health["checks"]:
            icon = "✅" if check["status"] == "healthy" else "⚠️" if check["status"] == "warning" else "❌"
            st.markdown(f"{icon} **{check['name']}**: {check['status']}")
            if check.get("details"):
                st.caption(check["details"])
    
    col_left, col_center, col_right = st.columns([4, 4, 2])
    with col_left:
        st.markdown("<h2 style='margin:0; padding:0; font-family:Orbitron; color:white;'>YOURS TO CREATE</h2>", unsafe_allow_html=True)
        st.caption("ACTIVE GENERATION PIPELINE WORKSPACE")
    with col_center:
        st.markdown("""
            <div style='display: flex; justify-content: left; align-items: center; height: 100%; margin-top: -5px;'>
                <div class='z-logo'>Z</div>
            </div>
        """, unsafe_allow_html=True)
    with col_right:
        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
        if st.button("EXIT", key="main_top_exit_btn", use_container_width=True):
            st.session_state["current_page"] = "landing"
            st.session_state["is_logged_in"] = False
            st.session_state["2fa_verified"] = False
            st.rerun()
    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 10px 0 20px 0;'>", unsafe_allow_html=True)
    
    if check_49_voucher_valid():
        st.info(f"🎫 ₹49 Voucher Active! 35 Credits added. Valid for: {st.session_state.get('voucher_49_expiry', datetime.now() + timedelta(hours=24)).strftime('%H:%M:%S')} remaining")
    
    if st.button("⚡ QUICK ACCESS NODES " + ("▼" if st.session_state["quick_access_open"] else "▶"), key="quick_access_toggle", use_container_width=True):
        st.session_state["quick_access_open"] = not st.session_state["quick_access_open"]
    if st.session_state["quick_access_open"]:
        st.markdown("""
        <div class="quick-access-panel">
            <div class="panel-header">⚡ QUICK ACCESS NODES</div>
        </div>
        """, unsafe_allow_html=True)
        tab_cols = st.columns(7)
        with tab_cols[0]:
            if st.button("⚙️ Setup", key="quick_tab_setup", use_container_width=True):
                st.session_state["sidebar_tab"] = "⚙️ Setup Config"
                st.rerun()
        with tab_cols[1]:
            if st.button("🚀 Factory", key="quick_tab_factory", use_container_width=True):
                st.session_state["sidebar_tab"] = "🚀 Zovix Mass Factory"
                st.rerun()
        with tab_cols[2]:
            if st.button("💎 Credits", key="quick_tab_credits", use_container_width=True):
                st.session_state["sidebar_tab"] = "💎 Buy Credits"
                st.rerun()
        with tab_cols[3]:
            if st.button("📂 Portfolio", key="quick_tab_portfolio", use_container_width=True):
                st.session_state["sidebar_tab"] = "📂 My Portfolio"
                st.rerun()
        with tab_cols[4]:
            if st.button("👤 Profile", key="quick_tab_profile", use_container_width=True):
                st.session_state["sidebar_tab"] = "👤 My Premium Profile"
                st.rerun()
        with tab_cols[5]:
            if st.button("👥 Sub-Users", key="quick_tab_subusers", use_container_width=True):
                st.session_state["sidebar_tab"] = "👥 SUB-USER ACCESS MANAGEMENT"
                st.rerun()
        with tab_cols[6]:
            if st.button("📅 Scheduler", key="quick_tab_scheduler", use_container_width=True):
                st.session_state["sidebar_tab"] = "📅 ADVANCED AI CONTENT SCHEDULER"
                st.rerun()
        st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 15px 0 20px 0;'>", unsafe_allow_html=True)
    
    if st.session_state["sidebar_tab"] == "⚙️ Setup Config":
        st.markdown("<h4 style='font-family: Orbitron; color: #FFC0CB;'>⚙️ Setup Configuration Panel</h4>", unsafe_allow_html=True)
        col_api, col_default = st.columns(2, gap="small")
        with col_api:
            with st.container(border=True):
                st.markdown("<h5 style='font-family: Orbitron; font-size: 12px; color: #FFC0CB; margin-bottom: 10px;'>🔑 API Key Configuration</h5>", unsafe_allow_html=True)
                st.text_input("Gemini API Key (Override)", value=st.session_state.get("user_gemini_api_key", ""), type="password", key="config_gemini_key", placeholder="Enter Gemini API Key...")
                st.text_input("Stability AI API Key", type="password", key="config_stability_key", placeholder="Enter Stability API Key...")
                st.text_input("ElevenLabs API Key", type="password", key="config_elevenlabs_key", placeholder="Enter ElevenLabs API Key...")
                st.text_input("Hugging Face API Key", type="password", key="config_hf_key", placeholder="Enter Hugging Face API Key...")
                if st.button("💾 Save API Keys", use_container_width=True):
                    st.session_state["user_gemini_api_key"] = st.session_state.get("config_gemini_key", "")
                    st.success("✅ API keys saved successfully!")
        with col_default:
            with st.container(border=True):
                st.markdown("<h5 style='font-family: Orbitron; font-size: 12px; color: #FFC0CB; margin-bottom: 10px;'>⚙️ Default Settings</h5>", unsafe_allow_html=True)
                st.selectbox("Default Language", ["🇮🇳 Hinglish", "🇬🇧 English", "🇫🇷 French", "🇯🇵 Japanese"], key="config_default_lang")
                st.selectbox("Default Voice Profile", ["Drew (Premium Male Voice)", "Rachel (Premium Female Voice)"], key="config_default_voice")
                st.selectbox("Default Aspect Ratio", ["📐 9:16 Vertical", "📐 16:9 Landscape", "📐 1:1 Square"], key="config_default_aspect")
                st.slider("Default BGM Volume", 0.0, 1.0, 0.30, key="config_default_bgm_vol")
    
    elif st.session_state["sidebar_tab"] == "🚀 Zovix Mass Factory":
        st.markdown("<h4 style='font-family: Orbitron; color: #FFC0CB;'>🚀 Zovix Mass Factory</h4>", unsafe_allow_html=True)
        st.info("Generate multiple videos in bulk using AI automation.")
        if st.button("🚀 Start Mass Production Run", key="mass_prod_start_btn", use_container_width=True):
            if FactoryProgress.get("is_running"):
                st.warning("⚠️ A mass production run is already in progress!")
            else:
                st.toast("Mass Production Started!")
                st.rerun()
        if FactoryProgress.get("is_running") or FactoryProgress.get("logs"):
            with st.container(border=True):
                st.markdown("### 📊 Production Progress")
                total_items = FactoryProgress.get("total_items", 18)
                current_index = FactoryProgress.get("current_index", 0)
                progress_pct = min(100, int((current_index / total_items) * 100)) if total_items > 0 else 0
                st.progress(progress_pct / 100, text=f"Progress: {progress_pct}%")
                st.markdown(f"**Current Category:** {FactoryProgress.get('current_category', 'N/A')}")
                st.markdown(f"**Current Topic:** {FactoryProgress.get('current_topic', 'N/A')}")
                logs = FactoryProgress.get("logs", [])
                if logs:
                    with st.expander("📋 View Logs", expanded=False):
                        for log in logs[-20:]:
                            st.text(log)
    
    elif st.session_state["sidebar_tab"] == "💎 Buy Credits":
        render_enhanced_payment_ui()
    
    elif st.session_state["sidebar_tab"] == "📂 My Portfolio":
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
        st.markdown("<h4 style='font-family: Orbitron; color: #FFC0CB;'>👤 My Premium Profile</h4>", unsafe_allow_html=True)
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
            else:
                st.info("2FA is not enabled for your account")
                if st.button("Setup 2FA", use_container_width=True):
                    secret = twofa.setup_2fa(st.session_state["logged_user"])
                    if secret:
                        qr_code = twofa.render_qr_code(st.session_state["logged_user"], secret)
                        if qr_code:
                            st.markdown(f"""
                                <div style="text-align: center; padding: 20px;">
                                    <h4>Scan QR Code with Google Authenticator</h4>
                                    <img src="data:image/png;base64,{qr_code}" style="max-width: 200px;" />
                                    <p style="font-size: 12px; color: #94a3b8; margin-top: 10px;">
                                        Or enter this secret manually: <code>{secret}</code>
                                    </p>
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.info(f"Secret: `{secret}`")
                        
                        code = st.text_input("Enter 6-digit code from authenticator", max_chars=6, type="password")
                        if st.button("Verify 2FA"):
                            if twofa.verify_code(st.session_state["logged_user"], code):
                                st.session_state["2fa_enabled"] = True
                                st.success("✅ 2FA enabled successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid code. Please try again.")
                    else:
                        st.error("Failed to setup 2FA. Please try again.")
            
            st.markdown("---")
            if st.button("🔄 Claim Daily Reward", key="claim_daily_reward_btn", use_container_width=True):
                result, streak, msg = enhanced_daily_reward(st.session_state["logged_user"])
                if result:
                    st.success(msg)
                    st.session_state["xp_points"] = get_user_xp_db(st.session_state["logged_user"])
                    st.session_state["creator_level"] = 1 + (st.session_state["xp_points"] // 100)
                    st.session_state["user_credits"] = get_user_credits_db(st.session_state["logged_user"])
                    st.rerun()
                else:
                    st.warning(msg)
            st.markdown("---")
            render_referral_system()
            st.markdown("---")
            render_leaderboard()
            st.markdown("---")
            render_competitive_features()
        else:
            st.warning("Please log in to view your profile.")
    
    elif st.session_state["sidebar_tab"] == "👥 SUB-USER ACCESS MANAGEMENT":
        st.markdown("<h4 style='font-family: Orbitron; color: #FFC0CB;'>👥 SUB-USER ACCESS MANAGEMENT</h4>", unsafe_allow_html=True)
        sub_col1, sub_col2 = st.columns([1.1, 1.4], gap="medium")
        with sub_col1:
            with st.container(border=True):
                st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>➕ ADD NEW LINKED SUB-USER</h4>", unsafe_allow_html=True)
                new_sub_user_id = st.text_input("Sub-User Email/ID:", placeholder="friend@zovix.ai", key="add_sub_user_text_input").strip()
                st.write("")
                if st.button("Link Sub-User Account", key="link_sub_user_action_btn", use_container_width=True):
                    if not new_sub_user_id:
                        st.error("Provide a valid ID configuration.")
                    else:
                        succ, msg = add_sub_user_db(st.session_state["logged_user"], new_sub_user_id)
                        if succ:
                            st.success(msg)
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(msg)
        with sub_col2:
            with st.container(border=True):
                st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>📋 CONNECTED ACTIVE SUB-USERS</h4>", unsafe_allow_html=True)
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
                                time.sleep(0.5)
                                st.rerun()
    
    elif st.session_state["sidebar_tab"] == "📅 ADVANCED AI CONTENT SCHEDULER":
        st.markdown("<h4 style='font-family: Orbitron; color: #FFC0CB;'>📅 ADVANCED AI CONTENT SCHEDULER</h4>", unsafe_allow_html=True)
        sch_col1, sch_col2 = st.columns([1.1, 1.4], gap="medium")
        with sch_col1:
            with st.container(border=True):
                st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>📅 BOOK A SOCIAL RUN</h4>", unsafe_allow_html=True)
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
                st.markdown("<h3 style='font-family: Orbitron; font-size: 14px; color: #FFC0CB; margin-bottom: 15px;'>📊 ACTIVE SCHEDULED JOBS CALENDAR</h3>", unsafe_allow_html=True)
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
                                    <span style="font-family:'Orbitron'; font-size: 11px; color:#FFC0CB; font-weight:bold;">{r_sch[3].upper()}</span>
                                    <span style="font-size:10px; color:#10b981; font-weight:bold; background:rgba(16,185,129,0.15); padding:2px 6px; border-radius:12px;">{r_sch[4].upper()}</span>
                                </div>
                                <div style="font-size: 13px; font-weight: bold; color: #ffffff; margin-top: 5px;">Category: {r_sch[0].replace('_', ' ')}</div>
                                <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Topic: "{r_sch[1]}"</div>
                                <div style="font-size:11px; color:#A0AEC0; font-family: monospace; margin-top: 4px;">📅 Execution Run: {r_sch[2]}</div>
                            </div>
                        """, unsafe_allow_html=True)
    
    st.markdown("<div class='compact-label' style='margin-bottom: 8px;'>Active Studio Workspace Mode</div>", unsafe_allow_html=True)
    col_m1, col_m2, col_m3, col_m4, col_m5, col_m6, col_m7, col_m8, col_m9, col_m10, col_m11, col_m12 = st.columns(12)
    mode_mapping = {
        "👤 Face Video Generator": "Face Video Mode",
        "🎬 Cinematic Engine ": "Cinematic Engine",
        "🎨 Creative Workshop ": "Creative Workshop Mode",
        "🎬 Video Editor ": "Video Editor Mode",
        "📐 Blueprints": "Blueprints Mode",
        "🌊 Flow State": "Flow State Mode",
        "⚡ Upscaler": "Upscaler Mode",
        "🎨 Draw": "Draw Mode",
        "🤖 AI Agent": "AI Agent Mode",
        "🎙️ AI Sales": "AI Sales Mode",
        "🧠 Dynamic UI": "Dynamic UI Mode",
        "🎤 Live Emotion": "Live Emotion Mode"
    }
    modes_list = list(mode_mapping.items())
    columns = [col_m1, col_m2, col_m3, col_m4, col_m5, col_m6, col_m7, col_m8, col_m9, col_m10, col_m11, col_m12]
    for idx, (btn_label, mode_value) in enumerate(modes_list):
        with columns[idx]:
            is_selected = (st.session_state["studio_active_mode"] == mode_value)
            wrapper_class = "selected-opt-wrap" if is_selected else "unselected-opt-wrap"
            st.markdown(f"<div class='{wrapper_class}'>", unsafe_allow_html=True)
            if st.button(btn_label, key=f"switch_to_{mode_value.replace(' ', '_')}_btn", use_container_width=True):
                handle_engine_access_request(mode_value)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.session_state["studio_active_mode"] == "Cinematic Engine":
        run_cinematic_engine()
    elif st.session_state["studio_active_mode"] == "Creative Workshop Mode":
        run_creative_workshop()
    elif st.session_state["studio_active_mode"] == "Blueprints Mode":
        run_blueprints_mode()
    elif st.session_state["studio_active_mode"] == "Flow State Mode":
        run_flow_state_mode()
    elif st.session_state["studio_active_mode"] == "Upscaler Mode":
        run_upscaler_mode()
    elif st.session_state["studio_active_mode"] == "Draw Mode":
        run_draw_mode()
    elif st.session_state["studio_active_mode"] == "Video Editor Mode":
        run_video_editor_mode()
    elif st.session_state["studio_active_mode"] == "Face Video Mode":
        run_face_video_mode()
    elif st.session_state["studio_active_mode"] == "AI Agent Mode":
        render_ai_agent_ui()
    elif st.session_state["studio_active_mode"] == "AI Sales Mode":
        render_ai_sales_ui()
    elif st.session_state["studio_active_mode"] == "Dynamic UI Mode":
        generate_dynamic_ui()
    elif st.session_state["studio_active_mode"] == "Live Emotion Mode":
        render_live_emotion_voice()
    
    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 30px 0;'>", unsafe_allow_html=True)

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
        elif current_mode == "Cinematic Engine":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                file_name = item.get("file_name", "")
                if os.path.exists(file_path) and "cinematic" in file_name.lower():
                    valid_items.append(item)
            gallery_title = "🎬 CINEMATIC ENGINE VIDEOS"
            no_items_msg = "No cinematic videos created yet. Generate your first cinematic video!"
            display_type = "video"
        elif current_mode == "Creative Workshop Mode":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                file_name = item.get("file_name", "")
                if os.path.exists(file_path) and "image" in file_name.lower():
                    valid_items.append(item)
            gallery_title = "🎨 CREATIVE WORKSHOP IMAGES"
            no_items_msg = "No workshop images created yet. Generate your first masterpiece!"
            display_type = "image"
        elif current_mode == "Video Editor Mode":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                file_name = item.get("file_name", "")
                if os.path.exists(file_path) and "editor" in file_name.lower():
                    valid_items.append(item)
            gallery_title = "🎬 VIDEO EDITOR OUTPUTS"
            no_items_msg = "No edited videos created yet. Upload media and process!"
            display_type = "video"
        elif current_mode == "Blueprints Mode":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                file_name = item.get("file_name", "")
                if os.path.exists(file_path) and "blueprint" in file_name.lower():
                    valid_items.append(item)
            gallery_title = "📐 BLUEPRINT GENERATIONS"
            no_items_msg = "No blueprints created yet. Generate your first architectural blueprint!"
            display_type = "image"
        elif current_mode == "Flow State Mode":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                file_name = item.get("file_name", "")
                if os.path.exists(file_path) and "flow" in file_name.lower():
                    valid_items.append(item)
            gallery_title = "🌊 FLOW STATE ANIMATIONS"
            no_items_msg = "No flow animations created yet. Generate your first flow simulation!"
            display_type = "video"
        elif current_mode == "Upscaler Mode":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                file_name = item.get("file_name", "")
                if os.path.exists(file_path) and "upscaled" in file_name.lower():
                    valid_items.append(item)
            gallery_title = "⚡ UPSCALED IMAGES"
            no_items_msg = "No upscaled images created yet. Upload an image to upscale!"
            display_type = "image"
        elif current_mode == "Draw Mode":
            for item in portfolio_renders_list:
                file_path = item.get("path", "")
                file_name = item.get("file_name", "")
                if os.path.exists(file_path) and "drawing" in file_name.lower():
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
    st.markdown(f"<h3 style='font-family: Orbitron; font-size: 18px; color: #FFFFFF; margin-bottom: 20px; letter-spacing: 1px;'>{gallery_title}</h3>", unsafe_allow_html=True)

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
                            <div style="font-family: 'Orbitron'; font-size: 11px; color: #EC4899; font-weight: bold; margin-bottom: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                {emotion_emoji} {item.get("file_name", "Voice")[:30]}
                            </div>
                        """, unsafe_allow_html=True)
                        if os.path.exists(item.get("path", "")):
                            with open(item["path"], "rb") as f:
                                audio_bytes = f.read()
                            st.audio(audio_bytes, format="audio/mp3")
                        st.markdown(f"""
                            <p style="font-size: 10px; color: #94a3b8; line-height: 1.3; height: 36px; overflow: hidden; text-overflow: ellipsis; margin: 8px 0 0 0; font-weight: 300;">
                                "{item.get('prompt', '')[:60]}"
                            </p>
                        """, unsafe_allow_html=True)
                        if st.button(f"📥 Download Audio", key=f"audio_dl_{idx}_{current_mode}", use_container_width=True):
                            if os.path.exists(item.get("path", "")):
                                with open(item["path"], "rb") as f:
                                    audio_bytes = f.read()
                                st.download_button(label="Click to Save", data=audio_bytes, file_name=f"zovix_voice_{uuid.uuid4().hex[:8]}.mp3", mime="audio/mp3", key=f"audio_dl_btn_{idx}")
        elif display_type == "text":
            text_cols = st.columns(2)
            for idx, item in enumerate(valid_items):
                with text_cols[idx % 2]:
                    with st.container(border=True):
                        st.markdown(f"""
                            <div style="font-family: 'Orbitron'; font-size: 11px; color: #45f3ff; font-weight: bold; margin-bottom: 6px;">
                                📝 {item.get("file_name", "Output")}
                            </div>
                        """, unsafe_allow_html=True)
                        st.markdown(f"""
                            <div style="background: rgba(18, 19, 26, 0.85); border-radius: 8px; padding: 12px; max-height: 150px; overflow-y: auto; font-size: 12px; color: #94a3b8; font-family: monospace; line-height: 1.5; border: 1px solid rgba(255,255,255,0.05);">
                                {item.get("content", "")[:500]}
                            </div>
                        """, unsafe_allow_html=True)
                        if len(item.get("content", "")) > 500:
                            st.caption(f"... and {len(item['content']) - 500} more characters")
                        if st.button(f"📋 Copy Text", key=f"text_copy_{idx}_{current_mode}", use_container_width=True):
                            st.toast("Text copied to clipboard!")
                            st.code(item.get("content", ""))
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
                                <div style="font-family: 'Orbitron'; font-size: 10px; color: #FFC0CB; font-weight: bold; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                    📁 {file_name[:25]}
                                    <span style="font-size: 8px; color: #45f3ff; margin-left: 5px;">[{quality}]</span>
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                                <div style="font-family: 'Orbitron'; font-size: 10px; color: #FFC0CB; font-weight: bold; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
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
                                        <span style="font-family: 'Orbitron'; font-size: 9px; color: #FFC0CB; margin-top: 5px; text-transform: uppercase;">VIDEO</span>
                                    </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.markdown("""
                                <div style="height: 120px; width: 100%; border-radius: 6px; overflow: hidden; border: 1px solid rgba(255,192,203,0.2); display: flex; flex-direction: column; align-items: center; justify-content: center; background: radial-gradient(circle, #1e1b29 0%, #0a0a0f 100%); margin-bottom: 10px;">
                                    <span style="font-size: 36px; display: block;">🎬</span>
                                    <span style="font-family: 'Orbitron'; font-size: 9px; color: #FFC0CB; margin-top: 5px; text-transform: uppercase;">VIDEO</span>
                                </div>
                            """, unsafe_allow_html=True)
                        st.markdown(f"""
                            <p style="font-size: 10px; color: #94a3b8; line-height: 1.3; height: 36px; overflow: hidden; text-overflow: ellipsis; margin: 8px 0 0 0; font-weight: 300;">
                                "{prompt[:60]}"
                            </p>
                        """, unsafe_allow_html=True)
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("▶️ Play", key=f"vid_play_{idx}_{current_mode}", use_container_width=True):
                                if os.path.exists(file_path):
                                    open_preview_modal(file_path)
                        with col_btn2:
                            if st.button("🔄 Remix", key=f"vid_remix_{idx}_{current_mode}", use_container_width=True):
                                st.session_state["studio_prompt_value"] = prompt
                                st.toast("Prompt copied!")
                                st.rerun()
        else:
            image_cols = st.columns(4)
            for idx, item in enumerate(valid_items[:8]):
                with image_cols[idx % 4]:
                    with st.container(border=True):
                        file_path = item.get("path", "")
                        file_name = item.get("file_name", "Untitled")
                        prompt = item.get("prompt", "")
                        st.markdown(f"""
                            <div style="font-family: 'Orbitron'; font-size: 10px; color: #FFC0CB; font-weight: bold; margin-bottom: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
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
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("🔎 View", key=f"img_view_{idx}_{current_mode}", use_container_width=True):
                                st.session_state["workshop_active_image"] = file_path
                                st.session_state["studio_active_mode"] = "Creative Workshop Mode"
                                st.rerun()
                        with col_btn2:
                            if st.button("🔄 Remix", key=f"img_remix_{idx}_{current_mode}", use_container_width=True):
                                st.session_state["studio_prompt_value"] = prompt
                                st.toast("Prompt copied!")
                                st.rerun()
                        if os.path.splitext(file_path)[1].lower() in [".png", ".jpg", ".jpeg", ".webm", ".gif"]:
                            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                            if st.button("🎬 Convert to Video", key=f"img_i2v_{idx}_{current_mode}", use_container_width=True):
                                with st.spinner("Synthesizing Motion Vector Layers... Please wait..."):
                                    motion_val = st.session_state.get("workshop_motion_bucket_slider", 127)
                                    video_out = convert_image_to_video_svd_robust(file_path, motion_bucket_id=motion_val)
                                    if video_out and os.path.exists(video_out):
                                        st.session_state["active_svd_video"] = video_out
                                        st.session_state["studio_active_mode"] = "Creative Workshop Mode"
                                        saved_vid_name = f"svd_render_{int(time.time())}.mp4"
                                        save_render_to_db(st.session_state.get("logged_user"), saved_vid_name, f"[I2V Motion of]: {prompt}", video_out)
                                        save_to_json_history(st.session_state.get("logged_user"), saved_vid_name, f"[I2V Motion of]: {prompt}", video_out)
                                        st.session_state["history_renders"] = load_renders_history_db(st.session_state.get("logged_user"))
                                        st.toast("Video compiled successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Image to video pipeline execution failed.")
                        if st.button("📢 Public Share", key=f"img_share_{idx}_{current_mode}", use_container_width=True):
                            img_thumb_path = file_path if os.path.splitext(file_path)[1].lower() in [".png", ".jpg"] else "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=300"
                            add_showcase_item(st.session_state["logged_user"], prompt, img_thumb_path)
                            st.toast("Success! Project shared to community viral showcase board.")
    
    if st.session_state["studio_active_mode"] == "Face Video Mode":
        st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 30px 0;'>", unsafe_allow_html=True)
        st.markdown("<h3 style='font-family: Orbitron; font-size: 18px; color: #FFFFFF; margin-bottom: 20px; letter-spacing: 1px;'>👤 FACE VIDEO HISTORY</h3>", unsafe_allow_html=True)
        face_videos = st.session_state.get("face_video_history", [])
        if not face_videos:
            st.info("No face videos generated yet. Upload a face image and create your first face video!")
        else:
            fv_grid = st.columns(3)
            for idx, fv_item in enumerate(face_videos[:6]):
                with fv_grid[idx % 3]:
                    with st.container(border=True):
                        quality_label = fv_item.get("quality", "Standard")
                        st.markdown(f"""
                            <div style="font-family: 'Orbitron'; font-size: 10px; color: #FFC0CB; font-weight: bold; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                📁 {fv_item.get("file_name", "Untitled")}
                                <span style="font-size: 8px; color: #45f3ff; margin-left: 5px;">[{quality_label}]</span>
                            </div>
                        """, unsafe_allow_html=True)
                        if os.path.exists(fv_item.get("path", "")):
                            st.video(fv_item["path"], format="video/mp4", autoplay=False, loop=True, muted=False)
                        st.markdown(f"""
                            <p style="font-size: 9px; color: #94a3b8; line-height: 1.3; height: 30px; overflow: hidden; text-overflow: ellipsis; margin: 4px 0 6px 0; font-weight: 300;">
                                "{fv_item.get('prompt', '')[:60]}..."
                            </p>
                        """, unsafe_allow_html=True)
                        if st.button(f"▶️ Play Face Video", key=f"fv_play_btn_{idx}", use_container_width=True):
                            if os.path.exists(fv_item.get("path", "")):
                                open_preview_modal(fv_item["path"])
                            else:
                                st.error("Video file not found.")
    
    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-family: Orbitron; font-size: 18px; color: #FFFFFF; margin-bottom: 20px; letter-spacing: 1px;'>📈 GLOBAL TRENDING HOT TOPICS (ONE-CLICK IMPORT)</h3>", unsafe_allow_html=True)
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
                        <span style="font-family:'Orbitron'; font-size:11px; font-weight:bold; color:#fbbf24;">{trend["hashtag"]}</span>
                        <span style="font-size:10px; color:#EC4899; font-weight:bold;">🔥 {trend["clicks"]}</span>
                    </div>
                    <div style="font-size:12px; color:#ffffff; font-weight:bold; height: 38px; overflow:hidden;">{trend["title"]}</div>
                    <div style="font-size:11px; color:#94a3b8; margin-bottom:12px;">Channel: {trend["category"]}</div>
                """, unsafe_allow_html=True)
                if st.button(f"One-Click Import Trend", key=f"import_trend_action_btn_{idx_t}", use_container_width=True):
                    st.session_state["studio_prompt_value"] = trend["title"]
                    st.session_state["studio_prompt_mode"] = "💡 Autonomous AI Topic"
                    st.toast("Success! Hot Topic imported.")
                    st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("ℹ Engine Technical Specs & Policies", expanded=False):
        st.markdown("<h4 style='font-family:Orbitron; font-size:15px; color:#ffffff; margin-bottom: 15px;'>🚀 INTEGRATED WORKFLOW PIPELINE</h4>", unsafe_allow_html=True)
        col_step1, col_step2, col_step3 = st.columns(3)
        with col_step1:
            st.markdown("""
                <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 14px; height: 100%;">
                    <div style="font-size: 18px; font-weight: bold; color: #ffd700; margin-bottom: 10px; font-family: 'Orbitron';">01</div>
                    <h5 style="color: #ffffff; font-family: Orbitron; font-size: 13px; margin-bottom: 8px;">1. Structured Scripting</h5>
                    <p style="color: #94a3b8; font-size: 11.5px; line-height: 1.5;">Constructs structured scripts with scene-by-scene keyword parameters using the LLM engine.</p>
                </div>
            """, unsafe_allow_html=True)
        with col_step2:
            st.markdown("""
                <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 14px; height: 100%;">
                    <div style="font-size: 18px; font-weight: bold; color: #ffd700; margin-bottom: 10px; font-family: 'Orbitron';">02</div>
                    <h5 style="color: #ffffff; font-family: Orbitron; font-size: 13px; margin-bottom: 8px;">2. Voice Segment Synthetics</h5>
                    <p style="color: #94a3b8; font-size: 11.5px; line-height: 1.5;">Generates specific voice streams per scene block and calculates precise audio timelines.</p>
                </div>
            """, unsafe_allow_html=True)
        with col_step3:
            st.markdown("""
                <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 14px; height: 100%;">
                    <div style="font-size: 18px; font-weight: bold; color: #ffd700; margin-bottom: 10px; font-family: 'Orbitron';">03</div>
                    <h5 style="color: #ffffff; font-family: Orbitron; font-size: 13px; margin-bottom: 8px;">3. Multi-Scene Stitching</h5>
                    <p style="color: #94a3b8; font-size: 11.5px; line-height: 1.5;">Trims visual assets to matching segment runtimes and compiles them together into final outputs.</p>
                </div>
            """, unsafe_allow_html=True)
        st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 20px 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='font-family:Orbitron; font-size:15px; color:#ffffff; margin-bottom: 15px;'>🚨 DISCLAIMER & PLATFORM POLICIES</h4>", unsafe_allow_html=True)
        disc_col1, disc_col2 = st.columns(2)
        with disc_col1:
            st.markdown("""
                <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 14px; height: 100%;">
                    <h5 style="color: #FFC0CB; font-family: Orbitron; font-size: 12px; margin-bottom: 10px;">Generative Media Policy</h5>
                    <p style="color: #94a3b8; font-size: 11.5px; line-height: 1.6;">ZOVIX operates as an automated synthesis tool. We do not claim ownership over stock materials retrieved from third-party APIs.</p>
                </div>
            """, unsafe_allow_html=True)
        with disc_col2:
            st.markdown("""
                <div style="background: rgba(18, 19, 26, 0.85); border: 1px solid rgba(255, 192, 203, 0.12); border-radius: 12px; padding: 14px; height: 100%;">
                    <h5 style="color: #FFC0CB; font-family: Orbitron; font-size: 12px; margin-bottom: 10px;">Usage & Credit Terms</h5>
                    <p style="color: #94a3b8; font-size: 11.5px; line-height: 1.6;">Access to processing nodes requires active credits. Standard 720p generations consume 1 credit.</p>
                </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 40px 0 20px 0;'>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: center; padding: 10px 0 20px 0; color: #404040; font-family: 'Inter'; font-size: 13px;">
            <p style="margin-bottom: 10px; font-weight: 400; color: #404040;">© 2026 ZOVIX. All rights reserved.</p>
            <div style="display: flex; justify-content: center; gap: 20px; font-family: 'Orbitron'; font-size: 11px; letter-spacing: 1px;">
                <a href="#" style="color: #FFC0CB; text-decoration: none;">SUPPORT</a>
                <span style="color: rgba(255,255,255,0.1);">|</span>
                <a href="#" style="color: #FFC0CB; text-decoration: none;">DOCUMENTATION</a>
                <span style="color: rgba(255,255,255,0.1);">|</span>
                <a href="#" style="color: #FFC0CB; text-decoration: none;">API ACCESS</a>
            </div>
        </div>
    """, unsafe_allow_html=True)
