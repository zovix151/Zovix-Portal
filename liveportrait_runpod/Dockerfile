FROM pytorch/pytorch:2.1.2-cuda11.8-cudnn8-runtime

WORKDIR /app

# System dependencies aur ffmpeg install karein
RUN apt-get update && apt-get install -y ffmpeg git libgl1-mesa-glx libglib2.0-0

# Poori liveportrait_runpod directory ko copy karein
COPY . /app

# Python packages install karein
RUN pip install --no-cache-dir runpod opencv-python imageio imageio-ffmpeg scikit-image tqdm pyyaml scipy

CMD ["python", "-u", "handler.py"]