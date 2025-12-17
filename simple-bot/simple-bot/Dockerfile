# Dockerfile for Pipecat Agent with LiveKit Transport
# Option A (Recommended for Production): WebRTC + LiveKit + Pipecat LiveKitTransport

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY main.py ./

# Install Python dependencies
# Using pip since uv might not be available in container
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "pipecat-ai[livekit]" && \
    pip install --no-cache-dir python-dotenv livekit

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the bot
CMD ["python", "main.py"]

