<div align="center">

# ZOVIX.PRO | Cinematic AI Engine

### Turn a creative brief into cinematic video, visual assets, and expressive media.

[![Engine Status](https://img.shields.io/badge/Engine-Active_Development-7c3aed?style=for-the-badge)](#)
[![Tech Stack](https://img.shields.io/badge/Stack-Python_%7C_Streamlit_%7C_AI-06b6d4?style=for-the-badge)](#tech-architecture)
[![License](https://img.shields.io/badge/License-Not_Specified-64748b?style=for-the-badge)](#license)

**A multi-engine creative studio for developers, creators, and storytellers.**

[Open ZOVIX.PRO](https://zovix.pro) · [Report an issue](https://github.com/zovix151/Zovix-Portal/issues)

</div>

---

## What is ZOVIX?

ZOVIX.PRO is a Streamlit-based AI creative studio. Its cinematic workflow takes a scene brief through prompt direction, keyframe generation, image-to-video motion, and final video mastering. Other tools provide workflows for image creation, blueprints, upscaling, editing, voice, and creator operations.

The application orchestrates external model providers; available features depend on configured API credentials, provider availability, and deployment environment.

## Creative engines

| Engine | Workflow |
|---|---|
| Cinematic Engine | Parse a scene brief, generate a directed keyframe, add image-to-video motion, and master the result. |
| Creative Workshop | Generate campaign-ready visuals from a creative prompt. |
| Blueprints | Create architectural and technical design concepts. |
| AI Upscaler | Upscale images and restore visual details. |
| Draw | Generate illustrations and concept art. |
| Video Editor | Combine and enhance uploaded media with effects, transitions, and audio. |
| Face Video Studio | Generate face-led video and speech workflows. |
| Expressive Face Video | Create expressive character animation workflows. |
| AI Agent | Generate AI-assisted business and marketing content. |
| AI Sales | Build product-focused sales video content. |
| Dynamic UI | Configure a workspace around a user-selected experience profile. |
| Live Emotion Voice | Generate speech with selectable voice and emotion options. |

## Cinematic pipeline

```text
Scene brief
    ↓
GPT-4o / configured prompt director
    ↓
Replicate Flux keyframe
    ↓
Image-to-video motion (configured provider/model)
    ↓
FFmpeg video mastering
    ↓
Browser-ready cinematic output
```

Provider selection and fallback behavior are implemented in the engine modules. Add credentials for the providers and features you intend to use.

## Tech architecture

| Layer | Technologies | Responsibility |
|---|---|---|
| Application UI | Python, Streamlit | Studio dashboard, engine controls, galleries, and workflows |
| Prompt and scene direction | GPT-4o, DeepSeek, Gemini | Prompt enhancement, structured scene direction, and AI-assisted content |
| Image and video generation | Replicate, Flux, configured image-to-video models | Keyframes, generated visuals, and motion |
| Media processing | FFmpeg, OpenCV, Pillow | Video composition, image preparation, and output processing |
| Database | Supabase PostgreSQL, `psycopg2` | Persistent user, credit, and generation data |
| Hosting | Streamlit-compatible hosting; Render can run the app | Web application runtime |

### Main modules

| File | Purpose |
|---|---|
| `app.py` | Main Streamlit application and engine routing |
| `layer6_master_engine.py` | Cinematic pipeline orchestration and final video mastering |
| `spatial_director_engine.py` | Scene direction, camera, lighting, and atmosphere options |
| `flux_render_engine.py` | Replicate image/keyframe generation |
| `camera_motion_engine.py` | Image-to-video routing and camera-motion processing |
| `postgres_db.py` | PostgreSQL compatibility layer used by the app |
| `static/` | Frontend assets and static pages |
| `tests/` | Focused automated tests |

## Run locally

### Requirements

- Python 3.10+
- FFmpeg available on `PATH` for video processing
- A PostgreSQL connection (Supabase is supported)
- API credentials for the providers and features you want to use

### 1. Clone the repository

```bash
git clone https://github.com/zovix151/Zovix-Portal.git
cd Zovix-Portal
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install FFmpeg separately using your operating system's package manager, then confirm `ffmpeg` is available on `PATH`.

### 4. Configure environment variables

Create a `.env` file in the repository root, or configure the same values through your hosting provider's secret manager. Use your own credentials—do not commit `.env` or paste secrets into source control.

```dotenv
# Supabase PostgreSQL connection string (one of these is required)
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require
# SUPABASE_DB_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require

# Core AI providers
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
GEMINI_API_KEY=
REPLICATE_API_TOKEN=

# Optional voice provider
ELEVENLABS_API_KEY=
```

The app also supports Streamlit secrets for configured credentials. Never commit actual API keys, database passwords, or `secrets.toml`.

### 5. Start the app

```bash
streamlit run app.py
```

Streamlit prints a local URL (typically `http://localhost:8501`) when the app is ready.

## Deploy on Render

For a Render web service using the main Streamlit app:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `python -m uvicorn seo_entrypoint:app --host 0.0.0.0 --port $PORT`
- Use Streamlit 1.58 or newer for the ASGI entrypoint.
- The main Studio is the default. Set `ZOVIX_APP_MODE=replit` only for the separate Replit face-testing UI and its static home page. If the deployment already sets this variable to `replit`, remove it or set it to `studio`.
- The ASGI entrypoint serves `static/sitemap.xml` at `/sitemap.xml` as `application/xml` and `static/robots.txt` at `/robots.txt`. A direct `streamlit run app.py` does not provide these root routes.
- Add the required database URL and provider credentials under the service's environment settings.
- Ensure FFmpeg is installed in the service environment if you use video processing.

Keep all secrets in the host's environment/secrets configuration, not in the repository.

## Run tests

```bash
python -m pytest -q
```

## Platform and credits

- **Platform:** [zovix.pro](https://zovix.pro)
- **Repository:** [zovix151/Zovix-Portal](https://github.com/zovix151/Zovix-Portal)
- **Developer credit:** Built by **ZOVIX** · [@zovix151](https://github.com/zovix151)

## License

No root-level `LICENSE` file is currently included in this repository. Until a license is added, reuse and redistribution permissions are not specified; contact the repository owner before using the code outside this project.
