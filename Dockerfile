# ChuoSmart optional container runtime.
#
# This file is used by Render (or local Docker) only. Namecheap/cPanel does not
# execute it, so the existing Passenger + virtualenv production deployment is
# unchanged.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_ENV=render

WORKDIR /app

# Keep dependency installation in its own cacheable layer.
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

# Copy application source after dependencies so ordinary code changes rebuild
# quickly. .dockerignore keeps local envs, media, secrets and git history out.
COPY . .

RUN chmod +x /app/deploy/render/start.sh \
    && addgroup --system chuosmart \
    && adduser --system --ingroup chuosmart --home /home/chuosmart chuosmart \
    && mkdir -p /app/logs /app/media /app/private_media /app/staticfiles \
    && chown -R chuosmart:chuosmart /app /home/chuosmart

USER chuosmart

# Render injects PORT at runtime. 10000 is its conventional default and this
# EXPOSE is documentation only; the startup script always binds to $PORT.
EXPOSE 10000

CMD ["/app/deploy/render/start.sh"]
