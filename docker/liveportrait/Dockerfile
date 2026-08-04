# ==========================================================================
# ZOVIX LivePortrait + CodeFormer GPU Container
# Platform: RunPod Serverless (A10G / L4)
# Purpose: Hyper-realistic face video generation at Rs. 0.50/video
# ==========================================================================

FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

LABEL maintainer="ZOVIX AI <dev@zovix.ai>"
LABEL description="LivePortrait + CodeFormer face video generation for RunPod"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    git \
    wget \
    curl \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Set Python aliases
RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel

# Core ML frameworks
RUN pip install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cu121

# RunPod SDK
RUN pip install runpod requests boto3

# Image/Video processing
RUN pip install opencv-python==4.8.1.78 \
    opencv-contrib-python \
    Pillow==10.1.0 \
    scipy==1.11.4 \
    numpy==1.24.3 \
    matplotlib==3.7.2

# Face / Enhancement models
RUN pip install facenet-pytorch==2.5.3 \
    insightface==0.7.3 \
    onnxruntime-gpu==1.16.3

# CodeFormer dependencies
RUN pip install basicsr==1.4.2 \
    facexlib==0.3.0 \
    realesrgan==0.3.0 \
    gfpgan==1.3.8

# Clone LivePortrait
WORKDIR /app
RUN git clone https://github.com/KwaiVGI/LivePortrait.git /app/LivePortrait
WORKDIR /app/LivePortrait

# Install LivePortrait dependencies
RUN pip install -r requirements.txt

# Download pretrained models
RUN wget -P pretrained_weights/ https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/liveportrait_base.pth
RUN wget -P pretrained_weights/ https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/liveportrait_retargeting.pth
RUN wget -P pretrained_weights/ https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/motion_extractor.pth
RUN wget -P pretrained_weights/ https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/warping_module.pth
RUN wget -P pretrained_weights/ https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/spade_generator.pth
RUN wget -P pretrained_weights/ https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/stitching_retargeting_module.pth

# Download CodeFormer model
RUN mkdir -p /app/codeformer/weights && \
    wget -P /app/codeformer/weights/ https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth

# Create working directories
RUN mkdir -p /app/inputs /app/outputs /app/temp

# Copy handler
WORKDIR /app
COPY rp_handler_liveportrait.py /app/rp_handler.py
RUN chmod +x /app/rp_handler.py

# RunPod entrypoint
CMD ["python", "-u", "/app/rp_handler.py"]
