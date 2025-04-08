# Use official Python 3.9 slim image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_UPGRADE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Set working directory inside the container
WORKDIR /app

# Copy requirements and .env file into the container
COPY requirements.txt .
COPY .env .env

# Install system dependencies and Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libpq-dev \
        gcc \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove \
        build-essential \
        libffi-dev \
        libpq-dev \
        gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Expose port for Gunicorn
EXPOSE 8000

# Start the app using Gunicorn
CMD ["gunicorn", "wsgi:app"]
