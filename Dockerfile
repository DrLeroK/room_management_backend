# ==============================================================================
# Multi-Stage Production Dockerfile for StayCraft Room Management Backend
# ==============================================================================

# Stage 1: Build & Dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production Final Runtime
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/django/.local/bin:${PATH}" \
    DJANGO_ENV=production \
    PORT=8000

# Install runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged application user
RUN groupadd -g 1000 django && \
    useradd -u 1000 -g django -s /bin/sh -m django

# Copy installed Python packages from builder
COPY --from=builder --chown=django:django /root/.local /home/django/.local

# Copy application source code
COPY --chown=django:django . .

# Ensure storage directories exist with correct permissions
RUN mkdir -p /app/staticfiles /app/media && \
    chown -R django:django /app && \
    chmod +x /app/docker-entrypoint.sh

USER django

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
