# ==========================================================================
# ZOVIX XTTS-v2 Multilingual TTS Container
# Platform: RunPod Dedicated / Serverless (A10G / L4)
# Purpose: Multi-lingual emotional voice cloning at Rs. 0.33/voice
# Languages: Hindi, Bhojpuri, Bengali, Tamil, Telugu, Gujarati + 10 more
# ==========================================================================

FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

LABEL maintainer="ZOVIX AI <dev@zovix.ai>"
LABEL description="XTTS-v2 multilingual TTS for RunPod"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HF_HOME=/app/hf_models
ENV XTTS_MODEL_DIR=/app/xtts_model

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    git \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    libasound2-dev \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Core ML
RUN pip install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cu121

# TTS framework
RUN pip install TTS==0.22.0
RUN pip install Coqui-TTS==0.22.0

# Server & API
RUN pip install runpod fastapi uvicorn requests boto3 python-multipart

# Audio processing
RUN pip install soundfile==0.12.1 \
    librosa==0.10.1 \
    pydub==0.25.1 \
    scipy==1.11.4 \
    numpy==1.24.3

# Text processing for Indian languages
RUN pip install indic-nlp-library==0.92 \
    indic-transliteration==2.2.6 \
    g2p-en==2.1.0

# Download XTTS-v2 model
RUN mkdir -p ${XTTS_MODEL_DIR}
RUN python -c "
from TTS.api import TTS;
tts = TTS('tts_models/multilingual/multi-dataset/xtts_v2');
tts.download_model();
print('XTTS-v2 model downloaded successfully')
"

# Download language support files
RUN python -c "
from TTS.tts.configs.xtts_config import XttsConfig;
from TTS.tts.models.xtts import Xtts;
print('XTTS models loaded successfully')
"

WORKDIR /app
COPY rp_handler_xtts.py /app/rp_handler.py
RUN chmod +x /app/rp_handler.py

# Pre-warm the model
RUN python -c "
from TTS.api import TTS;
import torch;
tts = TTS('tts_models/multilingual/multi-dataset/xtts_v2', gpu=True);
print('XTTS-v2 pre-warmed on GPU')
"

CMD ["python", "-u", "/app/rp_handler.py"]
