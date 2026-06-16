FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MVP_HOST=0.0.0.0 \
    MVP_PORT=8765 \
    PARKFLOW_ORIGINAL_DIR="/app/original_v0"

WORKDIR /app

# Install system deps for ChromaDB / reportlab
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY deploy/backend-requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt

# Application code
COPY mvp-app /app/mvp-app
COPY original_v0 /app/original_v0

WORKDIR /app/mvp-app
EXPOSE 8765

CMD ["sh", "-c", "export MVP_PORT=\"${PORT:-${MVP_PORT:-8765}}\"; exec python server.py"]
