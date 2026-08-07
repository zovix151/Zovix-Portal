"""
================================================================================
ZOVIX AI VIDEO GENERATION BACKEND — FastAPI (Production Ready)
================================================================================
Replicate Model:     prunaai/p-video-avatar
Credit System:       Starter (₹49/50cr, max 20s) | Pro (max 60s)
Database:            PostgreSQL (psycopg2) + SQLite fallback for dev
Audio Validation:    mutagen — server-side duration extraction
================================================================================
"""

import os, io, sys, json, time, uuid, logging, traceback
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# DATABASE DRIVERS
# ---------------------------------------------------------------------------
try:
    import psycopg2
    import psycopg2.extras
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
# SETTINGS
# ==========================================================================
class Settings:
    DATABASE_URL: str      = os.getenv("DATABASE_URL", "postgresql://zovix:zovix@localhost:5432/zovix_db")
    DB_ENGINE: str          = os.getenv("DB_ENGINE", "postgres")          # "postgres" | "sqlite"
    SQLITE_PATH: str        = os.getenv("SQLITE_PATH", "zovix_v4.db")
    REPLICATE_API_KEY: str  = os.getenv("REPLICATE_API_KEY", "")
    REPLICATE_MODEL: str    = os.getenv("REPLICATE_MODEL", "prunaai/p-video-avatar")
    STARTER_MAX_DURATION: int = 20                                        # seconds
    PRO_MAX_DURATION: int     = 60                                        # seconds
    COST_PER_SECOND: int      = 1                                         # 1 credit per 1 second
    API_SECRET_KEY: str       = os.getenv("API_SECRET_KEY", "zovix-api-secret-change-me")
    RATE_LIMIT_REQUESTS: int  = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
    RATE_LIMIT_WINDOW: int    = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    HOST: str                 = os.getenv("HOST", "0.0.0.0")
    PORT: int                 = int(os.getenv("PORT", "8000"))
    ENVIRONMENT: str          = os.getenv("ENVIRONMENT", "development")

settings = Settings()

# ==========================================================================
# DATABASE MANAGER
# ==========================================================================
class DatabaseManager:
    """
    PostgreSQL (prod) / SQLite (dev) manager.

    --- users ---
      id              SERIAL PK
      username        TEXT UNIQUE
      email           TEXT UNIQUE
      plan            TEXT   DEFAULT 'starter'   ('starter'|'pro')
      credits         INT    DEFAULT 50
      total_used      INT    DEFAULT 0
      auth_token      TEXT
      created_at      TIMESTAMP
      updated_at      TIMESTAMP

    --- generations ---
      id                   SERIAL PK
      user_id              INT FK → users
      replicate_pred_id    TEXT
      audio_duration       REAL
      credits_deducted     INT
      status               TEXT   ('pending'|'processing'|'completed'|'failed'|'canceled')
      refunded             BOOL
      output_video_url     TEXT
      error_message        TEXT
      created_at           TIMESTAMP

    --- credit_transactions ---
      id              SERIAL PK
      user_id         INT FK → users
      amount          INT    (+credit | -debit)
      type            TEXT   ('deduction'|'refund'|'purchase')
      generation_id   INT FK → generations (nullable)
      description     TEXT
      created_at      TIMESTAMP
    """

    def __init__(self):
        self.engine = settings.DB_ENGINE
        if self.engine == "postgres" and not HAS_POSTGRES:
            logger.warning("psycopg2 not installed → using SQLite")
            self.engine = "sqlite"

    # ------------------------------------------------------------------
    def _conn(self):
        if self.engine == "postgres":
            return psycopg2.connect(settings.DATABASE_URL)
        else:
            c = _sqlite3.connect(settings.SQLITE_PATH)
            c.row_factory = _sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA foreign_keys=ON")
            return c

    # ------------------------------------------------------------------
    def init_schema(self):
        q = self._conn()
        cur = q.cursor()
        try:
            if self.engine == "postgres":
                cur.execute("""CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE, plan TEXT NOT NULL DEFAULT 'starter', credits INTEGER NOT NULL DEFAULT 50, total_used INTEGER NOT NULL DEFAULT 0, auth_token TEXT, created_at TIMESTAMP NOT NULL DEFAULT NOW(), updated_at TIMESTAMP NOT NULL DEFAULT NOW())""")
                cur.execute("""CREATE TABLE IF NOT EXISTS generations (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), replicate_pred_id TEXT, audio_duration REAL, credits_deducted INTEGER, status TEXT NOT NULL DEFAULT 'pending', refunded BOOLEAN NOT NULL DEFAULT FALSE, output_video_url TEXT, error_message TEXT, created_at TIMESTAMP NOT NULL DEFAULT NOW())""")
                cur.execute("""CREATE TABLE IF NOT EXISTS credit_transactions (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), amount INTEGER NOT NULL, type TEXT NOT NULL, generation_id INTEGER REFERENCES generations(id), description TEXT, created_at TIMESTAMP NOT NULL DEFAULT NOW())""")
            else:
                cur.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE, plan TEXT NOT NULL DEFAULT 'starter', credits INTEGER NOT NULL DEFAULT 50, total_used INTEGER NOT NULL DEFAULT 0, auth_token TEXT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
                cur.execute("""CREATE TABLE IF NOT EXISTS generations (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), replicate_pred_id TEXT, audio_duration REAL, credits_deducted INTEGER, status TEXT NOT NULL DEFAULT 'pending', refunded BOOLEAN NOT NULL DEFAULT 0, output_video_url TEXT, error_message TEXT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
                cur.execute("""CREATE TABLE IF NOT EXISTS credit_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), amount INTEGER NOT NULL, type TEXT NOT NULL, generation_id INTEGER REFERENCES generations(id), description TEXT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            q.commit()
            logger.info("DB schema ready.")
        except Exception as e:
            q.rollback()
            logger.error(f"Schema init failed: {e}")
            raise
        finally:
            cur.close()
            q.close()

    # ------------------------------------------------------------------
    def get_user_by_token(self, token: str) -> Optional[Dict]:
        q = self._conn()
        cur = q.cursor()
        try:
            cur.execute("SELECT * FROM users WHERE auth_token = ?" if self.engine == "sqlite" else "SELECT * FROM users WHERE auth_token = %s", (token,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close(); q.close()

    def get_user_by_id(self, uid: int) -> Optional[Dict]:
        q = self._conn()
        cur = q.cursor()
        try:
            cur.execute("SELECT * FROM users WHERE id = ?" if self.engine == "sqlite" else "SELECT * FROM users WHERE id = %s", (uid,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close(); q.close()

    # ------------------------------------------------------------------
    # CREDIT OPERATIONS (atomic)
    # ------------------------------------------------------------------
    def deduct_credits(self, uid: int, amount: int) -> bool:
        """Atomically deduct credits. Returns False if insufficient."""
        q = self._conn()
        cur = q.cursor()
        try:
            if self.engine == "postgres":
                cur.execute("UPDATE users SET credits = credits - %s, total_used = total_used + %s, updated_at = NOW() WHERE id = %s AND credits >= %s", (amount, amount, uid, amount))
            else:
                cur.execute("UPDATE users SET credits = credits - ?, total_used = total_used + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND credits >= ?", (amount, amount, uid, amount))
            ok = cur.rowcount > 0
            q.commit()
            if not ok: q.rollback()
            return ok
        except Exception as e:
            q.rollback(); logger.error(f"deduct_credits({uid}, {amount}): {e}"); return False
        finally:
            cur.close(); q.close()

    def refund_credits(self, uid: int, amount: int) -> bool:
        """Atomically refund credits."""
        q = self._conn()
        cur = q.cursor()
        try:
            if self.engine == "postgres":
                cur.execute("UPDATE users SET credits = credits + %s, updated_at = NOW() WHERE id = %s", (amount, uid))
            else:
                cur.execute("UPDATE users SET credits = credits + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (amount, uid))
            q.commit()
            return True
        except Exception as e:
            q.rollback(); logger.error(f"refund_credits({uid}, {amount}): {e}"); return False
        finally:
            cur.close(); q.close()

    # ------------------------------------------------------------------
    # GENERATION RECORDS
    # ------------------------------------------------------------------
    def create_generation(self, uid: int, audio_dur: float, credits_deducted: int) -> int:
        q = self._conn()
        cur = q.cursor()
        try:
            if self.engine == "postgres":
                cur.execute("INSERT INTO generations (user_id, audio_duration, credits_deducted, status) VALUES (%s, %s, %s, 'pending') RETURNING id", (uid, audio_dur, credits_deducted))
                gid = cur.fetchone()[0]
            else:
                cur.execute("INSERT INTO generations (user_id, audio_duration, credits_deducted, status) VALUES (?, ?, ?, 'pending')", (uid, audio_dur, credits_deducted))
                gid = cur.lastrowid
            q.commit()
            return gid
        except Exception as e:
            q.rollback(); logger.error(f"create_generation: {e}"); raise
        finally:
            cur.close(); q.close()

    def update_generation(self, gid: int, **kwargs):
        q = self._conn()
        cur = q.cursor()
        try:
            fields = []
            vals = []
            for k, v in kwargs.items():
                col = {"replicate_pred_id":"replicate_pred_id","status":"status","output_video_url":"output_video_url","error_message":"error_message","refunded":"refunded"}.get(k, k)
                fields.append(f"{col} = ?" if self.engine == "sqlite" else f"{col} = %s")
                vals.append(v if not isinstance(v, bool) else (int(v) if self.engine == "sqlite" else v))
            if not fields: return
            vals.append(gid)
            sql = f"UPDATE generations SET {', '.join(fields)} WHERE id = ?" if self.engine == "sqlite" else f"UPDATE generations SET {', '.join(fields)} WHERE id = %s"
            cur.execute(sql, vals)
            q.commit()
        except Exception as e:
            q.rollback(); logger.error(f"update_generation: {e}")
        finally:
            cur.close(); q.close()

    # ------------------------------------------------------------------
    # AUDIT LOG
    # ------------------------------------------------------------------
    def log_transaction(self, uid: int, amount: int, ttype: str, gid: Optional[int] = None, desc: str = ""):
        q = self._conn()
        cur = q.cursor()
        try:
            if self.engine == "postgres":
                cur.execute("INSERT INTO credit_transactions (user_id, amount, type, generation_id, description) VALUES (%s, %s, %s, %s, %s)", (uid, amount, ttype, gid, desc))
            else:
                cur.execute("INSERT INTO credit_transactions (user_id, amount, type, generation_id, description) VALUES (?, ?, ?, ?, ?)", (uid, amount, ttype, gid, desc))
            q.commit()
        except Exception as e:
            q.rollback(); logger.error(f"log_transaction: {e}")
        finally:
            cur.close(); q.close()

    def get_generation(self, gid: int, uid: int) -> Optional[Dict]:
        q = self._conn()
        cur = q.cursor()
        try:
            cur.execute("SELECT * FROM generations WHERE id = ? AND user_id = ?" if self.engine == "sqlite" else "SELECT * FROM generations WHERE id = %s AND user_id = %s", (gid, uid))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close(); q.close()


db = DatabaseManager()

# ==========================================================================
# AUDIO DURATION EXTRACTOR
# ==========================================================================
def get_audio_duration(audio_bytes: bytes, filename: str = "audio.mp3") -> float:
    """Extract audio duration in seconds. Supports MP3/WAV/M4A/OGG."""
    ext = os.path.splitext(filename)[1].lower() if filename else ".mp3"
    cls_map = {".mp3": MP3, ".wav": WAVE, ".m4a": MP4, ".aac": MP4, ".ogg": OggFileType, ".flac": OggFileType}
    audio_cls = cls_map.get(ext, MP3)

    for cls in [audio_cls, MP3, WAVE, MP4, OggFileType]:
        try:
            fp = io.BytesIO(audio_bytes)
            return round(cls(fp).info.length, 2)
        except Exception:
            continue

    raise HTTPException(status_code=400, detail="Could not determine audio duration. Please upload a valid MP3/WAV/M4A/OGG file.")

# ==========================================================================
# REPLICATE CLIENT
# ==========================================================================
class ReplicateClient:
    BASE = "https://api.replicate.com/v1"

    def __init__(self, api_key: str):
        self.h = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}

    def create_prediction(self, face_url: str, audio_url: str) -> Dict:
        payload = {"version": None, "input": {"image": face_url, "audio": audio_url}}
        url = f"{self.BASE}/models/{settings.REPLICATE_MODEL}/predictions"
        try:
            r = requests.post(url, headers=self.h, json=payload, timeout=30)
            data = r.json()
            if not r.ok:
                raise HTTPException(status_code=502, detail=f"Replicate error: {data.get('detail', 'Unknown')}")
            logger.info(f"Replicate prediction created: {data.get('id')} | status={data.get('status')}")
            return data
        except requests.exceptions.Timeout:
            raise HTTPException(status_code=504, detail="Replicate API timed out.")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=502, detail=f"Replicate unreachable: {e}")

    def get_prediction(self, pid: str) -> Dict:
        try:
            r = requests.get(f"{self.BASE}/predictions/{pid}", headers=self.h, timeout=15)
            data = r.json()
            if not r.ok:
                raise HTTPException(status_code=502, detail=f"Replicate status check failed: {data.get('detail','')}")
            return data
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=502, detail=f"Replicate status unreachable: {e}")

    def cancel_prediction(self, pid: str) -> bool:
        try:
            return requests.post(f"{self.BASE}/predictions/{pid}/cancel", headers=self.h, timeout=10).ok
        except Exception:
            return False

replicate = ReplicateClient(settings.REPLICATE_API_KEY)

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
# RATE LIMITER (in-memory sliding window)
# ==========================================================================
from collections import defaultdict
_rate_store: Dict[str, List[float]] = defaultdict(list)

def check_rate_limit(uid: int) -> bool:
    key = str(uid); now = time.time()
    _rate_store[key] = [t for t in _rate_store[key] if now - t < settings.RATE_LIMIT_WINDOW]
    if len(_rate_store[key]) >= settings.RATE_LIMIT_REQUESTS:
        return False
    _rate_store[key].append(now)
    return True

# ==========================================================================
# REQUEST / RESPONSE MODELS
# ==========================================================================
class GenRequest(BaseModel):
    audio_url: Optional[str] = Field(None, description="Public audio file URL")
    face_image_url: Optional[str] = Field(None, description="Public face image URL")

class GenResponse(BaseModel):
    success: bool = True
    prediction_id: str
    status: str
    generation_id: int
    credits_deducted: int
    remaining_credits: int
    audio_duration: float
    message: str

class StatusResponse(BaseModel):
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
    logger.info(f"Zovix Backend starting | env={settings.ENVIRONMENT} | db={settings.DB_ENGINE} | model={settings.REPLICATE_MODEL}")
    db.init_schema()
    yield
    logger.info("Zovix Backend shutting down.")

app = FastAPI(title="Zovix AI Video API", version="2.0.0", lifespan=lifespan, docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(HTTPException)
async def http_exc_handler(req: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error_code": f"HTTP_{exc.status_code}", "detail": exc.detail})

@app.exception_handler(Exception)
async def generic_exc_handler(req: Request, exc: Exception):
    logger.error(f"Unhandled: {exc}\n{traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"success": False, "error_code": "INTERNAL_ERROR", "detail": "Unexpected error. Team notified."})

# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"status":"ok","service":"Zovix Backend","version":"2.0.0"}

@app.get("/api/health")
def health():
    try:
        db.get_user_by_id(1)
        db_ok = True
    except Exception:
        db_ok = False
    return {"status":"healthy" if db_ok else "degraded","database":"connected" if db_ok else "disconnected","model":settings.REPLICATE_MODEL,"timestamp":datetime.utcnow().isoformat()}

# =====================================================================
# POST /api/generate-video  (MAIN ENDPOINT)
# =====================================================================
@app.post("/api/generate-video", response_model=GenResponse)
async def generate_video(
    body: GenRequest,
    audio_file: Optional[UploadFile] = File(None),
    face_file: Optional[UploadFile] = File(None),
    user: Dict = Depends(get_current_user),
):
    """
    ## AI Talking-Face Video Generation

    **Flow:**
    1. Auth via Bearer token → load user plan & credits
    2. Download/read audio → extract duration server-side
    3. Validate against plan max (Starter=20s, Pro=60s) — **abort early**
    4. Check credit balance → reject if insufficient
    5. Deduct credits atomically
    6. Call Replicate API (`prunaai/p-video-avatar`)
    7. If Replicate fails → **auto-refund**
    """
    uid: int     = user["id"]
    plan: str    = user.get("plan", "starter")
    credits: int = user.get("credits", 0)

    # --- Rate limit ---
    if not check_rate_limit(uid):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait.")

    # --- Plan max duration ---
    max_dur = settings.STARTER_MAX_DURATION if plan == "starter" else settings.PRO_MAX_DURATION

    # --- Resolve audio bytes ---
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
            raise HTTPException(status_code=400, detail=f"Cannot read audio file: {e}")
    else:
        raise HTTPException(status_code=400, detail="Provide either 'audio_url' or 'audio_file'.")

    # --- Extract duration ---
    duration = get_audio_duration(audio_bytes, audio_filename)
    logger.info(f"User {uid} | duration={duration}s | plan={plan} | max={max_dur}s | credits={credits}")

    # --- Plan duration check (ABORT EARLY) ---
    if duration > max_dur:
        if plan == "starter":
            raise HTTPException(status_code=400, detail=f"Starter plan allows max {max_dur} seconds video. Please upgrade to Pro Plan.")
        else:
            raise HTTPException(status_code=400, detail=f"Pro plan allows max {max_dur} seconds video. Please use shorter audio.")

    # --- Credits needed ---
    needed = max(1, int(duration))  # 1 credit per second, minimum 1

    # --- Credit balance check (ABORT EARLY) ---
    if credits < needed:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Need {needed}, have {credits}.")

    # --- Resolve face image URL ---
    face_url = body.face_image_url or user.get("face_image_url")
    if not face_url:
        raise HTTPException(status_code=400, detail="Face image URL is required. Upload one in your profile.")

    # --- DEDUCT CREDITS (atomic) ---
    if not db.deduct_credits(uid, needed):
        raise HTTPException(status_code=402, detail="Credit deduction failed. Try again.")

    # --- Create generation record ---
    try:
        gid = db.create_generation(uid, duration, needed)
        db.log_transaction(uid, -needed, "deduction", gid, f"Video gen {duration}s")
    except Exception as e:
        db.refund_credits(uid, needed)  # refund on DB error
        logger.error(f"Generation record failed, refunded: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize. Credits refunded.")

    # --- CALL REPLICATE ---
    try:
        pred = replicate.create_prediction(face_url, audio_url if audio_url else "")
    except HTTPException:
        # Auto-refund on Replicate failure
        db.refund_credits(uid, needed)
        db.update_generation(gid, status="failed", error_message="Replicate API call failed", refunded=True)
        db.log_transaction(uid, +needed, "refund", gid, "Auto-refund: Replicate call failed")
        raise
    except Exception as e:
        db.refund_credits(uid, needed)
        db.update_generation(gid, status="failed", error_message=str(e), refunded=True)
        db.log_transaction(uid, +needed, "refund", gid, f"Auto-refund: {str(e)[:200]}")
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}. Credits refunded.")

    # --- Update record with prediction ID ---
    pid = pred.get("id", "")
    db.update_generation(gid, status="processing", replicate_pred_id=pid)

    # --- Remaining ---
    updated = db.get_user_by_id(uid)
    remaining = updated["credits"] if updated else 0

    logger.info(f"✅ Video started | user={uid} | pred={pid} | used={needed}cr | remaining={remaining}cr")
    return GenResponse(
        prediction_id=pid,
        status=pred.get("status", "processing"),
        generation_id=gid,
        credits_deducted=needed,
        remaining_credits=remaining,
        audio_duration=duration,
        message=f"Generation started! {needed} credits used. Estimated 30-120s.",
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

    pid = gen.get("replicate_pred_id")
    status = gen.get("status")
    output = gen.get("output_video_url")
    error = gen.get("error_message")

    if pid:
        try:
            pred = replicate.get_prediction(pid)
            status = pred.get("status", status)
            output = pred.get("output") or output
            error  = pred.get("error") or error

            if status == "succeeded":
                db.update_generation(gid, status="completed", output_video_url=output)
            elif status in ("failed", "canceled"):
                db.update_generation(gid, status="failed", error_message=error or "Replicate failure")
                if not gen.get("refunded"):
                    amt = gen.get("credits_deducted", 0)
                    db.refund_credits(uid, amt)
                    db.update_generation(gid, status="failed", refunded=True)
                    db.log_transaction(uid, +amt, "refund", gid, f"Auto-refund: replicate {status}")
                    logger.info(f"Auto-refunded {amt}cr for user {uid} (gen {gid}, status={status})")
        except Exception as e:
            logger.warning(f"Replicate poll failed: {e}")

    return StatusResponse(prediction_id=pid or "", status=status, output=output, error=error, generation_id=gid)

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
        }
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

    pid = gen.get("replicate_pred_id")
    if pid:
        replicate.cancel_prediction(pid)

    if not gen.get("refunded"):
        amt = gen.get("credits_deducted", 0)
        db.refund_credits(uid, amt)
        db.update_generation(gid, status="canceled", refunded=True, error_message="User canceled")
        db.log_transaction(uid, +amt, "refund", gid, "User canceled generation")

    return {"success": True, "message": "Canceled & refunded.", "generation_id": gid}

# ==========================================================================
# ENTRYPOINT
# ==========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=(settings.ENVIRONMENT == "development"))