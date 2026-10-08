# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables for Python and Flask
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501

# Set working directory
WORKDIR /app

# Install system dependencies:
# - curl: for container healthcheck
# - fonts-noto-core & fonts-freefont-ttf: for clean PDF rendering in ReportLab
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    fonts-noto-core \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (leveraging Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose Flask port 8501 for Coolify
EXPOSE 8501

# Container healthcheck using Flask health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/health || exit 1

# Start Flask application using gunicorn or python
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:8501", "--workers", "2", "--timeout", "120", "app:app"]
