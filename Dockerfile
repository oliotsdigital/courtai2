# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables for Python and Streamlit
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Set working directory
WORKDIR /app

# Install system dependencies:
# - curl: for container healthcheck
# - fonts-noto-core & fonts-freefont-ttf: for Hindi & Marathi Devanagari PDF exports in ReportLab
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

# Expose Streamlit port 8501 for Coolify
EXPOSE 8501

# Container healthcheck using Streamlit built-in health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Start Streamlit application
ENTRYPOINT ["streamlit", "run", "app.py"]
CMD ["--server.port=8501", "--server.address=0.0.0.0"]
