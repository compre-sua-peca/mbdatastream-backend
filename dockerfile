# Stage 1: Builder
FROM python:3.11-slim as builder

# Set environment variables to disable buffering and .pyc generation
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_UPGRADE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Set working directory for the build stage
WORKDIR /app

# Copy requirements and .env file
COPY requirements.txt .
COPY .env .

# Install system build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libpq-dev \
        gcc

# Create a virtual environment
RUN python -m venv /venv

# Upgrade pip, setuptools, and wheel, then install Python dependencies
RUN /venv/bin/pip install --upgrade pip setuptools wheel && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt

# Remove build dependencies and clean up
RUN apt-get purge -y --auto-remove \
        build-essential \
        libffi-dev \
        libpq-dev \
        gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the application code into the builder stage
COPY . .

# Stage 2: Runner
FROM python:3.11-slim as runner

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory for the runtime
WORKDIR /app

# Copy the built virtual environment and app code from the builder stage
COPY --from=builder /venv /venv
COPY --from=builder /app /app

# Add the virtual environment's bin folder to PATH
ENV PATH="/venv/bin:$PATH"

# Expose port 8000 for the app
EXPOSE 8000

# Start the app using Gunicorn (make sure your wsgi module is correctly defined)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "wsgi:app"]
