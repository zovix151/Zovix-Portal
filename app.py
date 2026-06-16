import os
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
import concurrent.futures
import base64
import urllib.parse
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
import edge_tts
from mutagen.mp3 import MP3
import traceback
import datetime
from PIL import Image, ImageDraw

# --- HUGGINGFACE HUB INTEGRATION (SAFE IMPORT) ---
try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

# --- Razorpay Safe Import ---
try:
    import razorpay
except ImportError:
    razorpay = None

# --- 1. PAGE SETUP & CONFIGURATION ---
st.set_page_config(page_title="ZOVIX - Cinematic AI Generative Engine", layout="wide", page_icon="💎")

# --- PREMIUM THEME INJECTION ---
def set_premium_theme():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght=700;900&family=Inter:wght=300;400;500;600;700;800&family=Orbitron:wght=500;600;800;900&display=swap');

        html, body, .stApp, [data-testid="stAppViewContainer"] {
            background-color: #06070a !important;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(255, 192, 203, 0.03) 0px, transparent 50%),
                radial-gradient(circle at 90% 80%, rgba(124, 58, 237, 0.02) 0px, transparent 50%),
                radial-gradient(circle at 50% 50%, #06070a 0%, #010102 100%) !important;
            color: #f8fafc !important;
            font-family: 'Inter', sans-serif !important;
        }

        /* Custom Cards & Panels Styling */
        div[data-testid="stVerticalBlockBorder"] {
            background: rgba(18, 19, 26, 0.85) !important;
            backdrop-filter: blur(15px) saturate(180%);
            border: 1px solid rgba(255, 192, 203, 0.12) !important;
            border-radius: 12px !important;
            padding: 14px !important; 
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.8) !important;
            margin-bottom: 10px !important;
            transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }

        /* Video Box Constraints */
        div[data-testid="stVideo"], 
        div[data-testid="stVideo"] video,
        .stVideo {
            max-height: 380px !important; 
            width: 100% !important;
            max-width: 100% !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            border: 2px solid rgba(236, 72, 153, 0.3) !important;
            background: #000000 !important;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.7) !important;
            object-fit: contain !important;
        }

        /* Uniform General Buttons */
        .stButton > button {
            background: #FFFFFF !important;
            background-color: #FFFFFF !important;
            color: #1F2937 !important;
            font-weight: 800 !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 13px !important;
            border-radius: 6px !important;
            border: 1.5px solid #CBD5E1 !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
            text-transform: uppercase;
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

        /* Scrollable Project History Container */
        .scroll-archive-wrapper {
            max-height: 250px !important;
            overflow-y: auto !important;
            padding-right: 4px;
            margin-bottom: 10px;
        }
        .scroll-archive-wrapper::-webkit-scrollbar {
            width: 4px;
        }
        .scroll-archive-wrapper::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.02);
        }
        .scroll-archive-wrapper::-webkit-scrollbar-thumb {
            background: #EC4899;
            border-radius: 4px;
        }

        /* Exit Button & Generate Button Exact Sizing Match rules */
        div.exit-btn-wrapper, div.generate-btn-wrapper {
            display: inline-block;
            width: auto;
        }
        
        div.exit-btn-wrapper button, 
        div.exit-btn-wrapper .stButton > button,
        div.generate-btn-wrapper button,
        div.generate-btn-wrapper .stButton > button {
            width: 160px !important;
            height: 40px !important;
            min-width: 160px !important;
            max-width: 160px !important;
            min-height: 40px !important;
            max-height: 40px !important;
            line-height: 40px !important;
            padding: 0px !important;
            font-size: 13px !important;
            font-weight: 800 !important;
            font-family: 'Orbitron', sans-serif !important;
            text-transform: uppercase !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        /* SELECTED option button styling */
        div.selected-opt-wrap button,
        div.selected-opt-wrap .stButton > button,
        div.selected-opt-wrap div[data-testid="stButton"] button {
            background: #EC4899 !important;
            background-color: #EC4899 !important;
            background-image: none !important;
            color: #FFFFFF !important;
            border: 2px solid #EC4899 !important;
            box-shadow: 0 0 12px rgba(236, 72, 153, 0.45) !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            height: 48px !important;
            text-transform: none !important;
            border-radius: 8px !important;
            width: 100% !important;
            white-space: normal !important;
            word-wrap: break-word !important;
        }
        div.selected-opt-wrap button:hover,
        div.selected-opt-wrap .stButton > button:hover,
        div.selected-opt-wrap div[data-testid="stButton"] button:hover {
            background: #db2777 !important;
            background-color: #db2777 !important;
            border-color: #db2777 !important;
            color: #FFFFFF !important;
        }

        /* Unselected option button styling */
        div.unselected-opt-wrap button,
        div.unselected-opt-wrap .stButton > button,
        div.unselected-opt-wrap div[data-testid="stButton"] button {
            background: #FFFFFF !important;
            background-color: #FFFFFF !important;
            background-image: none !important;
            color: #1F2937 !important;
            border: 1.5px solid #CBD5E1 !important;
            box-shadow: none !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            height: 48px !important;
            text-transform: none !important;
            border-radius: 8px !important;
            width: 100% !important;
            white-space: normal !important;
            word-wrap: break-word !important;
        }
        div.unselected-opt-wrap button:hover,
        div.unselected-opt-wrap .stButton > button:hover,
        div.unselected-opt-wrap div[data-testid="stButton"] button:hover {
            background: #F8FAFC !important;
            background-color: #F8FAFC !important;
            color: #000000 !important;
            border-color: #94A3B8 !important;
        }

        /* Custom Social Integration Wrappers */
        div.google-wrap button, div.google-wrap .stButton > button {
            background: #FFFFFF !important;
            color: #1F2937 !important;
            border: 1.5px solid #CBD5E1 !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            text-transform: none !important;
            border-radius: 6px !important;
        }
        div.facebook-wrap button, div.facebook-wrap .stButton > button {
            background: #1877F2 !important;
            color: #FFFFFF !important;
            border: 1.5px solid #1877F2 !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            text-transform: none !important;
            border-radius: 6px !important;
        }
        div.facebook-wrap button:hover, div.facebook-wrap .stButton > button:hover {
            background: #166FE5 !important;
            color: #FFFFFF !important;
            border-color: #166FE5 !important;
            box-shadow: 0 4px 12px rgba(24, 119, 242, 0.3) !important;
        }

        /* Brand Elements CSS */
        .brand-text-gold {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 38px !important;
            font-weight: 900 !important;
            letter-spacing: 4px;
            background: linear-gradient(135deg, #fffbeb 0%, #fbbf24 60%, #b8860b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            padding: 0;
            display: inline-block;
        }

        .screenshot-card-panel {
            background: #111218;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
        }

        .system-metrics-header {
            font-size: 11px;
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 1.5px;
            color: #a0a0a0 !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 6px;
            margin-bottom: 10px;
            text-transform: uppercase;
        }

        .guide-icon-row {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        .guide-icon-box {
            flex: 1;
            background: #1A1C24;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .guide-icon-box:hover {
            border-color: #ffd700;
            background: rgba(255, 215, 0, 0.04);
        }

        /* Bottom Feature Cards */
        .leonardo-feature-card {
            background: linear-gradient(145deg, rgba(16, 16, 22, 0.9) 0%, rgba(8, 8, 12, 0.98) 100%);
            border: 1px solid rgba(255, 192, 203, 0.1);
            padding: 24px 20px;
            border-radius: 12px;
            transition: all 0.3s ease;
            height: 100%;
        }

        .leonardo-feature-card:hover {
            border-color: rgba(255, 192, 203, 0.25);
            transform: translateY(-2px);
        }

        .compact-label {
            font-family: 'Orbitron', sans-serif;
            font-size: 11px;
            color: #a0a0a0 !important;
            letter-spacing: 1.5px;
            margin-top: 15px;
            margin-bottom: 6px;
            text-transform: uppercase;
        }

        .canvas-container-box {
            background-color: #000000 !important;
            border: 2px solid rgba(236, 72, 153, 0.3) !important;
            border-radius: 14px;
            padding: 12px;
            width: 100% !important;
            max-width: 100% !important;
            height: 380px !important; 
            min-height: 380px !important;
            max-height: 380px !important;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.85);
            overflow: hidden !important;
        }

        .pulse-indicator {
            width: 8px;
            height: 8px;
            background-color: #10b981;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
            animation: pulse-green 1.6s infinite;
            vertical-align: middle;
        }

        @keyframes pulse-green {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        /* --- MOBILE OPTIMIZATION OVERRIDES --- */
        @media (max-width: 768px) {
            .brand-text-gold {
                font-size: 44px !important;
                letter-spacing: 2px !important;
                text-align: center;
                display: block !important;
                margin: 15px auto !important;
                text-align: center !important;
            }
            div[data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
                margin-bottom: 15px !important;
            }
            .canvas-container-box {
                height: 300px !important;
                min-height: 300px !important;
            }
            div.exit-btn-wrapper button, 
            div.exit-btn-wrapper .stButton > button,
            div.generate-btn-wrapper button,
            div.generate-btn-wrapper .stButton > button {
                width: 100% !important;
                max-width: 100% !important;
                min-width: 100% !important;
                height: 44px !important;
            }
            .leonardo-feature-card {
                padding: 18px 14px !important;
                margin-bottom: 12px !important;
            }
            html, body, .stApp {
                background-attachment: scroll !important;
            }
            div[data-testid="stVerticalBlockBorder"] {
                padding: 10px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

set_premium_theme()

# --- 2. DEPLOYMENT READY SECRETS RESOLUTION ---
load_dotenv()

def get_system_secret(key, default_val=None):
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

try:
    if razorpay is not None:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID or "mock", RAZORPAY_KEY_SECRET or "mock"))
    else:
        razorpay_client = None
except Exception:
    razorpay_client = None

try:
    from google import genai
    from google.genai import types
    has_genai = True
except ImportError:
    has_genai = False

# --- 3. SQLite MONETIZATION, SESSION, AND CACHE DATABASE ---
def init_database():
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        # 1. Sabse pehle users table banao saare naye columns ke sath
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                credits REAL DEFAULT 0,
                xp_points REAL DEFAULT 0,
                streak_count INTEGER DEFAULT 0,
                last_claim_date TEXT,
                voucher_credits INTEGER DEFAULT 0,
                voucher_expires_at TEXT DEFAULT ''
            )
        """)
        
        # 2. History table banao
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
        
        # 3. Cache table banao
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                prompt TEXT PRIMARY KEY,
                cached_path TEXT,
                timestamp TEXT
            )
        """)
        
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"Database Init Error: {e}")
    finally:
        conn.close()

# Iske thik niche dhyan se check kar lena ki init_database() call ho raha ho
init_database()

# --- VOUCHER CHECK & DECAY SYSTEM ---
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
                expires_at = datetime.datetime.fromisoformat(expires_at_str)
                if datetime.datetime.now() > expires_at:
                    # Temporary voucher credits have expired! Revert to 0.
                    cursor.execute("UPDATE users SET voucher_credits = 0, voucher_expires_at = '' WHERE username = ?", (username,))
                    conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

# Database helpers
def authenticate_user_db(username, password):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row and row[0] == password:
            return True
    except Exception:
        pass
    finally:
        conn.close()
    return False

def register_user_db(username, password):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        # 1. Pehle ye confirm karega ki agar users table nahi hai toh ban jaye (Saare V3 Columns ke sath)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                credits REAL DEFAULT 0,
                xp_points REAL DEFAULT 0,
                streak_count INTEGER DEFAULT 0,
                last_claim_date TEXT,
                voucher_credits INTEGER DEFAULT 0,
                voucher_expires_at TEXT DEFAULT ''
            )
        """)
        
        # 2. Fir user ko insert karega (8 columns = 8 placeholders)
        cursor.execute(
            "INSERT INTO users (username, password, credits, xp_points, streak_count, last_claim_date, voucher_credits, voucher_expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (username, password, 0, 0, 0, '', 0, '')
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    except sqlite3.OperationalError as e:
        print(f"Database Error: {e}")
        success = False
    finally:
        conn.close()
    return success

# --- DIRECT SOCIAL LOGIN/REGISTER FLOW ---
def login_or_register_social(email, platform):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT username FROM users WHERE username = ?", (email,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO users (username, password, credits, xp_points, streak_count, last_claim_date, voucher_credits, voucher_expires_at) VALUES (?, ?, 100, 0, 0, '', 0, '')", 
                           (email, f"social_{platform.lower()}"))
            conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_user_credits_db(username):
    check_and_expire_vouchers(username) # Ensure voucher validity
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    row = None
    try:
        cursor.execute("SELECT credits, voucher_credits FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
    except Exception:
        pass
    finally:
        conn.close()
    if row:
        return row[0] + row[1] # Sum of standard + active voucher credits
    return 0

def add_credits(username, amount, credit_type="standard"):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        if credit_type == "voucher":
            expiry_time = (datetime.datetime.now() + datetime.timedelta(hours=24)).isoformat()
            cursor.execute("UPDATE users SET voucher_credits = voucher_credits + ?, voucher_expires_at = ? WHERE username = ?", 
                           (amount, expiry_time, username))
        else:
            cursor.execute("UPDATE users SET credits = credits + ? WHERE username = ?", (amount, username))
        conn.commit()
    except Exception:
        pass
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
            # Deduct from temporary voucher credits first (expiring resource)
            if v_credits >= amount:
                new_v = v_credits - amount
                cursor.execute("UPDATE users SET voucher_credits = ? WHERE username = ?", (new_v, username))
            else:
                remaining = amount - v_credits
                cursor.execute("UPDATE users SET voucher_credits = 0, credits = MAX(0, credits - ?) WHERE username = ?", (remaining, username))
            conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def get_user_xp_db(username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    row = None
    try:
        cursor.execute("SELECT xp_points FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
    except Exception:
        pass
    finally:
        conn.close()
    return row[0] if row and row[0] is not None else 0

def update_user_xp_db(username, xp_amount):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET xp_points = xp_points + ? WHERE username = ?", (xp_amount, username))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def get_user_streak_info(username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    row = None
    try:
        cursor.execute("SELECT streak_count, last_claim_date FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
    except Exception:
        pass
    finally:
        conn.close()
    return row if row else (0, "")

def claim_daily_reward_db(username):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    today_str = datetime.date.today().isoformat()
    try:
        cursor.execute("SELECT last_claim_date, streak_count FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            last_claim, streak = row[0], row[1]
            if last_claim == today_str:
                return False, streak, "Already claimed today! Return tomorrow to keep your streak hot."
            
            yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
            new_streak = streak + 1 if last_claim == yesterday_str else 1
            reward_credits = 5 + min(new_streak, 5)
            
            cursor.execute(
                "UPDATE users SET credits = credits + ?, streak_count = ?, last_claim_date = ? WHERE username = ?",
                (reward_credits, new_streak, today_str, username)
            )
            conn.commit()
            return True, new_streak, f"Successfully claimed! Received +{reward_credits} Credits."
    except Exception as e:
        return False, 0, f"Error: {str(e)}"
    finally:
        conn.close()
    return False, 0, "User not found."

def credit_check(username, required_credits):
    return get_user_credits_db(username) >= required_credits

def save_render_to_db(username, file_name, prompt, path):
    conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        timestamp = time.strftime("%b %d, %Y - %I:%M %p")
        cursor.execute("INSERT OR IGNORE INTO history (username, file_name, timestamp, prompt, path) VALUES (?, ?, ?, ?, ?)",
                       (username, file_name, timestamp, prompt, path))
        conn.commit()
    except Exception:
        pass
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
    except Exception:
        pass
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
    except Exception:
        pass
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
    except Exception:
        pass
    finally:
        conn.close()

def create_payment_order(amount_paise):
    if razorpay_client and RAZORPAY_KEY_ID != "mock":
        try:
            data = {"amount": amount_paise, "currency": "INR", "receipt": f"receipt_{int(time.time())}"}
            return razorpay_client.order.create(data=data)
        except Exception:
            pass
    return {"id": f"order_mock_{uuid.uuid4().hex[:8]}", "amount": amount_paise}


# --- 4. ENGAGEMENT ENGINE PORTFOLIO STORAGE (renders_history.json) ---
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
    except Exception:
        pass

def load_from_json_history(username):
    history_file = "renders_history.json"
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, "r") as f:
            data = json.load(f)
        return [item for item in data if item.get("username") == username]
    except Exception:
        return []


# --- 5. ENGINE RESOURCE CACHING ---
@st.cache_resource
def verify_system_folders():
    os.makedirs("saved_renders", exist_ok=True)
    os.makedirs("temp_scenes", exist_ok=True)
    os.makedirs("assets", exist_ok=True)
    os.makedirs(os.path.join("assets", "cache"), exist_ok=True)
    return "Ready"

verify_system_folders()

def find_valid_logo_path():
    candidates = ["14758253318608497028.jpeg", "logo.png", "watermarked_img_368871974808060610.png"]
    for candidate in candidates:
        for path in [candidate, os.path.join(os.getcwd(), candidate)]:
            if os.path.exists(path):
                return path
    return None

def get_base64_img_raw(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

# --- 6. STATE INITIALIZATION ---
if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "landing" 
if "logged_user" not in st.session_state:
    st.session_state["logged_user"] = ""
if "render_done" not in st.session_state:
    st.session_state["render_done"] = False
if "render_failed" not in st.session_state:
    st.session_state["render_failed"] = False
if "total_generated" not in st.session_state:
    st.session_state["total_generated"] = 14280
if "total_downloads" not in st.session_state:
    st.session_state["total_downloads"] = 9845
if "trigger_render" not in st.session_state:
    st.session_state["trigger_render"] = False
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "Enterprise Dark"
if "history_renders" not in st.session_state:
    st.session_state["history_renders"] = []
if "studio_prompt_value" not in st.session_state:
    st.session_state["studio_prompt_value"] = ""
if "studio_prompt_mode" not in st.session_state:
    st.session_state["studio_prompt_mode"] = "💡 Autonomous AI Topic"
if "studio_active_mode" not in st.session_state:
    st.session_state["studio_active_mode"] = "Cinematic Engine Mode"
if "workshop_active_image" not in st.session_state:
    st.session_state["workshop_active_image"] = None
if "active_svd_video" not in st.session_state:
    st.session_state["active_svd_video"] = None

# Engagement Engine State Parameters
if "xp_points" not in st.session_state:
    st.session_state["xp_points"] = 0
if "creator_level" not in st.session_state:
    st.session_state["creator_level"] = 1

# Persistent Configuration Selections
if "aspect_ratio" not in st.session_state:
    st.session_state["aspect_ratio"] = "📐 9:16 Vertical (Shorts/Reels)"
if "voice_profile" not in st.session_state:
    st.session_state["voice_profile"] = "Drew (Premium Male Voice)"
if "duration_choice" not in st.session_state:
    st.session_state["duration_choice"] = "⏱️ Quick Format Shorts (10-15s)"
if "language_choice" not in st.session_state:
    st.session_state["language_choice"] = "🇮🇳 Hinglish (Fluent Hindi Mix)"
if "model_choice" not in st.session_state:
    st.session_state["model_choice"] = "🤖 gemini-2.5-flash (Fast Stream Processing)"
if "res_choice" not in st.session_state:
    st.session_state["res_choice"] = "720p (1 Credit)"

if st.session_state["is_logged_in"] and st.session_state["logged_user"]:
    check_and_expire_vouchers(st.session_state["logged_user"])
    st.session_state["history_renders"] = load_renders_history_db(st.session_state["logged_user"])
    st.session_state["xp_points"] = get_user_xp_db(st.session_state["logged_user"])
    st.session_state["creator_level"] = 1 + (st.session_state["xp_points"] // 100)

# --- 7. PYDANTIC SCHEMAS ---
class SceneDetail(BaseModel):
    scene_text: str = Field(description="The portion of script written specifically for this scene narration.")
    search_keyword: str = Field(description="Strictly 2 to 4 premium English descriptive keywords. Do not use Hindi language words.")
    duration: int = Field(description="Estimated duration in seconds for this scene segment.")

class VideoScriptBreakdown(BaseModel):
    scenes: List[SceneDetail]
    music_mood: str = Field(description="The emotional mood/vibe for background music: 'uplifting', 'dramatic', 'calm', 'energetic', 'mysterious', or 'cinematic'.")

# --- 8. MOOD-TO-MUSIC MAPPING ---
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
    target_path = os.path.join(base_path, f"{mood}.mp3")
    default_path = os.path.join(base_path, "default.mp3")
    if os.path.exists(target_path):
        return target_path
    return default_path

# --- 9. AUDIO METRICS UTILITY ---
def get_audio_duration(audio_path):
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

def get_hwaccel_args():
    if getattr(get_hwaccel_args, "cached", None) is not None:
        return get_hwaccel_args.cached
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-hwaccel", "auto", "-h"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        enabled = result.returncode == 0
    except Exception:
        enabled = False
    get_hwaccel_args.cached = ["-hwaccel", "auto"] if enabled else []
    return get_hwaccel_args.cached

def get_video_resolution(video_path):
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

def parse_tagged_script(script_text):
    paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]
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
        scenes_mapped.append({
            "scene_text": clean_text,
            "search_keyword": keyword,
            "duration": 5
        })
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

# --- 10. MODULAR ENGINES IMPLEMENTATION ---

class ScriptingEngine:
    @staticmethod
    def generate_script(topic, duration_choice, selected_model, language_choice):
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
        except Exception:
            pass
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
        except Exception: 
            pass
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
            headers = {
                "authorization": f"Bearer {st_key}",
                "accept": "image/*"
            }
            data = {
                "prompt": f"Cinematic masterpiece, highly detailed: {prompt}",
                "output_format": "png",
                "aspect_ratio": sd_aspect
            }
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
            except Exception:
                pass

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
        except Exception:
            pass

        return False

    @staticmethod
    def convert_image_to_video(image_path, output_video_path, duration, res_width, res_height):
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


# --- 11. STRICT VIDEO VALIDATOR WITH CACHING ---
def get_scene_asset(description, output_filename):
    try:
        cached_path = get_cached_clip(description)
        if cached_path and os.path.exists(cached_path):
            shutil.copy(cached_path, output_filename)
            return True

        if VisualEngine.fetch_pexels_clip(description, output_filename):
            cache_dir = os.path.join("assets", "cache")
            permanent_path = os.path.join(cache_dir, f"cache_{uuid.uuid4().hex[:8]}.mp4")
            shutil.copy(output_filename, permanent_path)
            cache_clip(description, permanent_path)
            return True
            
        if VisualEngine.fetch_pixabay_clip(description, output_filename):
            cache_dir = os.path.join("assets", "cache")
            permanent_path = os.path.join(cache_dir, f"cache_{uuid.uuid4().hex[:8]}.mp4")
            shutil.copy(output_filename, permanent_path)
            cache_clip(description, permanent_path)
            return True
    except Exception:
        pass
    return False


# --- 11B. VISUAL WORKSHOP ENGINE ---
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
        headers = {
            "authorization": f"Bearer {api_key}",
            "accept": "image/*"
        }
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
            encoded_neg = urllib.parse.quote(negative_prompt.strip())
            poll_url += f"&negative={encoded_neg}"
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
        }
        
        response = requests.get(poll_url, headers=headers, timeout=25)
        if response.status_code == 200 and len(response.content) > 10000:
            output_path = f"workshop_output_{uuid.uuid4().hex[:6]}.png"
            with open(output_path, "wb") as f:
                f.write(response.content)
            return output_path
    except Exception:
        pass

    pexels_key = os.getenv("PEXELS_API_KEY") or get_system_secret("PEXELS_API_KEY")
    if pexels_key:
        try:
            clean_query = prompt.replace('"', '').replace("'", "").strip()
            url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(clean_query)}&per_page=10"
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
                            output_path = f"workshop_output_{uuid.uuid4().hex[:6]}.png"
                            with open(output_path, "wb") as f:
                                f.write(img_res.content)
                            return output_path
        except Exception:
            pass

    pixabay_key = os.getenv("PIXABAY_API_KEY") or get_system_secret("PIXABAY_API_KEY")
    if pixabay_key:
        try:
            clean_query = prompt.replace('"', '').replace("'", "").strip()
            url = f"https://pixabay.com/api/?key={pixabay_key}&q={urllib.parse.quote(clean_query)}&image_type=photo&per_page=10"
            res = requests.get(url, timeout=12)
            if res.status_code == 200:
                data = res.json()
                hits = data.get("hits", [])
                if hits:
                    chosen_hit = random.choice(hits)
                    img_url = chosen_hit.get("largeImageURL") or chosen_hit.get("webformatURL")
                    if img_url:
                        img_res = requests.get(img_url, timeout=15)
                        if img_res.status_code == 200 and len(img_res.content) > 10000:
                            output_path = f"workshop_output_{uuid.uuid4().hex[:6]}.png"
                            with open(output_path, "wb") as f:
                                f.write(img_res.content)
                            return output_path
        except Exception:
            pass

    try:
        clean_query = prompt.replace('"', '').replace("'", "").strip()
        unsplash_url = f"https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w={width}&h={height}&q=80"
        if "village" in clean_query.lower():
            unsplash_url = f"https://images.unsplash.com/photo-1582213782179-e0d53f98f2ca?auto=format&fit=crop&w={width}&h={height}&q=80"
        
        response = requests.get(unsplash_url, timeout=20)
        if response.status_code == 200 and len(response.content) > 10000:
            output_path = f"workshop_output_{uuid.uuid4().hex[:6]}.png"
            with open(output_path, "wb") as f:
                f.write(response.content)
            return output_path
    except Exception:
        pass

    try:
        img = Image.new("RGB", (width, height), color=(18, 19, 26))
        d = ImageDraw.Draw(img)
        d.rectangle([(10, 10), (width - 10, height - 10)], outline=(236, 72, 153), width=4)
        d.line([(10, 10), (width-10, height-10)], fill=(236, 72, 153, 100), width=2)
        d.line([(10, height-10), (width-10, 10)], fill=(236, 72, 153, 100), width=2)
        output_path = f"workshop_output_{uuid.uuid4().hex[:6]}.png"
        img.save(output_path)
        return output_path
    except Exception:
        pass
        
    return None


# --- I2V BACKEND SVD ENGINE (ROBUST MULTI-TIER) ---
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
                'ffmpeg', '-y', '-loop', '1', '-i', image_path,
                '-t', '4',
                '-vf', f"zoompan=z='min(zoom+0.0015,1.5)':d=96:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720",
                '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-r', '24', output_video_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(output_video_path):
                video_path = output_video_path
        except Exception:
            pass

    return video_path


# --- LUMA & RUNWAY AI VIDEO GENERATION UTILITY ---
def generate_ai_video(prompt):
    luma_key = os.getenv("LUMA_API_KEY") or get_system_secret("LUMA_API_KEY")
    runway_key = os.getenv("RUNWAY_API_KEY") or get_system_secret("RUNWAY_API_KEY")
    
    if luma_key:
        url = "https://api.lumalabs.ai/dream-machine/v1/generations"
        headers = {
            "Authorization": f"Bearer {luma_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": prompt,
            "aspect_ratio": "16:9"
        }
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
        except Exception:
            pass

    if runway_key:
        url = "https://api.runwayml.com/v1/tasks"
        headers = {
            "Authorization": f"Bearer {runway_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06"
        }
        payload = {
            "taskType": "text_to_video",
            "promptText": prompt
        }
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
        except Exception:
            pass

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
        except Exception: 
            pass
        return False

    @staticmethod
    def run_fallback_tts(text, output_filename, language_choice, voice_profile):
        safe_remove_file(output_filename)
        is_male = "Drew" in voice_profile or "Male" in voice_profile
        if "English" in language_choice:
            voice_name = "en-US-GuyNeural" if is_male else "en-US-AriaNeural"
        else:
            voice_name = "hi-IN-MadhurNeural" if is_male else "hi-IN-SwaraNeural"
        run_async_in_thread(edge_tts.Communicate(text, voice_name).save(output_filename))


class StitcherEngine:
    @staticmethod
    def generate_ai_video(image_path, output_video_path):
        stability_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")
        if not stability_key:
            return False
            
        url = "https://api.stability.ai/v2beta/image-to-video"
        headers = {
            "authorization": f"Bearer {stability_key}"
        }
        
        try:
            with open(image_path, "rb") as img_file:
                files = {
                    "image": img_file
                }
                data = {
                    "seed": 0,
                    "cfg_scale": 1.8,
                    "motion_bucket_id": 127
                }
                response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                
            if response.status_code != 200:
                return False
                
            generation_id = response.json().get("id")
            if not generation_id:
                return False
                
            result_url = f"https://api.stability.ai/v2beta/image-to-video/result/{generation_id}"
            headers_get = {
                "authorization": f"Bearer {stability_key}",
                "accept": "video/*"
            }
            
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
    def generate_smart_fallback_motion(text, image_path, output_video_path, status_dict=None):
        os.makedirs("temp_scenes", exist_ok=True)
        safe_remove_file(output_video_path)

        if status_dict is not None:
            status_dict["status_text"] = "Initiating Cinematic Engine..."
        
        runway_key = os.getenv("RUNWAY_API_KEY") or get_system_secret("RUNWAY_API_KEY")
        if runway_key:
            try:
                video_url = generate_ai_video(text)
                if video_url:
                    with requests.get(video_url, stream=True, timeout=20) as r:
                        if r.status_code == 200:
                            with open(output_video_path, "wb") as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 100:
                                return True
            except Exception:
                pass

        if status_dict is not None:
            status_dict["status_text"] = "Switching to Fallback Motion..."
        
        hf_key = os.getenv("HUGGINGFACE_API_KEY") or get_system_secret("HUGGINGFACE_API_KEY")
        if InferenceClient is not None and hf_key and image_path and os.path.exists(image_path):
            try:
                try:
                    client_hf = InferenceClient(token=hf_key)
                except Exception:
                    client_hf = InferenceClient(api_key=hf_key)
                    
                with open(image_path, "rb") as img_file:
                    img_data = img_file.read()
                
                response = client_hf.post(
                    model="stabilityai/stable-video-diffusion-img2vid-xt",
                    data=img_data
                )
                if response and len(response) > 1000:
                    with open(output_video_path, "wb") as out_f:
                        out_f.write(response)
                    return True
            except Exception:
                pass

        if status_dict is not None:
            status_dict["status_text"] = "Applying Morphing Effects..."
            
        fallback_source_image = image_path
        workshop_img = st.session_state.get("workshop_active_image")

        if not fallback_source_image or not os.path.exists(fallback_source_image):
            if workshop_img and os.path.exists(workshop_img):
                fallback_source_image = workshop_img
            else:
                fallback_source_image = os.path.join("temp_scenes", f"temp_solid_canvas_{uuid.uuid4().hex[:6]}.png")
                cmd_img = [
                    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=#050508:s=1280x720',
                    '-vframes', '1', fallback_source_image
                ]
                subprocess.run(cmd_img, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            cmd = [
                'ffmpeg', '-y', '-loop', '1', '-i', fallback_source_image,
                '-t', '3',
                '-vf', "zoompan=z='min(zoom+0.0015,1.5)':d=72:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720",
                '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-r', '24', output_video_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 1000:
                return True
        except Exception:
            pass

        return create_emergency_solid_clip(output_video_path, 3.0, 1280, 720)

    @staticmethod
    def build_scene_stitched_video_isolated(scenes_data, video_output, size_choice, voice_profile, language_choice, bgm_path=None, bgm_volume=0.3, music_mood=None, status_dict=None):
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
                status_dict["status_text"] = f"Processing scene {idx+1}: Synthesizing speech track..."

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
                create_emergency_solid_clip(audio_segment_path, 5.0, res_width, res_height)

            dur = get_audio_duration(audio_segment_path)
            if dur <= 0:
                dur = 5.0

            raw_video_path = os.path.join(workspace_dir, f"temp_raw_vid_{idx}.mp4")
            
            if status_dict is not None:
                status_dict["status_text"] = f"Processing scene {idx+1}: Searching stock clip..."
                
            success = get_scene_asset(description=kw, output_filename=raw_video_path)

            if not success or not os.path.exists(raw_video_path) or os.path.getsize(raw_video_path) < 1000:
                warning_msg = f"Warning: Scene video not found, generating AI video..."
                if status_dict is not None:
                    status_dict["warning_text"] = warning_msg
                    status_dict["status_text"] = f"Generating AI Video for scene {idx+1}..."
                
                sd_temp_img = os.path.join(workspace_dir, f"temp_sd_base_{idx}.png")
                sd_success = VisualEngine.generate_sd_core_image(text, sd_temp_img, size_choice)
                
                ai_video_success = StitcherEngine.generate_smart_fallback_motion(
                    text=text,
                    image_path=sd_temp_img if sd_success else None,
                    output_video_path=raw_video_path,
                    status_dict=status_dict
                )
                
                if os.path.exists(sd_temp_img):
                    safe_remove_file(sd_temp_img)
                
                if status_dict is not None:
                    status_dict["warning_text"] = None

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
                'ffmpeg',
                *get_hwaccel_args(),
                '-y',
                '-stream_loop', '-1',
                '-i', raw_video_path,
                '-i', audio_segment_path,
                '-t', f"{dur:.2f}",
                '-vf', vf_filter_with_text,
                '-af', f'afade=t=in:ss=0:d=0.4,afade=t=out:st={fade_out_start:.2f}:d=0.4',
                '-r', '24', '-pix_fmt', 'yuv420p',
                '-c:v', 'libx264', '-crf', '18', '-preset', 'ultrafast',
                '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', '-shortest',
                segment_mux_path,
            ]

            try:
                subprocess.run(ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                if os.path.exists(segment_mux_path) and os.path.getsize(segment_mux_path) > 0:
                    return segment_mux_path
            except Exception:
                fallback_cmd = [
                    'ffmpeg',
                    *get_hwaccel_args(),
                    '-y',
                    '-stream_loop', '-1',
                    '-i', raw_video_path,
                    '-i', audio_segment_path,
                    '-t', f"{dur:.2f}",
                    '-vf', vf_filter_no_text,
                    '-r', '24', '-pix_fmt', 'yuv420p',
                    '-c:v', 'libx264', '-preset', 'ultrafast',
                    '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', '-shortest',
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
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_idx = {
                    executor.submit(process_scene_segment, idx, scene): idx
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
                'ffmpeg',
                *get_hwaccel_args(),
                '-y', '-f', 'concat', '-safe', '0', '-i', manifest_file,
                '-c:v', 'copy', '-c:a', 'copy', temp_stitched_output
            ]
            
            subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            
            if bgm_path and os.path.exists(bgm_path):
                mix_cmd = [
                    'ffmpeg',
                    *get_hwaccel_args(),
                    '-y',
                    '-i', temp_stitched_output,
                    '-stream_loop', '-1',
                    '-i', bgm_path,
                    '-filter_complex', f'[0:a]volume=1.0[a0];[1:a]volume={bgm_volume:.2f}[a1];[a0][a1]amix=inputs=2:duration=first[aout]',
                    '-map', '0:v:0',
                    '-map', '[aout]',
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    video_output
                ]
                try:
                    subprocess.run(mix_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                except Exception:
                    shutil.copy(temp_stitched_output, video_output)
            else:
                shutil.copy(temp_stitched_output, video_output)
                
            if os.path.exists(video_output) and os.path.getsize(video_output) > 1000:
                return True
            return False
        except Exception:
            return False
        finally:
            try:
                shutil.rmtree(workspace_dir, ignore_errors=True)
            except Exception:
                pass


def get_premium_local_backup(output_filename):
    local_dir = "local_assets"
    if os.path.exists(local_dir) and os.path.isdir(local_dir):
        files = [os.path.join(local_dir, f) for f in os.listdir(local_dir) if f.endswith(".mp4")]
        if files:
            chosen = random.choice(files)
            try:
                shutil.copy(chosen, output_filename)
                return True
            except Exception:
                pass
    return False

def create_emergency_solid_clip(output_filename, duration, res_width, res_height):
    safe_remove_file(output_filename)
    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=#050508:s={res_width}x{res_height}:r=24',
        '-t', str(duration), '-pix_fmt', 'yuv420p', '-c:v', 'libx264', output_filename
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def safe_remove_file(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

def convert_mp4_to_webm(mp4_path, webm_path):
    safe_remove_file(webm_path)
    cmd = [
        'ffmpeg',
        *get_hwaccel_args(),
        '-y', '-i', mp4_path,
        '-c:v', 'libvpx-vp9', '-crf', '32', '-b:v', '0', 
        '-c:a', 'libopus', webm_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        try:
            cmd = [
                'ffmpeg',
                *get_hwaccel_args(),
                '-y', '-i', mp4_path,
                '-c:v', 'libvpx', '-crf', '10', '-b:v', '1M', 
                '-c:a', 'libvorbis', webm_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except Exception:
            return False


# --- 12. INTERACTIVE SELECTION CARD HELPER ---
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

# --- 13. DIALOG PREVIEW MODALS ---
@st.dialog("🎬 Cinematic Production Monitor", width="large")
def open_preview_modal(video_path):
    st.markdown(f"""
        <div style="background: rgba(18, 19, 26, 0.95); padding: 15px; border-radius: 12px; border: 1px solid rgba(255, 192, 203, 0.15);">
            <div style="font-family: 'Orbitron', sans-serif; font-size: 14px; color: #FFC0CB; margin-bottom: 12px; letter-spacing: 1px;">🟢 THEATRICAL PLAYBACK MONITOR</div>
        </div>
    """, unsafe_allow_html=True)
    st.video(video_path, format="video/mp4", autoplay=True, loop=True, muted=False)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Close Monitor", key="close_theatrical_monitor_btn", use_container_width=True):
        st.rerun()

# Dynamic Social Login Dialog Box
@st.dialog("🔑 Social Account Authentication", width="small")
def social_login_dialog(platform):
    st.markdown(f"""
        <div style="background: rgba(18, 19, 26, 0.95); padding: 5px; border-radius: 12px; text-align: center;">
            <div style="font-family: 'Orbitron', sans-serif; font-size: 14px; color: #FFC0CB; margin-bottom: 10px; letter-spacing: 1px; text-transform: uppercase;">Direct Login with {platform}</div>
            <p style="font-size:12px; color:#94a3b8; margin-bottom:15px;">Please verify your active social account email to secure instant access.</p>
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
                st.session_state["current_page"] = "studio"
                st.toast(f"Logged in successfully via {platform} account!")
                st.rerun()
            else:
                st.error("Authentication nodes failed. Try again.")
        else:
            st.error("Please provide a valid email format.")

# --- 14. CANVAS & SOCIAL SUITE ---
@st.fragment
def render_interactive_canvas_suite(selected_model, est_time, res_choice):
    if os.path.exists("final_shorts.mp4") and os.path.getsize("final_shorts.mp4") > 0:
        st.video("final_shorts.mp4", format="video/mp4", autoplay=True, loop=True, muted=False)
        
        st.markdown(f"""
            <div style="background: rgba(255, 192, 203, 0.05); border: 1px solid rgba(255, 192, 203, 0.18); border-radius: 8px; padding: 10px; margin-top: 10px; font-family: 'Orbitron', sans-serif; font-size: 11px; text-align: center; color: #a0a0a0;">
                🟢 Active Canvas State | Resolution: <span style="color: #FFC0CB; font-weight: bold;">{res_choice}</span> | 
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
                        st.download_button(
                            label=f"📥 Click to Save as {file_ext.upper()}",
                            data=video_bytes_data,
                            file_name=f"zovix_project_render.{file_ext}",
                            mime=f"video/{file_ext}" if file_ext != "gif" else "image/gif",
                            use_container_width=True,
                            key="st_final_download_save_action_button"
                        )
                    else:
                        st.error("No processed media found on active canvas viewport to compile.")
        
        with col_share:
            local_share_url = os.path.abspath("final_shorts.mp4")
            if st.button("🔗 Copy Local Path", key="social_copy_link_btn", use_container_width=True):
                st.toast("Copied absolute local render address.")
                st.info(f"Local Path Copied: {local_share_url}")
        
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
                st.link_button("🐦 Share on X (Twitter)", tw_intent_url, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<h4 style='font-family: Orbitron; font-size: 12px; color: #FFC0CB; margin-bottom: 10px;'>⚙         MULTI-FORMAT EXPORT ENGINE</h4>", unsafe_allow_html=True)
            if st.button("🔄 Transcode to WebM Formats", key="transcode_webm_trigger", use_container_width=True):
                with st.spinner("Processing WebM Transcode filters..."):
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
                        <td style="padding: 8px 0; color: #b8860b;">{st.session_state["aspect_ratio"]}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255,192,203,0.05);">
                        <td style="padding: 8px 0; color: #ffffff;">Engine Voice Channel</td>
                        <td style="padding: 8px 0; color: #b8860b;">{st.session_state["voice_profile"]}</td>
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
                <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px;">Your generated cinematic output will load directly into this box once rendering starts.</p>
            </div>
        """, unsafe_allow_html=True)

# --- 15. EXCLUSIVE DETACHED PROPARATOR TRIGGER ---
@st.fragment
def render_isolated_prompt_canvas_trigger(selected_model):
    with st.container(border=True):
        st.markdown("<div class='compact-label'>💡 Prompt Interface</div>", unsafe_allow_html=True)
        
        input_mode = st.radio(
            "Prompt Select Option Mode:", 
            ["💡 Autonomous AI Topic", "✍️ Manual Custom Script"], 
            horizontal=True, 
            key="studio_mode_radio"
        )
        
        initial_topic_val = st.session_state.get("studio_prompt_value", "")
        
        if input_mode == "💡 Autonomous AI Topic":
            user_input = st.text_area(
                "Prompt Input",
                value=initial_topic_val,
                placeholder="Explain video concept: e.g. Bermuda triangle ka ansuljha rahasya jo kisi ko nahi pata tha.",
                height=110,
                label_visibility="collapsed",
                key="studio_prompt_topic_input"
            )
        else:
            user_input = st.text_area(
                "Direct Custom Script",
                value=initial_topic_val,
                placeholder="Write a custom script separated by paragraph breaks. E.g:\n[Scene 1: ocean] Paragraph text...\n\n[Scene 2: storm] Next text...",
                height=110,
                label_visibility="collapsed",
                key="studio_prompt_script_input"
            )
        
        p_cols = st.columns([15, 2], gap="small")
        with p_cols[0]:
            st.write("")
        with p_cols[1]:
            is_running = st.session_state.get("render_status") == "running"
            if is_running:
                st.markdown("""
                    <style>
                    div.generate-btn-wrapper button {
                        background: #EC4899 !important;
                        background-color: #EC4899 !important;
                        color: #FFFFFF !important;
                        box-shadow: 0 0 15px rgba(236, 72, 153, 0.45) !important;
                        border: 1px solid #EC4899 !important;
                    }
                    </style>
                """, unsafe_allow_html=True)
                
            st.markdown("<div class='generate-btn-wrapper'>", unsafe_allow_html=True)
            if st.button("Generate", key="studio_generate_action_btn", use_container_width=True):
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


# --- 16. SYSTEM SIDEBAR NAVIGATION, PORTFOLIO & GAMIFIED REWARDS ---
with st.sidebar:
    st.markdown("<h3 style='font-family: Orbitron; color: #FFC0CB; margin-top: 15px;'>👑 ZOVIX PORTAL</h3>", unsafe_allow_html=True)
    
    st.markdown("<div class='compact-label'>👤 User Profile</div>", unsafe_allow_html=True)
    user_display = st.session_state["logged_user"].upper() if st.session_state["is_logged_in"] else "GUEST"
    
    user_xp = get_user_xp_db(st.session_state["logged_user"]) if st.session_state["is_logged_in"] else 0
    creator_level = 1 + (user_xp // 100)
    
    personal_renders = load_from_json_history(st.session_state["logged_user"]) if st.session_state["is_logged_in"] else []
    total_renders_count = len(personal_renders)
    
    st.session_state["xp_points"] = user_xp
    st.session_state["creator_level"] = creator_level
    
    streak_count, last_claim_date = (0, "")
    if st.session_state["is_logged_in"]:
        streak_count, last_claim_date = get_user_streak_info(st.session_state["logged_user"])
        
    std_c, v_c, expires_at_str = (0, 0, "")
    if st.session_state["is_logged_in"]:
        check_and_expire_vouchers(st.session_state["logged_user"])
        conn = sqlite3.connect("zovix_v4.db", check_same_thread=False)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT credits, voucher_credits, voucher_expires_at FROM users WHERE username = ?", (st.session_state['logged_user'],))
            row = cursor.fetchone()
        except sqlite3.OperationalError as e:
            if "no such table: users" in str(e):
                # Agar table nahi mili, toh turant pehle yahi table create kar do!
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        password TEXT,
                        credits REAL DEFAULT 0,
                        xp_points REAL DEFAULT 0,
                        streak_count INTEGER DEFAULT 0,
                        last_claim_date TEXT,
                        voucher_credits INTEGER DEFAULT 0,
                        voucher_expires_at TEXT DEFAULT ''
                    )
                """)
                conn.commit()
                # Table banane ke baad dobara query chalao taaki khali row check ho sake
                cursor.execute("SELECT credits, voucher_credits, voucher_expires_at FROM users WHERE username = ?", (st.session_state['logged_user'],))
                row = cursor.fetchone()
            else:
                raise 
        conn.close()
        if row:
            std_c, v_c, expires_at_str = row[0], row[1], row[2]
            
    # Premium visual dashboard highlighting both Standard & Voucher Credits safely
    st.markdown(f"""
        <div style='background: rgba(255, 192, 203, 0.04); border: 1px solid rgba(255, 192, 203, 0.1); padding: 10px; border-radius: 8px; margin-bottom: 12px;'>
            <div style='font-size: 13px; font-weight: bold; color: #FFC0CB; font-family: Orbitron;'>Node ID: {user_display}</div>
            <div style='font-size: 11px; color: #A0AEC0; margin-top: 4px;'>🏆 Creator Level: {creator_level}</div>
            <div style='font-size: 11px; color: #A0AEC0;'>⚡ XP Points: {user_xp} XP</div>
            <div style='font-size: 11px; color: #A0AEC0;'>🔥 Login Streak: <span style='color: #fbbf24; font-weight: bold;'>{streak_count} Days</span></div>
            <div style='font-size: 11px; color: #A0AEC0; margin-top: 5px; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 5px;'>Standard Credits: <span style='color:#ffffff; font-weight:bold;'>{std_c}</span></div>
            {"<div style='font-size: 11px; color: #fbbf24;'>⏳ Voucher Credits: <span style='font-weight:bold;'>" + str(v_c) + "</span> (Expires soon!)</div>" if v_c > 0 else ""}
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state["is_logged_in"]:
        today_iso = datetime.date.today().isoformat()
        if last_claim_date == today_iso:
            st.markdown("""
                <div style='background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 8px; border-radius: 6px; text-align: center; margin-bottom: 15px;'>
                    <span style='color: #10b981; font-size: 11px; font-weight: bold;'>🎉 Today's Daily Streak Claimed!</span>
                </div>
            """, unsafe_allow_html=True)
        else:
            if st.button("🎁 Claim Daily login Reward", key="claim_daily_bonus_streak_button", use_container_width=True):
                success, new_strk, msg = claim_daily_reward_db(st.session_state["logged_user"])
                if success:
                    st.success(msg)
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.info(msg)
    
    credits_val = get_user_credits_db(st.session_state["logged_user"]) if st.session_state["is_logged_in"] else 0
    st.metric(label="Total Credits Available", value=f"{credits_val} / ∞", delta="Node Secure", delta_color="normal")
    
    st.markdown("---")
    
    st.markdown("<div class='compact-label'>Portal View Selection</div>", unsafe_allow_html=True)
    sidebar_tab = st.radio(
        "View Tab",
        ["⚙️ Setup Config", "💎 Buy Credits", "📂 My Portfolio"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    now = datetime.datetime.now().strftime("%H:%M:%S")
    st.sidebar.caption(f"🟢 Project Autosaved: {now}")


# --- 17. SYSTEM PAGE ROUTING ---
if st.session_state["current_page"] == "landing":
    
    main_banner_col, auth_panel_col = st.columns([1.7, 1.3], gap="large")
    
    with main_banner_col:
        logo_path = find_valid_logo_path()
        
        logo_col, title_col = st.columns([0.22, 0.78])
        if logo_path:
            with logo_col:
                st.image(logo_path, width=180)
            with title_col:
                st.markdown("<h1 style='font-size: 85px !important; margin-top: 25px; font-family: \"Orbitron\", sans-serif; font-weight: 900; margin-left: -20px;' class='brand-text-gold'>ZOVIX</h1>", unsafe_allow_html=True)
        else:
            svg_data = """<svg viewBox="0 0 100 100" width="180" style="filter: drop-shadow(0 0 12px rgba(255, 215, 0, 0.4));">
                <defs>
                    <linearGradient id="gold-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#FFF3B0" />
                        <stop offset="30%" stop-color="#CA9E32" />
                        <stop offset="70%" stop-color="#F5C518" />
                        <stop offset="100%" stop-color="#6E5005" />
                    </linearGradient>
                </defs>
                <polygon points="50,15 30,35 70,35" fill="url(#gold-grad)" opacity="0.9" stroke="#000000" stroke-width="0.3"/>
                <polygon points="30,35 10,35 20,50 30,35" fill="url(#gold-grad)" opacity="0.8" stroke="#000000" stroke-width="0.3"/>
                <polygon points="50,15 30,35 20,50 50,50" fill="url(#gold-grad)" opacity="0.85" stroke="#000000" stroke-width="0.3"/>
                <polygon points="50,15 70,35 80,50 50,50" fill="url(#gold-grad)" opacity="0.95" stroke="#000000" stroke-width="0.3"/>
                <polygon points="70,35 90,35 80,50 70,35" fill="url(#gold-grad)" opacity="0.8" stroke="#000000" stroke-width="0.3"/>
                <polygon points="10,35 50,90 20,50" fill="url(#gold-grad)" opacity="0.75" stroke="#000000" stroke-width="0.3"/>
                <polygon points="20,50 50,90 50,50" fill="url(#gold-grad)" opacity="0.85" stroke="#000000" stroke-width="0.3"/>
                <polygon points="50,50 50,90 80,50" fill="url(#gold-grad)" opacity="0.9" stroke="#000000" stroke-width="0.3"/>
                <polygon points="80,50 50,90 90,35" fill="url(#gold-grad)" opacity="0.8" stroke="#000000" stroke-width="0.3"/>
            </svg>"""
            with logo_col:
                st.markdown(svg_data, unsafe_allow_html=True)
            with title_col:
                st.markdown("<h1 style='font-size: 85px !important; margin-top: 25px; font-family: \"Orbitron\", sans-serif; font-weight: 900; margin-left: -20px;' class='brand-text-gold'>ZOVIX</h1>", unsafe_allow_html=True)
        
        st.title("Transform Ideas into Cinematic Scene Breakdowns")
        st.write("Construct contextual AI breakdowns matching technical visual criteria with custom formatting rules.")
        
        st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
        
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.markdown(f"""
                <div style="margin-bottom: 25px;">
                    <div style="font-size: 14px; text-transform: uppercase; letter-spacing: 1.5px; color: #8A90A6; font-family: 'Orbitron', sans-serif; font-weight: 600;">System Downloads</div>
                    <div style="font-family: 'Orbitron', sans-serif; font-size: 48px; font-weight: 900; color: #FFFFFF; margin-top: 8px; text-shadow: 0 0 15px rgba(255,255,255,0.1);">{st.session_state["total_downloads"]:,}</div>
                </div>
            """, unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"""
                <div style="margin-bottom: 25px;">
                    <div style="font-size: 14px; text-transform: uppercase; letter-spacing: 1.5px; color: #8A90A6; font-family: 'Orbitron', sans-serif; font-weight: 600;">Videos Rendered</div>
                    <div style="font-family: 'Orbitron', sans-serif; font-size: 48px; font-weight: 900; color: #FFFFFF; margin-top: 8px; text-shadow: 0 0 15px rgba(255,255,255,0.1);">{st.session_state["total_generated"]:,}</div>
                </div>
            """, unsafe_allow_html=True)
        with m_col3:
            st.markdown("""
                <div style="margin-bottom: 25px;">
                    <div style="font-size: 14px; text-transform: uppercase; letter-spacing: 1.5px; color: #8A90A6; font-family: 'Orbitron', sans-serif; font-weight: 600;">Active Nodes Online</div>
                    <div style="font-family: 'Orbitron', sans-serif; font-size: 32px; font-weight: 900; color: #10B981; margin-top: 15px; display: flex; align-items: center; gap: 10px; text-shadow: 0 0 15px rgba(16,185,129,0.2);">
                        <span class="pulse-indicator" style="width: 14px; height: 14px; margin-right: 0;"></span> ONLINE
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
    with auth_panel_col:
        st.markdown("<div style='margin-top: 20px;'>", unsafe_allow_html=True)
        
        st.markdown("""
            <div class="screenshot-card-panel" style="padding: 12px 20px; margin-bottom: 20px;">
                <div style="font-size:11px; font-family:'Orbitron'; letter-spacing:1px; color:#A0AEC0; text-transform:uppercase; margin-bottom:4px;">System Metrics</div>
                <div style="font-size: 12px; color: #A0AEC0; font-family: monospace;">
                    Latency: <span style="color: #FFC0CB;">24ms</span> | Engine Load: <span style="color: #FFC0CB;">12%</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        auth_mode = st.radio("Access Node Mode", ["🔒 Studio Access Sign-in", "📝 Register identity"], horizontal=True, key="landing_auth_toggle")
        
        if auth_mode == "🔒 Studio Access Sign-in":
            st.markdown("""
                <div style="background-color: #12131A; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 20px; margin-bottom: 10px;">
                    <div style="font-family: 'Orbitron', sans-serif; font-size: 11px; color: #FFFFFF; letter-spacing: 1px; text-transform: uppercase;">STUDIO ACCESS SIGN-IN</div>
                </div>
            """, unsafe_allow_html=True)
            
            l_user = st.text_input("Username", key="land_login_user", placeholder="Username", label_visibility="collapsed").strip()
            l_pass = st.text_input("Password", type="password", key="land_login_pass", placeholder="Password", label_visibility="collapsed").strip()
            
            st.write("")
            if st.button("Login", key="landing_login_submit", use_container_width=True):
                if authenticate_user_db(l_user, l_pass):
                    st.session_state["is_logged_in"] = True
                    st.session_state["logged_user"] = l_user
                    st.session_state["xp_points"] = get_user_xp_db(l_user)
                    st.session_state["creator_level"] = 1 + (st.session_state["xp_points"] // 100)
                    st.session_state["history_renders"] = load_renders_history_db(l_user)
                    st.session_state["current_page"] = "studio"
                    st.rerun()
                else:
                    st.error("Invalid Username or Password configuration!")
            
            st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 15px 0;'>", unsafe_allow_html=True)
            st.markdown("<div style='font-family: Orbitron; font-size: 10px; color: #A0AEC0; text-align: center; margin-bottom: 12px; letter-spacing: 1px;'>OR DIRECT SECURE AUTHENTICATION</div>", unsafe_allow_html=True)
            
            col_g, col_f = st.columns(2)
            with col_g:
                st.markdown("<div class='google-wrap'>", unsafe_allow_html=True)
                if st.button("🔴 Google Email", key="google_login_action_btn", use_container_width=True):
                    social_login_dialog("Google")
                st.markdown("</div>", unsafe_allow_html=True)
            with col_f:
                st.markdown("<div class='facebook-wrap'>", unsafe_allow_html=True)
                if st.button("🔵 Facebook ID", key="fb_login_action_btn", use_container_width=True):
                    social_login_dialog("Facebook")
                st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.markdown("""
                <div style="background-color: #12131A; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 20px; margin-bottom: 10px;">
                    <div style="font-family: 'Orbitron', sans-serif; font-size: 11px; color: #FFFFFF; letter-spacing: 1px; text-transform: uppercase;">REGISTER NEW ID</div>
                </div>
            """, unsafe_allow_html=True)
            
            s_user = st.text_input("New Username", key="land_signup_user", placeholder="Username", label_visibility="collapsed").strip()
            s_pass = st.text_input("Access Password", type="password", key="land_signup_pass", placeholder="Password", label_visibility="collapsed").strip()
            
            st.write("")
            if st.button("Register & Activate Workspace", key="landing_signup_submit", use_container_width=True):
                if s_user and s_pass:
                    if register_user_db(s_user, s_pass):
                        st.session_state["is_logged_in"] = True
                        st.session_state["logged_user"] = s_user
                        st.session_state["xp_points"] = 0
                        st.session_state["creator_level"] = 1
                        st.session_state["history_renders"] = []
                        st.session_state["current_page"] = "studio"
                        st.rerun()
                    else:
                        st.error("Username already registered in database!")
                else:
                    st.error("Invalid parameters entered!")

        st.markdown("""
            <div class="screenshot-card-panel" style="margin-top: 20px;">
                <div class="system-metrics-header" style="border: none; margin-bottom: 5px;">User Guide / Top Renders</div>
                <div class="guide-icon-row">
                    <div class="guide-icon-box">🗂️</div>
                    <div class="guide-icon-box">📹</div>
                    <div class="guide-icon-box">🎞️</div>
                    <div class="guide-icon-box">📄</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
                    
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; font-family:Orbitron; font-size:22px; color:#ffffff; margin-bottom: 30px; letter-spacing: 1px;'>💎 EXPLORE PREMIUM AI RENDERS</h3>", unsafe_allow_html=True)
    
    showcase_cols = st.columns(4)
    showcase_items = [
        {"title": "Lost City of El Dorado", "type": "video", "desc": "Pre-rendered masterpiece showing mysterious gold temples.", "icon": "🎬"},
        {"title": "Cyberpunk Neo Tokyo", "type": "photo", "desc": "Stunning neon-lit street captured under artificial rain.", "icon": "🖼️"},
        {"title": "Deep Space Nebula Core", "type": "video", "desc": "Immersive trip through swirling gas and distant star clusters.", "icon": "🎬"},
        {"title": "Bermuda Abyss Monolith", "type": "photo", "desc": "Generative digital art illustrating ancient underwater monuments.", "icon": "🖼️"}
    ]
    for idx, item in enumerate(showcase_items):
        with showcase_cols[idx]:
            st.markdown(f"""
                <div style="background: rgba(18, 19, 26, 0.95); border: 1px solid rgba(255, 192, 203, 0.15); border-radius: 10px; padding: 15px; text-align: center; height: 210px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <span style="font-size: 32px; display: block; margin-bottom: 10px;">{item["icon"]}</span>
                        <h4 style="font-family: 'Orbitron'; font-size: 13px; color: #FFC0CB; margin: 0 0 5px 0;">{item["title"]}</h4>
                        <p style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin: 0; font-weight: 300;">{item["desc"]}</p>
                    </div>
                    <div style="font-family: 'Orbitron'; font-size: 10px; color: #fbbf24; font-weight: bold; text-transform: uppercase;">{item["type"].upper()} PREVIEW</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; font-family:Orbitron; font-size:24px; color:#ffffff; margin-bottom: 30px; letter-spacing: 1px;'>🚀 INTEGRATED WORKFLOW PIPELINE</h3>", unsafe_allow_html=True)
    
    col_step1, col_step2, col_step3 = st.columns(3)
    with col_step1:
        st.markdown("""
            <div class="leonardo-feature-card">
                <div style="font-size: 24px; font-weight: bold; color: #ffd700; margin-bottom: 10px; font-family: 'Orbitron';">01</div>
                <h4 style="color: #ffffff; font-family: Orbitron; font-size: 15px; margin-bottom: 8px;">1. Structured Scripting</h4>
                <p style="color: #94a3b8; font-size: 12.5px; line-height: 1.5; font-weight: 300;">Constructs structured scripts with scene-by-scene keyword parameters using the LLM engine.</p>
            </div>
        """, unsafe_allow_html=True)
        
    with col_step2:
        st.markdown("""
            <div class="leonardo-feature-card">
                <div style="font-size: 24px; font-weight: bold; color: #ffd700; margin-bottom: 10px; font-family: 'Orbitron';">02</div>
                <h4 style="color: #ffffff; font-family: Orbitron; font-size: 15px; margin-bottom: 8px;">2. Voice Segment Synthetics</h4>
                <p style="color: #94a3b8; font-size: 12.5px; line-height: 1.5; font-weight: 300;">Generates specific voice streams per scene block and calculates precise audio timelines.</p>
            </div>
        """, unsafe_allow_html=True)
        
    with col_step3:
        st.markdown("""
            <div class="leonardo-feature-card">
                <div style="font-size: 24px; font-weight: bold; color: #ffd700; margin-bottom: 10px; font-family: 'Orbitron';">03</div>
                <h4 style="color: #ffffff; font-family: Orbitron; font-size: 15px; margin-bottom: 8px;">3. Multi-Scene Stitching</h4>
                <p style="color: #94a3b8; font-size: 12.5px; line-height: 1.5; font-weight: 300;">Trims visual assets to matching segment runtimes and compiles them together into final outputs.</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 40px 0 20px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; font-family:Orbitron; font-size:24px; color:#ffffff; margin-bottom: 30px; letter-spacing: 1px;'>📊 ENGINE TECHNICAL SPECIFICATIONS</h3>", unsafe_allow_html=True)
    
    spec_col1, spec_col2, spec_col3, spec_col4 = st.columns(4)
    with spec_col1:
        st.markdown("""
            <div class="leonardo-feature-card" style="text-align: center;">
                <div style="font-size: 11px; color: #8A90A6; letter-spacing: 1px;">STITCHING RATIO</div>
                <div style="font-family: 'Orbitron', sans-serif; font-size: 14px; color: #FFFFFF; font-weight: 600; margin-top: 5px;">9:16 / 16:9 / 1:1</div>
            </div>
        """, unsafe_allow_html=True)
    with spec_col2:
        st.markdown("""
            <div class="leonardo-feature-card" style="text-align: center;">
                <div style="font-size: 11px; color: #8A90A6; letter-spacing: 1px;">TRANSCODE CODEC</div>
                <div style="font-family: 'Orbitron', sans-serif; font-size: 14px; color: #FFFFFF; font-weight: 600; margin-top: 5px;">H.264 & VP9 WEB</div>
            </div>
        """, unsafe_allow_html=True)
    with spec_col3:
        st.markdown("""
            <div class="leonardo-feature-card" style="text-align: center;">
                <div style="font-size: 11px; color: #8A90A6; letter-spacing: 1px;">SAMPLING RATE</div>
                <div style="font-family: 'Orbitron', sans-serif; font-size: 14px; color: #FFFFFF; font-weight: 600; margin-top: 5px;">44.1 kHz High-Fi</div>
            </div>
        """, unsafe_allow_html=True)
    with spec_col4:
        st.markdown("""
            <div class="leonardo-feature-card" style="text-align: center;">
                <div style="font-size: 11px; color: #8A90A6; letter-spacing: 1px;">COMPOSITE FILTER</div>
                <div style="font-family: 'Orbitron', sans-serif; font-size: 14px; color: #FFFFFF; font-weight: 600; margin-top: 5px;">Lanczos Scaling</div>
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
        
    col_hdr_l, col_hdr_r = st.columns([13, 3], gap="small")
    with col_hdr_l:
        logo_path = find_valid_logo_path()
        hdr_logo_col, hdr_title_col = st.columns([0.12, 0.88])
        
        if logo_path:
            with hdr_logo_col:
                st.image(logo_path, width=80)
            with hdr_title_col:
                st.markdown("<h1 style='font-size: 45px !important; margin-top: 5px; font-family: \"Orbitron\", sans-serif; font-weight: 900; margin-left: -35px;' class='brand-text-gold'>ZOVIX</h1>", unsafe_allow_html=True)
        else:
            svg_data_small = """<svg viewBox="0 0 100 100" width="80" style="filter: drop-shadow(0 0 10px rgba(255, 192, 203, 0.35));">
                <defs>
                    <linearGradient id="gold-grad-sm" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#FFF3B0" />
                        <stop offset="30%" stop-color="#CA9E32" />
                        <stop offset="70%" stop-color="#F5C518" />
                        <stop offset="100%" stop-color="#6E5005" />
                    </linearGradient>
                </defs>
                <polygon points="50,15 30,35 70,35" fill="url(#gold-grad-sm)" opacity="0.9" stroke="#000000" stroke-width="0.3"/>
                <polygon points="30,35 10,35 20,50 30,35" fill="url(#gold-grad-sm)" opacity="0.8" stroke="#000000" stroke-width="0.3"/>
                <polygon points="50,15 30,35 20,50 50,50" fill="url(#gold-grad-sm)" opacity="0.85" stroke="#000000" stroke-width="0.3"/>
                <polygon points="50,15 70,35 80,50 50,50" fill="url(#gold-grad-sm)" opacity="0.95" stroke="#000000" stroke-width="0.3"/>
                <polygon points="70,35 90,35 80,50 70,35" fill="url(#gold-grad-sm)" opacity="0.8" stroke="#000000" stroke-width="0.3"/>
                <polygon points="10,35 50,90 20,50" fill="url(#gold-grad-sm)" opacity="0.75" stroke="#000000" stroke-width="0.3"/>
                <polygon points="20,50 50,90 50,50" fill="url(#gold-grad-sm)" opacity="0.85" stroke="#000000" stroke-width="0.3"/>
                <polygon points="50,50 50,90 80,50" fill="url(#gold-grad-sm)" opacity="0.9" stroke="#000000" stroke-width="0.3"/>
                <polygon points="80,50 50,90 90,35" fill="url(#gold-grad-sm)" opacity="0.8" stroke="#000000" stroke-width="0.3"/>
            </svg>"""
            with hdr_logo_col:
                st.markdown(svg_data_small, unsafe_allow_html=True)
            with hdr_title_col:
                st.markdown("<h1 style='font-size: 45px !important; margin-top: 5px; font-family: \"Orbitron\", sans-serif; font-weight: 900; margin-left: -35px;' class='brand-text-gold'>ZOVIX</h1>", unsafe_allow_html=True)
            
    with col_hdr_r:
        st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='exit-btn-wrapper'>", unsafe_allow_html=True)
        if st.button("Exit Studio", key="studio_hdr_logout_btn", use_container_width=True):
            st.session_state["is_logged_in"] = False
            st.session_state["logged_user"] = ""
            st.session_state["current_page"] = "landing"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 10px 0 20px 0;'>", unsafe_allow_html=True)

    # --- MAIN PORTAL VIEW ROUTING BASED ON SIDEBAR TABS ---
    if sidebar_tab == "💎 Buy Credits":
        st.markdown("""
            <div style="background: rgba(18, 19, 26, 0.95); border-radius: 12px; border: 1px solid rgba(255,192,203,0.15); padding: 25px; margin-bottom: 25px; text-align: center;">
                <h2 style="font-family: 'Orbitron', sans-serif; font-size: 24px; color: #ffffff; letter-spacing: 1px; margin-bottom: 6px;">💎 ZOVIX COIN SYSTEM & MONETIZATION HUB</h2>
                <p style="color: #94a3b8; font-size: 13.5px; margin: 0; max-width: 600px; margin-left: auto; margin-right: auto;">
                    Buy standard long-term packs or single-use 24-Hour Video Vouchers to supercharge your generative experience.
                </p>
            </div>
        """, unsafe_allow_html=True)

        currency_toggle = st.radio(
            "Select Currency (INR / USD):",
            ["🇮🇳 INR (₹) - Razorpay / UPI", "🇺🇸 USD ($) - International Card Portal"],
            horizontal=True,
            key="currency_payment_selection_toggle"
        )
        is_usd = "USD" in currency_toggle

        col_left_packs, col_right_vouch = st.columns([1.8, 1.2], gap="large")

        with col_left_packs:
            st.markdown("<h3 style='font-family: Orbitron; font-size: 16px; color: #FFC0CB; margin-bottom: 15px;'>📦 STANDARD CREDIT PACKS (NO EXPIRY)</h3>", unsafe_allow_html=True)
            
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                price_str = "$1.99" if is_usd else "₹99"
                st.markdown(f"""
                    <div style="background: rgba(255,192,203,0.02); border: 1px solid rgba(255,192,203,0.1); border-radius: 10px; padding: 20px; text-align: center; height: 100%; min-height: 200px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <span style="font-size: 28px;">🥉</span>
                            <h4 style="font-family: Orbitron; font-size: 14px; margin-top: 10px; color: #ffffff;">Starter Pack</h4>
                            <p style="font-size: 20px; font-weight: bold; color: #FFC0CB; margin: 8px 0;">{price_str}</p>
                            <p style="font-size: 11px; color: #94a3b8;">Provides 100 standard high-fidelity rendering credits.</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Buy Starter Pack", key="buy_pack_starter_btn", use_container_width=True):
                    add_credits(st.session_state["logged_user"], 100, "standard")
                    st.success("Starter Pack purchased successfully!")
                    st.toast("+100 Credits added!")
                    time.sleep(1)
                    st.rerun()

            with p_col2:
                price_str = "$3.99" if is_usd else "₹299"
                st.markdown(f"""
                    <div style="background: rgba(255,192,203,0.02); border: 1px solid rgba(255,192,203,0.1); border-radius: 10px; padding: 20px; text-align: center; height: 100%; min-height: 200px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <span style="font-size: 28px;">🥈</span>
                            <h4 style="font-family: Orbitron; font-size: 14px; margin-top: 10px; color: #ffffff;">Creator Pack</h4>
                            <p style="font-size: 20px; font-weight: bold; color: #FFC0CB; margin: 8px 0;">{price_str}</p>
                            <p style="font-size: 11px; color: #94a3b8;">Provides 400 standard high-fidelity rendering credits.</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Buy Creator Pack", key="buy_pack_creator_btn", use_container_width=True):
                    add_credits(st.session_state["logged_user"], 400, "standard")
                    st.success("Creator Pack purchased successfully!")
                    st.toast("+400 Credits added!")
                    time.sleep(1)
                    st.rerun()

            with p_col3:
                price_str = "$5.99" if is_usd else "₹499"
                st.markdown(f"""
                    <div style="background: rgba(255,192,203,0.02); border: 1px solid rgba(255,192,203,0.1); border-radius: 10px; padding: 20px; text-align: center; height: 100%; min-height: 200px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <span style="font-size: 28px;">🥇</span>
                            <h4 style="font-family: Orbitron; font-size: 14px; margin-top: 10px; color: #ffffff;">Studio Pro Pack</h4>
                            <p style="font-size: 20px; font-weight: bold; color: #FFC0CB; margin: 8px 0;">{price_str}</p>
                            <p style="font-size: 11px; color: #94a3b8;">Provides 800 standard high-fidelity rendering credits.</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Buy Studio Pro Pack", key="buy_pack_pro_btn", use_container_width=True):
                    add_credits(st.session_state["logged_user"], 800, "standard")
                    st.success("Studio Pro Pack purchased successfully!")
                    st.toast("+800 Credits added!")
                    time.sleep(1)
                    st.rerun()

        with col_right_vouch:
            st.markdown("<h3 style='font-family: Orbitron; font-size: 16px; color: #FFC0CB; margin-bottom: 15px;'>⏳ QUICK-FIX VIDEO VOUCHER</h3>", unsafe_allow_html=True)
            v_price = "$0.99" if is_usd else "₹49"
            
            st.markdown(f"""
                <div style="background: rgba(251,191,36,0.02); border: 1px solid rgba(251,191,36,0.2); border-radius: 10px; padding: 25px; text-align: center; min-height: 200px; display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 15px;">
                    <div>
                        <span style="font-size: 32px;">🎟️</span>
                        <h4 style="font-family: Orbitron; font-size: 15px; margin-top: 10px; color: #ffffff;">Single-Use Voucher</h4>
                        <p style="font-size: 24px; font-weight: bold; color: #fbbf24; margin: 8px 0;">{v_price}</p>
                        <p style="font-size: 11.5px; color: #94a3b8; line-height: 1.4;">
                            Grants <span style="color:#ffffff; font-weight:bold;">20 temporary credits</span> (valid for exactly <span style="color:#fbbf24; font-weight:bold;">24 hours</span>). Expired credits are auto-removed.
                        </p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("Buy Single Video Voucher", key="buy_voucher_btn", use_container_width=True):
                add_credits(st.session_state["logged_user"], 20, "voucher")
                st.success("Temporary Voucher Credits activated successfully!")
                st.toast("+20 Temporary Voucher Credits active for 24 hours!")
                time.sleep(1)
                st.rerun()

        # Premium International Payment Simulated Validation Layer
        if is_usd:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>🇺🇸 SECURE GLOBAL CREDIT CARD CHECKOUT (INTERNATIONAL CLIENTS)</h4>", unsafe_allow_html=True)
                
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    st.text_input("Cardholder Name", placeholder="John Doe", key="checkout_card_name_input")
                    st.text_input("Card Number", placeholder="•••• •••• •••• ••••", key="checkout_card_num_input")
                with c_col2:
                    st.text_input("Expiration Date", placeholder="MM/YY", key="checkout_card_exp_input")
                    st.text_input("CVV Code", type="password", placeholder="•••", key="checkout_card_cvv_input")
                st.caption("🔒 All global transactions are securely routed through PCI-DSS compliant gateways.")

    elif sidebar_tab == "⚙️ Setup Config" or sidebar_tab == "📂 My Portfolio":
        # --- ACTIVE STUDIO WORKSPACE SELECTION ---
        st.markdown("<div class='compact-label' style='margin-bottom: 8px;'>Active Studio Workspace Mode</div>", unsafe_allow_html=True)
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m1_selected = (st.session_state["studio_active_mode"] == "Cinematic Engine Mode")
            m1_wrap = "selected-opt-wrap" if m1_selected else "unselected-opt-wrap"
            st.markdown(f"<div class='{m1_wrap}'>", unsafe_allow_html=True)
            if st.button("🎬 Cinematic Engine (Video Mode)", key="switch_to_cinematic_mode_btn", use_container_width=True):
                st.session_state["studio_active_mode"] = "Cinematic Engine Mode"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with col_m2:
            m2_selected = (st.session_state["studio_active_mode"] == "Creative Workshop Mode")
            m2_wrap = "selected-opt-wrap" if m2_selected else "unselected-opt-wrap"
            st.markdown(f"<div class='{m2_wrap}'>", unsafe_allow_html=True)
            if st.button("🎨 Creative Workshop (Image Mode)", key="switch_to_creative_mode_btn", use_container_width=True):
                st.session_state["studio_active_mode"] = "Creative Workshop Mode"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)

        # ========================== MODE 1: CINEMATIC ENGINE (VIDEO) ==========================
        if st.session_state["studio_active_mode"] == "Cinematic Engine Mode":
            
            render_isolated_prompt_canvas_trigger(st.session_state["model_choice"])
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            parameters_col, video_canvas_col = st.columns([1.1, 1.4], gap="medium")
            
            with parameters_col:
                with st.container(border=True):
                    st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>⚙️ ENGINE CONFIGURATORS</h4>", unsafe_allow_html=True)
                    
                    render_premium_selection_cards(
                        "Model Core Selection", 
                        ["🤖 gemini-2.5-flash (Fast Stream Processing)", "🤖 gemini-2.5-pro (Deep Creative Narrative)"], 
                        "model_choice"
                    )
                    selected_model = "gemini-2.5-pro" if "gemini-2.5-pro" in st.session_state["model_choice"] else "gemini-2.5-flash"
                    
                    render_premium_selection_cards(
                        "Target Syntax Language", 
                        ["🇮🇳 Hinglish (Fluent Hindi Mix)", "🇬🇧 English (Global Standard)"], 
                        "language_choice"
                    )
                    
                    render_premium_selection_cards(
                        "Aspect Scaling Rules", 
                        ["📐 9:16 Vertical (Shorts/Reels)", "📐 16:9 Landscape (YouTube)", "📐 1:1 Square (Instagram)"], 
                        "aspect_ratio"
                    )
                    
                    render_premium_selection_cards(
                        "Timeline Target Duration", 
                        ["⏱️ Quick Format Shorts (10-15s)", "⏱️ Expanded Long Format (1 Minute / 60s)"], 
                        "duration_choice"
                    )
                    
                    render_premium_selection_cards(
                        "Voice Profile", 
                        ["Rachel (Premium Female Voice)", "Drew (Premium Male Voice)"], 
                        "voice_profile"
                    )
                    
                    render_premium_selection_cards(
                        "Quality resolution", 
                        ["720p (1 Credit)", "1080p (2 Credits)", "2K (3 Credits)", "4K (5 Credits)"], 
                        "res_choice"
                    )
                    
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
                                    <p style="color: #fca5a5; font-size: 12.5px; margin-bottom: 15px; font-weight: 300;">
                                        A compilation exception occurred during rendering. Ensure active network connections and confirm system parameters.
                                    </p>
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
                            order = create_payment_order(10000)
                            
                            with canvas_slot.container():
                                st.markdown(f"<div class='canvas-container-box' style='aspect-ratio: {aspect_ratio_css}; height: 380px; min-height: 380px; flex-direction: column;'>", unsafe_allow_html=True)
                                
                                status_indicator = st.empty()
                                progress_pulse = st.empty().progress(0, text="Initiating transcription nodes...")
                                status_indicator.write("🎬 **Executing Generation Sequence...**")
                                time.sleep(0.4)
                                progress_pulse.progress(20, text="Interpreting prompt syntax...")
                                
                                music_mood = "cinematic"
                                if pipeline_prompt_mode == "💡 Autonomous AI Topic":
                                    scenes, music_mood = ScriptingEngine.generate_script(
                                        topic=pipeline_prompt_input, 
                                        duration_choice=st.session_state["duration_choice"], 
                                        selected_model=selected_model, 
                                        language_choice=st.session_state["language_choice"]
                                    )
                                else:
                                    scenes = parse_tagged_script(pipeline_prompt_input)
                                    music_mood = "cinematic"
                                
                                progress_pulse.progress(40, text="Synthesizing storyboards...")
                                status_indicator.write("🌐 **Step 2: Fetching Assets & Sourcing Visuals...**")
                                time.sleep(0.4)
                                progress_pulse.progress(60, text="Extracting contextual database items...")
                                
                                status_indicator.write("🧵 **Step 3: Stitching Scenes & Mixing Audio...**")
                                progress_pulse.progress(80, text="Merging multi-scene elements and overlaying audio arrays...")

                                render_result_container = []

                                size_choice_val = st.session_state.get("aspect_ratio")
                                voice_profile_val = st.session_state.get("voice_profile")
                                language_choice_val = st.session_state.get("language_choice")

                                user_before_credits = get_user_credits_db(st.session_state["logged_user"]) if st.session_state.get("is_logged_in") else 0
                                user_after_credits = get_user_credits_db(st.session_state["logged_user"]) if st.session_state.get("is_logged_in") else 0

                                data_snapshot = {
                                    "aspect_ratio": size_choice_val,
                                    "voice_profile": voice_profile_val,
                                    "language_choice": language_choice_val,
                                    "user_credits_before": user_before_credits,
                                    "user_credits_after": user_after_credits,
                                    "required_credits": required_credits,
                                    "logged_user": st.session_state.get("logged_user"),
                                    "res_choice": st.session_state.get("res_choice"),
                                    "duration_choice": st.session_state.get("duration_choice"),
                                    "music_mood": music_mood,
                                }

                                effective_bgm_path = bgm_temp_path
                                if not effective_bgm_path:
                                    normalized_mood = music_mood.lower().strip()
                                    effective_bgm_path = get_music_path(normalized_mood)

                                render_status_dict = {
                                    "status_text": "Processing active scene layers...",
                                    "warning_text": None
                                }

                                def targeted_thread_worker(data_snapshot, scenes_data, video_output, bgm_path, bgm_volume, status_dict):
                                    result = {"success": False, "error": None, "video_path": None}
                                    try:
                                        thread_result = StitcherEngine.build_scene_stitched_video_isolated(
                                            scenes_data=scenes_data,
                                            video_output=video_output,
                                            size_choice=data_snapshot["aspect_ratio"],
                                            voice_profile=data_snapshot["voice_profile"],
                                            language_choice=data_snapshot["language_choice"],
                                            bgm_path=bgm_path,
                                            bgm_volume=bgm_volume,
                                            music_mood=data_snapshot.get("music_mood"),
                                            status_dict=status_dict
                                        )
                                        if thread_result and os.path.exists(video_output):
                                            result["success"] = True
                                            result["video_path"] = video_output
                                        else:
                                            result["success"] = False
                                    except Exception:
                                        error_msg = traceback.format_exc()
                                        result["success"] = False
                                        result["error"] = error_msg
                                    render_result_container.append(result)

                                st.session_state["render_status"] = "running"
                                compilation_thread = threading.Thread(
                                    target=targeted_thread_worker,
                                    args=(data_snapshot, scenes, "final_shorts.mp4", effective_bgm_path, bgm_volume, render_status_dict),
                                    daemon=True,
                                )
                                compilation_thread.start()

                                poll_interval = 0.5
                                max_wait = 600
                                elapsed = 0
                                while compilation_thread.is_alive() and elapsed < max_wait:
                                    time.sleep(poll_interval)
                                    elapsed += poll_interval
                                    
                                    warning_text = render_status_dict.get("warning_text")
                                    status_text = render_status_dict.get("status_text", "Stitching together assets...")
                                    
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
                                    time.sleep(0.5)
                                    progress_pulse.progress(100, text="Compilation successful!")
                                    status_indicator.write("✨ Video successfully compiled!")

                                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                                    local_file_name = f"zovix_render_{timestamp}.mp4"
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
                                    # Agar file nahi bani toh ye log terminal (black panel) mein print hoga
                                    print("❌❌❌ LOG: final_shorts.mp4 FILE HI NAHI BANI! ❌❌❌")
                                    try:
                                        add_credits(st.session_state.get("logged_user"), required_credits, "standard")
                                    except Exception:
                                        pass

                                    # 🚨 Background thread ke andar se chhupa hua asli error nikalne ke liye:
                                    asli_error = "File 'final_shorts.mp4' generate nahi ho saki (No specific thread error recorded)."
                                    if render_result_container and isinstance(render_result_container, list) and len(render_result_container) > 0:
                                        asli_error = render_result_container[0].get("error", asli_error)

                                    # 🔥 Ab ye generic text nahi dikhayega, balki seedhe screen par RED BOX mein error print karega!
                                    status_indicator.error(f"🚨 PIPELINE CRASHED! ASLI PYTHON ERROR YAHAN HAI:\n{asli_error}")
                                    st.session_state["render_failed"] = True

                                st.session_state["render_status"] = "idle"
                                st.markdown("</div>", unsafe_allow_html=True)
                        except Exception as e:
                            import traceback
                            asli_error = traceback.format_exc()

                            # 🔥 Yeh line error ko seedhe tumhari browser screen par RED BOX mein dikha degi!
                            status_indicator.error(f"🚨 ASLI ERROR MIL GAYA:\n{asli_error}")

                            try:
                                add_credits(st.session_state.get("logged_user"), required_credits, "standard")
                            except Exception:
                                pass
                            if bgm_temp_path:
                                safe_remove_file(bgm_temp_path)
                            st.session_state["render_failed"] = True

                            # 🚨 Is line ko comment (#) kar rahe hain taaki page refresh na ho aur error screen par ruka rahe!
                            # st.rerun()

                    with canvas_slot.container():
                        scene_count = 3
                        if "1 Minute" in st.session_state["duration_choice"]:
                            scene_count = 4
                        est_time = scene_count * 5
                        
                        render_interactive_canvas_suite(
                            selected_model=selected_model, 
                            est_time=est_time, 
                            res_choice=st.session_state["res_choice"]
                        )

        # ========================== MODE 2: CREATIVE WORKSHOP (IMAGE GENERATION) ==========================
        elif st.session_state["studio_active_mode"] == "Creative Workshop Mode":
            st.markdown("""
                <div style="background: rgba(18, 19, 26, 0.85); border-radius: 12px; border: 1px solid rgba(255,192,203,0.15); padding: 20px; margin-bottom: 20px;">
                    <h3 style="font-family: 'Orbitron'; font-size: 16px; color: #FFC0CB; margin: 0 0 5px 0;">🎨 Creative Image Synthesis Hub</h3>
                    <p style="color: #94a3b8; font-size: 12px; margin: 0;"> High-Quality Thumbnail Banner Poster </p>
                </div>
            """, unsafe_allow_html=True)

            w_col1, w_col2 = st.columns([1.1, 1.4], gap="medium")

            with w_col1:
                with st.container(border=True):
                    st.markdown("<h4 style='font-family: Orbitron; font-size: 13px; color: #FFC0CB; margin-bottom: 15px;'>⚙️ WORKSHOP PARAMETERS</h4>", unsafe_allow_html=True)
                    
                    workshop_ar = st.selectbox(
                        "Select Aspect Ratio:",
                        ["16:9", "9:16", "1:1", "21:9", "4:5", "3:2"],
                        key="workshop_aspect_ratio_choice"
                    )
                    
                    st.markdown("<div class='compact-label'>Masterpiece Prompt Input</div>", unsafe_allow_html=True)
                    workshop_prompt_str = st.text_area(
                        "Image Description Prompt",
                        placeholder="E.g. A gorgeous cyberpunk temple with pink neon aurora, hyperrealistic, 8k resolution, cinematic lighting...",
                        height=120,
                        label_visibility="collapsed",
                        key="workshop_prompt_str_area"
                    )
                    
                    st.markdown("<div class='compact-label'>Negative Prompt</div>", unsafe_allow_html=True)
                    workshop_neg_prompt_str = st.text_area(
                        "Negative Prompt",
                        placeholder="E.g. blurry, low quality, distorted, extra limbs, bad anatomy, text, watermark...",
                        height=80,
                        label_visibility="collapsed",
                        key="workshop_neg_prompt_str_area"
                    )
                    
                    st.markdown("<div class='compact-label'>Stable Video Diffusion (I2V) settings</div>", unsafe_allow_html=True)
                    motion_bucket_val = st.slider(
                        "Motion Bucket ID (Animation Intensity)", 
                        min_value=1, 
                        max_value=255, 
                        value=127, 
                        help="Higher values result in more dramatic camera motion and visual activity.",
                        key="workshop_motion_bucket_slider"
                    )
                    
                    st.write("")
                    if st.button("🚀 Generate Workshop Image", key="workshop_generation_action_btn", use_container_width=True):
                        if not workshop_prompt_str.strip():
                            st.error("Please enter a valid description first.")
                        else:
                            user_credits = get_user_credits_db(st.session_state["logged_user"])
                            if not credit_check(st.session_state["logged_user"], 1):
                                st.error(f"Low Credit Error! Required: 1, Available: {user_credits}")
                            else:
                                deduct_credits_db(st.session_state["logged_user"], 1)
                                with st.spinner("Synthesizing creative frame..."):
                                    generated_img = generate_pro_image(
                                        workshop_prompt_str, 
                                        aspect_ratio=workshop_ar,
                                        negative_prompt=workshop_neg_prompt_str
                                    )
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
                                        st.error("Synthesis engine failed to generate the visual frame. Please review API parameters.")

            with w_col2:
                with st.container(border=True):
                    st.markdown("<h3 style='font-family: Orbitron; font-size: 15px; color: #FFC0CB; margin-bottom: 15px; letter-spacing: 0.5px;'>🖼️ LIVE IMAGE OUTPUT BOX</h3>", unsafe_allow_html=True)
                    
                    active_video_file = st.session_state.get("active_svd_video")
                    active_img_file = st.session_state["workshop_active_image"]
                    
                    if active_video_file and os.path.exists(active_video_file):
                        st.video(active_video_file, format="video/mp4", autoplay=True, loop=True, muted=False)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        col_dl, col_clr = st.columns(2)
                        with col_dl:
                            with open(active_video_file, "rb") as file_bytes_wrapper:
                                st.download_button(
                                    label="📥 Save Video (MP4)",
                                    data=file_bytes_wrapper,
                                    file_name="zovix_motion_masterpiece.mp4",
                                    mime="video/mp4",
                                    use_container_width=True,
                                    key="workshop_video_download_btn"
                                )
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
                                st.download_button(
                                    label="📥 Save Frame (PNG)",
                                    data=file_bytes_wrapper,
                                    file_name="zovix_workshop_masterpiece.png",
                                    mime="image/png",
                                    use_container_width=True,
                                    key="workshop_download_action_btn"
                                )
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
                                <p style="font-size: 11px; color: #a0a0a0; max-width:400px; text-align:center; margin-top: 5px; line-height: 1.4;">Your high-fidelity synthesized artwork will display here immediately upon clicking generate.</p>
                            </div>
                        """, unsafe_allow_html=True)

        # --- 18. DYNAMIC FILTERED PORTFOLIO THUMBNAIL GALLERY ---
        st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 30px 0;'>", unsafe_allow_html=True)
        
        portfolio_renders_list = st.session_state["history_renders"]
        
        if st.session_state["studio_active_mode"] == "Cinematic Engine Mode":
            valid_items = [
                item for item in portfolio_renders_list 
                if os.path.exists(item["path"]) and os.path.splitext(item["path"])[1].lower() == ".mp4"
            ]
            gallery_title = "🎬 MY PORTFOLIO GENERATIONS (VIDEO RENDERS)"
            no_items_msg = "No video renders created yet in this session."
        else:
            valid_items = [
                item for item in portfolio_renders_list 
                if os.path.exists(item["path"]) and os.path.splitext(item["path"])[1].lower() in [".png", ".jpg", ".jpeg", ".webp"]
            ]
            gallery_title = "🎨 MY PORTFOLIO GENERATIONS (IMAGE RENDERS)"
            no_items_msg = "No synthesized artwork created yet in this session."

        st.markdown(f"<h3 style='font-family: Orbitron; font-size: 18px; color: #FFFFFF; margin-bottom: 20px; letter-spacing: 1px;'>{gallery_title}</h3>", unsafe_allow_html=True)
        
        if not valid_items:
            st.info(no_items_msg)
        else:
            grid_cols = st.columns(4)
            for idx, item in enumerate(valid_items[:8]): 
                col_target = grid_cols[idx % 4]
                file_ext = os.path.splitext(item["path"])[1].lower()
                
                with col_target:
                    with st.container(border=True):
                        st.markdown(f"""
                            <div style="font-family: 'Orbitron'; font-size: 11px; color: #FFC0CB; font-weight: bold; margin-bottom: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                📁 {item["file_name"]}
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if file_ext in [".png", ".jpg", ".jpeg", ".webp"]:
                            img_b64 = get_base64_img_raw(item["path"])
                            ext_thumb = file_ext.replace('.', '')
                            if ext_thumb == 'jpg':
                                ext_thumb = 'jpeg'
                            mime_thumb = f"image/{ext_thumb}" if ext_thumb in ['png', 'jpeg', 'webp', 'gif'] else "image/png"
                            
                            if img_b64:
                                st.markdown(f"""
                                    <div style="height: 120px; width: 100%; border-radius: 6px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: center; background: #000; margin-bottom: 10px;">
                                        <img src="data:{mime_thumb};base64,{img_b64}" style="max-height: 100%; max-width: 100%; object-fit: contain;" />
                                    </div>
                                """, unsafe_allow_html=True)
                        elif file_ext == ".mp4":
                            st.markdown("""
                                <div style="height: 120px; width: 100%; border-radius: 6px; overflow: hidden; border: 1px solid rgba(255,192,203,0.2); display: flex; flex-direction: column; align-items: center; justify-content: center; background: radial-gradient(circle, #1e1b29 0%, #0a0a0f 100%); margin-bottom: 10px;">
                                    <span style="font-size: 36px; display: block;">🎬</span>
                                    <span style="font-family: 'Orbitron'; font-size: 9px; color: #FFC0CB; margin-top: 5px; text-transform: uppercase;">VIDEO SCENE RENDER</span>
                                </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown(f"""
                            <p style="font-size: 10px; color: #94a3b8; line-height: 1.3; height: 36px; overflow: hidden; text-overflow: ellipsis; margin: 0 0 10px 0; font-weight: 300;">
                                "{item["prompt"]}"
                            </p>
                        """, unsafe_allow_html=True)
                        
                        col_rem, col_pl = st.columns(2)
                        with col_rem:
                            if st.button("🔄 Remix", key=f"port_remix_btn_{idx}", use_container_width=True):
                                st.session_state["studio_prompt_value"] = item["prompt"]
                                st.toast("Prompt copied! Click Generate to apply.")
                                st.rerun()
                        with col_pl:
                            if file_ext == ".mp4":
                                if st.button("▶️ Play", key=f"port_play_btn_{idx}", use_container_width=True):
                                    open_preview_modal(item["path"])
                            else:
                                if st.button("🔎 View", key=f"port_view_image_btn_{idx}", use_container_width=True):
                                    st.session_state["workshop_active_image"] = item["path"]
                                    st.session_state["studio_active_mode"] = "Creative Workshop Mode"
                                    st.rerun()
                                    
                        if file_ext in [".png", ".jpg", ".jpeg", ".webp"]:
                            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                            if st.button("🎬 Convert to Video", key=f"port_i2v_btn_{idx}", use_container_width=True):
                                with st.spinner("Synthesizing Motion Vector Layers... Please wait..."):
                                    motion_val = st.session_state.get("workshop_motion_bucket_slider", 127)
                                    video_out = convert_image_to_video_svd_robust(item["path"], motion_bucket_id=motion_val)
                                    if video_out and os.path.exists(video_out):
                                        st.session_state["active_svd_video"] = video_out
                                        st.session_state["studio_active_mode"] = "Creative Workshop Mode"
                                        
                                        saved_vid_name = f"svd_render_{int(time.time())}.mp4"
                                        save_render_to_db(st.session_state.get("logged_user"), saved_vid_name, f"[I2V Motion of]: {item['prompt']}", video_out)
                                        save_to_json_history(st.session_state.get("logged_user"), saved_vid_name, f"[I2V Motion of]: {item['prompt']}", video_out)
                                        st.session_state["history_renders"] = load_renders_history_db(st.session_state.get("logged_user"))
                                        
                                        st.toast("Spectacular I2V video compiled successfully!")
                                        st.rerun()
                                    else:
                                        st.error("I2V video synthesis pipeline failed. Please check network/dependencies.")

    # Studio Page Collapsible Technical Expansion Area
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("ℹ️ ZOVIX Engine Technical Specs & Policies", expanded=False):
        st.markdown("<h4 style='font-family:Orbitron; font-size:15px; color:#ffffff; margin-bottom: 15px;'>🚀 INTEGRATED WORKFLOW PIPELINE</h4>", unsafe_allow_html=True)
        col_step1, col_step2, col_step3 = st.columns(3)
        with col_step1:
            st.markdown("""
                <div class="leonardo-feature-card">
                    <div style="font-size: 18px; font-weight: bold; color: #ffd700; margin-bottom: 10px; font-family: 'Orbitron';">01</div>
                    <h5 style="color: #ffffff; font-family: Orbitron; font-size: 13px; margin-bottom: 8px;">1. Structured Scripting</h5>
                    <p style="color: #94a3b8; font-size: 11.5px; line-height: 1.5;">Constructs structured scripts with scene-by-scene keyword parameters using the LLM engine.</p>
                </div>
            """, unsafe_allow_html=True)
        with col_step2:
            st.markdown("""
                <div class="leonardo-feature-card">
                    <div style="font-size: 18px; font-weight: bold; color: #ffd700; margin-bottom: 10px; font-family: 'Orbitron';">02</div>
                    <h5 style="color: #ffffff; font-family: Orbitron; font-size: 13px; margin-bottom: 8px;">2. Voice Segment Synthetics</h5>
                    <p style="color: #94a3b8; font-size: 11.5px; line-height: 1.5;">Generates specific voice streams per scene block and calculates precise audio timelines.</p>
                </div>
            """, unsafe_allow_html=True)
        with col_step3:
            st.markdown("""
                <div class="leonardo-feature-card">
                    <div style="font-size: 18px; font-weight: bold; color: #ffd700; margin-bottom: 10px; font-family: 'Orbitron';">03</div>
                    <h5 style="color: #ffffff; font-family: Orbitron; font-size: 13px; margin-bottom: 8px;">3. Multi-Scene Stitching</h5>
                    <p style="color: #94a3b8; font-size: 11.5px; line-height: 1.5;">Trims visual assets to matching segment runtimes and compiles them together with subtitles into final outputs.</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 20px 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='font-family:Orbitron; font-size:15px; color:#ffffff; margin-bottom: 15px;'>🚨 DISCLAIMER & PLATFORM POLICIES</h4>", unsafe_allow_html=True)
        disc_col1, disc_col2 = st.columns(2)
        with disc_col1:
            st.markdown("""
                <div class="leonardo-feature-card">
                    <h5 style="color: #FFC0CB; font-family: Orbitron; font-size: 12px; margin-bottom: 10px;">Generative Media Policy</h5>
                    <p style="color: #94a3b8; font-size: 11.5px; line-height: 1.6;">
                        ZOVIX operates as an automated synthesis tool. All visual assets, scripts, and synthesized voice clips are generated contextually through AI algorithms. We do not claim ownership over stock materials retrieved from third-party APIs.
                    </p>
                </div>
            """, unsafe_allow_html=True)
        with disc_col2:
            st.markdown("""
                <div class="leonardo-feature-card">
                    <h5 style="color: #FFC0CB; font-family: Orbitron; font-size: 12px; margin-bottom: 10px;">Usage & Credit Terms</h5>
                    <p style="color: #94a3b8; font-size: 11.5px; line-height: 1.6;">
                        Access to the processing nodes requires active credits. Standard 720p generations consume 1 credit, while higher configurations deduct credits proportionally. Re-rendering of previous creations from the archive is free of additional costs.
                    </p>
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