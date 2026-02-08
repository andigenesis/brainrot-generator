# === Builder stage: install Python dependencies ===
FROM python:3.11-slim AS builder

WORKDIR /build

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# === Runtime stage ===
FROM python:3.11-slim

# Install ffmpeg and system deps for moviepy/Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy backend code
COPY backend/ ./

# Copy pre-built frontend to static directory
COPY frontend/dist/ ./static/

# Copy assets (gameplay clips + fonts)
COPY assets/ ./assets/

# Create output and temp directories, set up non-root user
RUN mkdir -p /app/output /app/temp && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Environment
ENV GAMEPLAY_DIR=/app/assets/gameplay
ENV OUTPUT_DIR=/app/output
ENV TEMP_DIR=/app/temp
ENV STATIC_DIR=/app/static
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV OLLAMA_URL=http://host.docker.internal:11434/api/generate

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/api/health')" || exit 1

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
