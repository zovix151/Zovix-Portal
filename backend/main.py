"""
================================================================================
ZOVIX AI VIDEO GENERATION BACKEND — FastAPI (Production Ready) v4.0
================================================================================
DEEPINFRA ONLY — No Replicate, No Local Scripts.
Model:  PrunaAI/p-video-avatar
Credit: Starter (₹49/50cr, max 20s) | Pro (max 60s)
DB:     PostgreSQL (psycopg2) + SQLite fallback for dev
Audio:  mutagen — server-side duration extraction
================================================================================
"""

import os, io, sys, time, uuid, logging, traceback
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import asynccontextmanager

# ---------------------------------------------------------------------------
# 1. LOAD .env WITH python-dotenv (MUST BE FIRST)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
        print(f"✅ .env loaded from: {_env_path}")
    else:
        load_dotenv()
        print("✅ .env loaded from current directory")
except ImportError:
    print("⚠️  python-dotenv not installed. Using system env vars only.")

import requests
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# DATABASE DRIVERS
# ---------------------------------------------------------------------------
try:
    import psycopg2
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

import sqlite3 as _sqlite3

# ---------------------------------------------------------------------------
# AUDIO DURATION (mutagen)
# ---------------------------------------------------------------------------
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.mp4 import MP4
from mutagen.ogg import OggFileType

# ==========================================================================
# LOGGING
# ==========================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.FileHandler("zovix_backend.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ZovixBackend")

# ==========================================================================
# CONFIGURATION (loaded from .env / OS env)
# ==========================================================================
class Settings:
    # -- Database -----------------------------------------------------------
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://zovix:zovix@localhost:5432/zovix_db")
    DB_ENGINE: str    = os.getenv("DB_ENGINE", "postgres")
    SQLITE_PATH: str  = os.getenv("SQLITE_PATH", "zovix_v4.db")

    # -- DeepInfra (ONLY PROVIDER) ------------------------------------------
    DEEPINFRA_API_KEY: str = (os.getenv("DEEPINFRA_API_KEY") or "").strip().strip('"').strip("'")
    DEEPINFRA_MODEL: str   = os.getenv("DEEPINFRA_MODEL", "PrunaAI/p-video-avatar")
    DEEPINFRA_BASE_URL: str = "https://api.deepinfra.com/v1"
    DEEPINFRA_AVAILABLE: bool = False
    DEEPINFRA_TIMEOUT: int = int(os.getenv("DEEPINFRA_TIMEOUT", "180"))

    # -- Plan Limits --------------------------------------------------------
    STARTER_MAX_DURATION: int = 20
    PRO_MAX_DURATION: int     = 60
    COST_PER_SECOND: int      = 1

    # -- API Security -------------------------------------------------------
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
    RATE_LIMIT_WINDOW: int   = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    HOST: str     = os.getenv("HOST", "0.0.0.0")
    PORT: int     = int(os.getenv("PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    def __init__(self):
        self.DEEPINFRA_AVAILABLE = bool(self.DEEPINFRA_API_KEY and len(self.DEEPINFRA_API_KEY) > 5)

settings = Settings()

# ==========================================================================
# DATABASE MANAGER
# ==========================================================================
class DatabaseManager:
    def __init__(self):
        self.engine = settings.DB_ENGINE
        if self.engine == "postgres" and not HAS_POSTGRES:
            logger.warning("psycopg2 not installed → using SQLite"); self.engine = "sqlite"

    def _conn(self):
        if self.engine == "postgres":
            return psycopg2.connect(settings.DATABASE_URL)
        c = _sqlite3.connect(settings.SQLITE_PATH)
        c.row_factory = _sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON")
        return c

    def init_schema(self):
        q = self._conn(); cur = q.cursor()
        try:
            if self.engine == "postgres":
                cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE, plan TEXT NOT NULL DEFAULT 'starter', credits INTEGER NOT NULL DEFAULT 50, total_used INTEGER NOT NULL DEFAULT 0, auth_token TEXT, created_at TIMESTAMP NOT NULL DEFAULT NOW(), updated_at TIMESTAMP NOT NULL DEFAULT NOW())")
                cur.execute("CREATE TABLE IF NOT EXISTS generations (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), provider TEXT DEFAULT 'deepinfra', provider_pred_id TEXT, audio_duration REAL, credits_deducted INTEGER, status TEXT NOT NULL DEFAULT 'pending', refunded BOOLEAN NOT NULL DEFAULT FALSE, output_video_url TEXT, error_message TEXT, created_at TIMESTAMP NOT NULL DEFAULT NOW())")
                cur.execute("CREATE TABLE IF NOT EXISTS credit_transactions (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), amount INTEGER NOT NULL, type TEXT NOT NULL, generation_id INTEGER REFERENCES generations(id), description TEXT, created_at TIMESTAMP NOT NULL DEFAULT NOW())")
            else:
                cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE, plan TEXT NOT NULL DEFAULT 'starter', credits INTEGER NOT NULL DEFAULT 50, total_used INTEGER NOT NULL DEFAULT 0, auth_token TEXT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)")
                cur.execute("CREATE TABLE IF NOT EXISTS generations (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), provider TEXT DEFAULT 'deepinfra', provider_pred_id TEXT, audio_duration REAL, credits_deducted INTEGER, status TEXT NOT NULL DEFAULT 'pending', refunded BOOLEAN NOT NULL DEFAULT 0, output_video_url TEXT, error_message TEXT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)")
                cur.execute("CREATE TABLE IF NOT EXISTS credit_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), amount INTEGER NOT NULL, type TEXT NOT NULL, generation_id INTEGER REFERENCES generations(id), description TEXT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            q.commit(); logger.info("✅ DB schema ready.")
        except Exception as e:
            q.rollback(); logger.error(f"❌ Schema init: {e}"); raise
        finally:
            cur.close(); q.close()

    def get_user_by_token(self, token: str) -> Optional[Dict]:
        q = self._conn(); cur = q.cursor()
        try:
            cur.execute("SELECT * FROM users WHERE auth_token = ?" if self.engine == "sqlite" else "SELECT * FROM users WHERE auth_token = %s", (token,))
            row = cur.fetchone(); return dict(row) if row else None
        finally: cur.close(); q.close()

    def get_user_by_id(self, uid: int) -> Optional[Dict]:
        q = self._conn(); cur = q.cursor()
        try:
            cur.execute("SELECT * FROM users WHERE id = ?" if self.engine == "sqlite" else "SELECT * FROM users WHERE id = %s", (uid,))
            row = cur.fetchone(); return dict(row) if row else None
        finally: cur.close(); q.close()

    def deduct_credits(self, uid: int, amount: int) -> bool:
        q = self._conn(); cur = q.cursor()
        try:
            if self.engine == "postgres":
                cur.execute("UPDATE users SET credits = credits - %s, total_used = total_used + %s, updated_at = NOW() WHERE id = %s AND credits >= %s", (amount, amount, uid, amount))
            else:
                cur.execute("UPDATE users SET credits = credits - ?, total_used = total_used + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND credits >= ?", (amount, amount, uid, amount))
            ok = cur.rowcount > 0; q.commit()
            if not ok: q.rollback()
            return ok
        except Exception as e: q.rollback(); logger.error(f"deduct_credits: {e}"); return False
        finally: cur.close(); q.close()

    def refund_credits(self, uid: int, amount: int) -> bool:
        q = self._conn(); cur = q.cursor()
        try:
            if self.engine == "postgres": cur.execute("UPDATE users SET credits = credits + %s, updated_at = NOW() WHERE id = %s", (amount, uid))
            else: cur.execute("UPDATE users SET credits = credits + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (amount, uid))
            q.commit(); return True
        except Exception as e: q.rollback(); logger.error(f"refund_credits: {e}"); return False
        finally: cur.close(); q.close()

    def create_generation(self, uid: int, dur: float, deducted: int, provider: str = "deepinfra") -> int:
        q = self._conn(); cur = q.cursor()
        try:
            if self.engine == "postgres":
                cur.execute("INSERT INTO generations (user_id, audio_duration, credits_deducted, status, provider) VALUES (%s,%s,%s,'pending',%s) RETURNING id", (uid, dur, deducted, provider))
                gid = cur.fetchone()[0]
            else:
                cur.execute("INSERT INTO generations (user_id, audio_duration, credits_deducted, status, provider) VALUES (?,?,?,'pending',?)", (uid, dur, deducted, provider))
                gid = cur.lastrowid
            q.commit(); return gid
        except Exception as e: q.rollback(); logger.error(f"create_gen: {e}"); raise
        finally: cur.close(); q.close()

    def update_generation(self, gid: int, **kw):
        q = self._conn(); cur = q.cursor()
        try:
            f, v = [], []
            cm = {"provider_pred_id":"provider_pred_id","status":"status","output_video_url":"output_video_url","error_message":"error_message","refunded":"refunded","provider":"provider"}
            for k, val in kw.items():
                col = cm.get(k, k)
                f.append(f"{col} = ?" if self.engine == "sqlite" else f"{col} = %s")
                v.append(val if not isinstance(val, bool) else (int(val) if self.engine == "sqlite" else val))
            if not f: return
            v.append(gid)
            sql = f"UPDATE generations SET {', '.join(f)} WHERE id = ?" if self.engine == "sqlite" else f"UPDATE generations SET {', '.join(f)} WHERE id = %s"
            cur.execute(sql, v); q.commit()
        except Exception as e: q.rollback(); logger.error(f"update_gen: {e}")
        finally: cur.close(); q.close()

    def log_transaction(self, uid: int, amount: int, ttype: str, gid: Optional[int] = None, desc: str = ""):
        q = self._conn(); cur = q.cursor()
        try:
            if self.engine == "postgres": cur.execute("INSERT INTO credit_transactions (user_id, amount, type, generation_id, description) VALUES (%s,%s,%s,%s,%s)", (uid, amount, ttype, gid, desc))
            else: cur.execute("INSERT INTO credit_transactions (user_id, amount, type, generation_id, description) VALUES (?,?,?,?,?)", (uid, amount, ttype, gid, desc))
            q.commit()
        except Exception as e: q.rollback(); logger.error(f"log_txn: {e}")
        finally: cur.close(); q.close()

    def get_generation(self, gid: int, uid: int) -> Optional[Dict]:
        q = self._conn(); cur = q.cursor()
        try:
            cur.execute("SELECT * FROM generations WHERE id = ? AND user_id = ?" if self.engine == "sqlite" else "SELECT * FROM generations WHERE id = %s AND user_id = %s", (gid, uid))
            row = cur.fetchone(); return dict(row) if row else None
        finally: cur.close(); q.close()

db = DatabaseManager()

# ==========================================================================
# AUDIO DURATION
# ==========================================================================
def get_audio_duration(audio_bytes: bytes, filename: str = "audio.mp3") -> float:
    ext = os.path.splitext(filename)[1].lower() if filename else ".mp3"
    cm = {".mp3": MP3, ".wav": WAVE, ".m4a": MP4, ".aac": MP4, ".ogg": OggFileType, ".flac": OggFileType}
    for cls in [cm.get(ext, MP3), MP3, WAVE, MP4, OggFileType]:
        try: return round(cls(io.BytesIO(audio_bytes)).info.length, 2)
        except Exception: continue
    raise HTTPException(status_code=400, detail="Could not determine audio duration. Upload a valid MP3/WAV/M4A/OGG file.")

# ==========================================================================
# DEEPINFRA CLIENT — THE ONLY PROVIDER
# ==========================================================================
class DeepInfraClient:
    """100% DeepInfra — PrunaAI/p-video-avatar for talking-face video."""

    BASE = "https://api.deepinfra.com/v1"

    def __init__(self, api_key: str):
        self.key = api_key
        self.h = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def create_video(self, face_url: str, audio_url: str) -> Dict:
        """
        POST https://api.deepinfra.com/v1/inference/PrunaAI/p-video-avatar
        Body: {"input": {"image": "<url>", "audio": "<url>"}}

        On error → prints full response to console AND raises HTTPException
        with the raw error body so it's visible in the API response.
        """
        if not self.key:
            raise HTTPException(status_code=502, detail="DEEPINFRA_API_KEY not configured. Set it in .env")

        payload = {"input": {"image": face_url, "audio": audio_url}}
        url = f"{self.BASE}/inference/{settings.DEEPINFRA_MODEL}"

        try:
            logger.info(f"🟢 [DeepInfra] POST {url}")
            r = requests.post(url, headers=self.h, json=payload, timeout=settings.DEEPINFRA_TIMEOUT)

            # --- VISIBLE ERROR LOGGING ---
            if not r.ok:
                print(f"\n{'='*60}")
                print(f"[DeepInfra Error] Status: {r.status_code}")
                print(f"[DeepInfra Error] Body: {r.text}")
                print(f"{'='*60}\n")
                logger.error(f"❌ [DeepInfra] HTTP {r.status_code}: {r.text[:500]}")
                # Pass the RAW error body back so it's visible
                raise HTTPException(
                    status_code=502,
                    detail=f"DeepInfra Error {r.status_code}: {r.text}",
                )

            data = r.json()
            pred_id = data.get("inference_id") or data.get("id", "")
            status = data.get("status", "processing")
            output = data.get("output") or data.get("result")

            logger.info(f"✅ [DeepInfra] ACCEPTED — id={pred_id}, status={status}")
            if output:
                logger.info(f"✅ [DeepInfra] Output URL: {str(output)[:200]}")

            return {
                "id": pred_id,
                "status": status,
                "output": output,
                "raw": data,
            }

        except requests.exceptions.Timeout:
            logger.error(f"❌ [DeepInfra] TIMEOUT after {settings.DEEPINFRA_TIMEOUT}s")
            raise HTTPException(status_code=504, detail=f"DeepInfra timed out after {settings.DEEPINFRA_TIMEOUT}s.")
        except HTTPException:
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ [DeepInfra] Connection error: {e}")
            raise HTTPException(status_code=502, detail=f"DeepInfra connection failed: {e}")
        except Exception as e:
            logger.error(f"❌ [DeepInfra] Unexpected {type(e).__name__}: {e}")
            raise HTTPException(status_code=502, detail=f"DeepInfra: {type(e).__name__}: {e}")

    def get_result(self, inference_id: str) -> Dict:
        """Poll DeepInfra for result."""
        url = f"{self.BASE}/inference/{settings.DEEPINFRA_MODEL}/{inference_id}"
        try:
            r = requests.get(url, headers=self.h, timeout=15)
            d = r.json()
            if not r.ok:
                raise HTTPException(status_code=502, detail=f"DeepInfra status: {d.get('detail','error')}")
            return {"id": d.get("inference_id",""), "status": d.get("status","unknown"), "output": d.get("output"), "error": d.get("error")}
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=502, detail=f"DeepInfra unreachable: {e}")

deepinfra = DeepInfraClient(settings.DEEPINFRA_API_KEY)

# ==========================================================================
# VIDEO GENERATION (DeepInfra only — NO fallback)
# ==========================================================================
def call_deepinfra_video_generation(face_url: str, audio_url: str) -> tuple:
    """
    Calls DeepInfra. That's it. No fallback.
    Returns: ("deepinfra", prediction_id, response_dict)
    Raises HTTPException with full error body on failure.
    """
    if not settings.DEEPINFRA_AVAILABLE:
        raise HTTPException(
            status_code=502,
            detail="DEEPINFRA_API_KEY not configured. Please set it in .env (DEEPINFRA_API_KEY=your_key_here)",
        )

    resp = deepinfra.create_video(face_url, audio_url)
    logger.info(f"✅ VIDEO STARTED VIA DeepInfra: {resp.get('id')}")
    return ("deepinfra", resp.get("id", ""), resp)


def get_prediction_status(provider: str, pred_id: str) -> Dict:
    return deepinfra.get_result(pred_id)

# ==========================================================================
# AUTH
# ==========================================================================
security = HTTPBearer()

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    user = db.get_user_by_token(creds.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")
    return user

# ==========================================================================
# RATE LIMITER
# ==========================================================================
from collections import defaultdict
_rate_store: Dict[str, List[float]] = defaultdict(list)

def check_rate_limit(uid: int) -> bool:
    key = str(uid); now = time.time()
    _rate_store[key] = [t for t in _rate_store[key] if now - t < settings.RATE_LIMIT_WINDOW]
    if len(_rate_store[key]) >= settings.RATE_LIMIT_REQUESTS: return False
    _rate_store[key].append(now); return True

# ==========================================================================
# MODELS
# ==========================================================================
class GenRequest(BaseModel):
    audio_url: Optional[str] = Field(None)
    face_image_url: Optional[str] = Field(None)

class GenResponse(BaseModel):
    success: bool = True
    provider: str = "deepinfra"
    prediction_id: str
    status: str
    generation_id: int
    credits_deducted: int
    remaining_credits: int
    audio_duration: float
    message: str

class StatusResponse(BaseModel):
    provider: str = "deepinfra"
    prediction_id: str
    status: str
    output: Optional[Any] = None
    error: Optional[str] = None
    generation_id: int

# ==========================================================================
# FASTAPI APP
# ==========================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("  ZOVIX BACKEND v4.0 — DeepInfra ONLY")
    print("=" * 60)
    print(f"  Provider  : DeepInfra (PrunaAI/p-video-avatar)")
    print(f"  API Key   : {'✅ CONFIGURED (' + '*' * 8 + settings.DEEPINFRA_API_KEY[-4:] + ')' if settings.DEEPINFRA_AVAILABLE else '❌ MISSING'}")
    print(f"  DB Engine : {settings.DB_ENGINE}")
    print(f"  Env       : {settings.ENVIRONMENT}")
    print("  Replicate : ❌ REMOVED")
    print("  Local     : ❌ DISABLED (cloud only)")
    print("=" * 60)

    if not settings.DEEPINFRA_AVAILABLE:
        print("❌ WARNING: DEEPINFRA_API_KEY not set! Video generation will fail.")

    logger.info(f"DeepInfra={'AVAILABLE' if settings.DEEPINFRA_AVAILABLE else 'UNAVAILABLE'}")
    db.init_schema()
    yield
    logger.info("Shutting down.")

app = FastAPI(title="Zovix AI Video API (DeepInfra Only)", version="4.0.0", lifespan=lifespan, docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(HTTPException)
async def http_exc(req: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error_code": f"HTTP_{exc.status_code}", "detail": exc.detail})

@app.exception_handler(Exception)
async def generic_exc(req: Request, exc: Exception):
    logger.error(f"Unhandled: {exc}\n{traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"success": False, "error_code": "INTERNAL_ERROR", "detail": "Unexpected server error."})

# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "service": "Zovix Backend",
        "version": "4.0.0",
        "provider": "deepinfra",
        "model": settings.DEEPINFRA_MODEL,
        "deepinfra_available": settings.DEEPINFRA_AVAILABLE,
        "mode": "DEEPINFRA_ONLY",
    }

@app.get("/api/health")
def health():
    db_ok = False
    try:
        db.get_user_by_id(1)
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "provider": "deepinfra",
        "model": settings.DEEPINFRA_MODEL,
        "key_configured": settings.DEEPINFRA_AVAILABLE,
        "replicate": "REMOVED",
        "local_fallback": "DISABLED",
        "timestamp": datetime.utcnow().isoformat(),
    }

# =====================================================================
# POST /api/generate-video
# =====================================================================
@app.post("/api/generate-video", response_model=GenResponse)
async def generate_video(
    body: GenRequest,
    audio_file: Optional[UploadFile] = File(None),
    face_file: Optional[UploadFile] = File(None),
    user: Dict = Depends(get_current_user),
):
    """
    ## AI Talking-Face Video Generation (DeepInfra Only)

    **Flow:**
    1. Auth → plan & credits
    2. Audio duration extraction & validation
    3. Plan max check (Starter=20s, Pro=60s) — reject early
    4. Credit balance check
    5. Atomic credit deduction
    6. 🟢 DeepInfra (PrunaAI/p-video-avatar)
    7. Auto-refund on failure
    """
    uid: int     = user["id"]
    plan: str    = user.get("plan", "starter")
    credits: int = user.get("credits", 0)

    if not check_rate_limit(uid):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    max_dur = settings.STARTER_MAX_DURATION if plan == "starter" else settings.PRO_MAX_DURATION

    # Resolve audio
    audio_bytes: Optional[bytes] = None
    audio_url = body.audio_url
    audio_filename = "audio.mp3"

    if audio_url:
        try:
            r = requests.get(audio_url, timeout=30); r.raise_for_status()
            audio_bytes = r.content
            audio_filename = os.path.basename(audio_url.split("?")[0])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot download audio: {e}")
    elif audio_file:
        try:
            audio_bytes = await audio_file.read()
            audio_filename = audio_file.filename or "audio.mp3"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot read audio: {e}")
    else:
        raise HTTPException(status_code=400, detail="Provide 'audio_url' or 'audio_file'.")

    duration = get_audio_duration(audio_bytes, audio_filename)
    logger.info(f"User {uid} | {duration}s | plan={plan} max={max_dur}s | credits={credits}")

    if duration > max_dur:
        if plan == "starter":
            raise HTTPException(status_code=400, detail=f"Starter plan allows max {max_dur}s. Your audio is {duration}s. Upgrade to Pro Plan for up to 60s.")
        raise HTTPException(status_code=400, detail=f"Pro plan allows max {max_dur}s. Your audio is {duration}s. Use shorter audio.")

    needed = max(1, int(duration))

    if credits < needed:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Need {needed}, have {credits}.")

    face_url = body.face_image_url or user.get("face_image_url")
    if not face_url:
        raise HTTPException(status_code=400, detail="Face image URL is required.")

    if not db.deduct_credits(uid, needed):
        raise HTTPException(status_code=402, detail="Credit deduction failed.")

    try:
        gid = db.create_generation(uid, duration, needed, "deepinfra")
        db.log_transaction(uid, -needed, "deduction", gid, f"Video gen {duration}s")
    except Exception as e:
        db.refund_credits(uid, needed)
        logger.error(f"DB record failed, refunded: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize. Credits refunded.")

    # --- CALL DeepInfra ---
    try:
        provider_name, pred_id, pred_data = call_deepinfra_video_generation(face_url, audio_url if audio_url else "")
    except HTTPException:
        db.refund_credits(uid, needed)
        db.update_generation(gid, status="failed", error_message="DeepInfra call failed", refunded=True)
        db.log_transaction(uid, +needed, "refund", gid, "Auto-refund: DeepInfra call failed")
        raise
    except Exception as e:
        db.refund_credits(uid, needed)
        db.update_generation(gid, status="failed", error_message=str(e), refunded=True)
        db.log_transaction(uid, +needed, "refund", gid, f"Auto-refund: {str(e)[:200]}")
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}. Credits refunded.")

    db.update_generation(gid, status="processing", provider_pred_id=pred_id, provider=provider_name)

    updated = db.get_user_by_id(uid)
    remaining = updated["credits"] if updated else 0

    logger.info(f"✅ Video started | user={uid} | pred={pred_id} | used={needed}cr | remain={remaining}cr")
    return GenResponse(
        prediction_id=pred_id,
        status=pred_data.get("status", "processing"),
        generation_id=gid,
        credits_deducted=needed,
        remaining_credits=remaining,
        audio_duration=duration,
        message=f"Generation started via DeepInfra! {needed} credits deducted.",
    )

# =====================================================================
# GET /api/generation/{gid}/status
# =====================================================================
@app.get("/api/generation/{gid}/status", response_model=StatusResponse)
def get_status(gid: int, user: Dict = Depends(get_current_user)):
    uid = user["id"]
    gen = db.get_generation(gid, uid)
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found.")

    pred_id = gen.get("provider_pred_id")
    status = gen.get("status")
    output = gen.get("output_video_url")
    error = gen.get("error_message")

    if pred_id:
        try:
            pred = get_prediction_status("deepinfra", pred_id)
            status = pred.get("status", status)
            output = pred.get("output") or output
            error  = pred.get("error") or error

            if status == "succeeded":
                db.update_generation(gid, status="completed", output_video_url=output)
            elif status in ("failed", "canceled"):
                db.update_generation(gid, status="failed", error_message=error or "DeepInfra failure")
                if not gen.get("refunded"):
                    amt = gen.get("credits_deducted", 0)
                    db.refund_credits(uid, amt)
                    db.update_generation(gid, status="failed", refunded=True)
                    db.log_transaction(uid, +amt, "refund", gid, f"Auto-refund: DeepInfra {status}")
                    logger.info(f"💰 Auto-refunded {amt}cr (gen {gid}, status={status})")
        except Exception as e:
            logger.warning(f"DeepInfra poll error: {e}")

    return StatusResponse(prediction_id=pred_id or "", status=status, output=output, error=error, generation_id=gid)

# =====================================================================
# GET /api/user/profile
# =====================================================================
@app.get("/api/user/profile")
def profile(user: Dict = Depends(get_current_user)):
    plan = user.get("plan", "starter")
    max_dur = settings.STARTER_MAX_DURATION if plan == "starter" else settings.PRO_MAX_DURATION
    return {
        "success": True,
        "profile": {
            "id": user["id"], "username": user.get("username"), "email": user.get("email"),
            "plan": plan, "plan_max_seconds": max_dur, "credits": user.get("credits", 0),
            "total_used": user.get("total_used", 0), "created_at": str(user.get("created_at", "")),
        },
    }

# =====================================================================
# POST /api/generation/{gid}/cancel
# =====================================================================
@app.post("/api/generation/{gid}/cancel")
def cancel_gen(gid: int, user: Dict = Depends(get_current_user)):
    uid = user["id"]
    gen = db.get_generation(gid, uid)
    if not gen:
        raise HTTPException(status_code=404, detail="Not found.")
    if gen.get("status") not in ("pending", "processing"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel status '{gen.get('status')}'.")

    if not gen.get("refunded"):
        amt = gen.get("credits_deducted", 0)
        db.refund_credits(uid, amt)
        db.update_generation(gid, status="canceled", refunded=True, error_message="User canceled")
        db.log_transaction(uid, +amt, "refund", gid, "User canceled")

    return {"success": True, "message": "Canceled & refunded.", "generation_id": gid}

# ==========================================================================
# MAIN
# ==========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=(settings.ENVIRONMENT == "development"))
