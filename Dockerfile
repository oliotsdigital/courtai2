# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables for Python, Flask, and Coolify
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=8501

# Set working directory
WORKDIR /app

# Install system dependencies:
# - curl: for container healthcheck in Coolify
# - ffmpeg: for robust audio format processing
# - fonts-noto-core, fonts-freefont-ttf, fonts-dejavu-core: for clean PDF rendering in ReportLab
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    fonts-noto-core \
    fonts-freefont-ttf \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (leveraging Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files (including training/steno_english.json)
COPY . .

# Expose default port (Coolify can map this or override via PORT environment variable)
EXPOSE 8501

# Container healthcheck using Flask /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl --fail http://127.0.0.1:${PORT:-8501}/health || exit 1

# Start Flask + SocketIO application using Gunicorn with gthread worker
# Single worker with multi-threading (50 threads) ensures thread-safe in-memory WebSocket sessions for real-time STT
CMD ["sh", "-c", "exec gunicorn --worker-class gthread --workers 1 --threads 50 --bind 0.0.0.0:${PORT:-8501} --timeout 120 --access-logfile - --error-logfile - app:app"]
