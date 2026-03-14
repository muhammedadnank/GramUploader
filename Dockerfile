FROM python:3.11-slim

# System deps — ffmpeg for Whisper audio extraction + build tools for torch
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (cache layer before copying code)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create required runtime directories
RUN mkdir -p /app/downloads /app/logs

# Non-root user for security
RUN useradd -m botuser && chown -R botuser /app
USER botuser

CMD ["python", "main.py"]
