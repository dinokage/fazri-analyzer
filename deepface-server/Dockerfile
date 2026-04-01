FROM python:3.12-slim

# System libs required by OpenCV and InsightFace
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libhdf5-dev \
    libgomp1 \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer-cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create unprivileged user with a home directory before prebake so that
# InsightFace bakes the model weights into /home/appuser/.insightface
# (instead of /root/.insightface, which is unreachable at runtime).
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser \
    && chown -R appuser:appuser /app

USER appuser

# Pre-download model weights into the image so startup is instant.
# Runs as appuser → models land in /home/appuser/.insightface/models/
COPY --chown=appuser:appuser prebake_weights.py .
RUN python prebake_weights.py

# Copy application code
COPY --chown=appuser:appuser app/ ./app/

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--log-level", "info"]
