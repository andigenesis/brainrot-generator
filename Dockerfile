FROM python:3.11-slim

# Install ffmpeg and system deps for moviepy/Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy pre-built frontend to static directory
COPY frontend/dist/ ./static/

# Copy assets (gameplay clips + fonts)
COPY assets/ ./assets/

# Create output and temp directories
RUN mkdir -p /app/output /app/temp

# Environment
ENV GAMEPLAY_DIR=/app/assets/gameplay
ENV OUTPUT_DIR=/app/output
ENV TEMP_DIR=/app/temp
ENV STATIC_DIR=/app/static
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Start FastAPI from backend directory (preserves import structure)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
