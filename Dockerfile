FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/momo \
    XDG_CACHE_HOME=/home/momo/.cache \
    MOMO_LLM_PROVIDER=ollama \
    MOMO_LLM_MODEL=qwen3.5:9b \
    MOMO_LLM_BASE_URL=http://ollama:11434 \
    MOMO_ASR_DEVICE=cuda

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
        git \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python3 -m pip install --upgrade pip setuptools wheel \
    && python3 -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124 \
    && python3 -m pip install -e '.[gui,asr]'

COPY config ./config
COPY meeting_profile.md topic_details.json ./
COPY docs ./docs

RUN mkdir -p videos runs /home/momo/.cache/whisper \
    && chmod -R 0777 videos runs /home/momo

EXPOSE 8501

CMD ["python3", "-m", "streamlit", "run", "src/meeting_ai/app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--server.runOnSave=false", "--browser.gatherUsageStats=false"]
