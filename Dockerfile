FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create downloads dir
RUN mkdir -p /app/downloads

# Non-root user for security
RUN useradd -m botuser && chown -R botuser /app
USER botuser

CMD ["python", "main.py"]
