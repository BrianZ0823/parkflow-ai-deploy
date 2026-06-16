FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MVP_HOST=0.0.0.0 \
    MVP_PORT=8765 \
    PARKFLOW_ORIGINAL_DIR="/app/original V0"

WORKDIR /app

COPY ["MVP DEMO/deploy/backend-requirements.txt", "/tmp/backend-requirements.txt"]
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt

COPY ["MVP DEMO/mvp-app", "/app/mvp-app"]
COPY ["original V0/agent", "/app/original V0/agent"]
COPY ["original V0/data", "/app/original V0/data"]
COPY ["original V0/db", "/app/original V0/db"]
COPY ["original V0/external_api", "/app/original V0/external_api"]
COPY ["original V0/mcp_servers", "/app/original V0/mcp_servers"]
COPY ["original V0/skills", "/app/original V0/skills"]
COPY ["original V0/tools", "/app/original V0/tools"]
COPY ["original V0/main.py", "/app/original V0/main.py"]
COPY ["original V0/mcp_client.py", "/app/original V0/mcp_client.py"]
COPY ["original V0/requirements.txt", "/app/original V0/requirements.txt"]

WORKDIR /app/mvp-app
EXPOSE 8765

CMD ["sh", "-c", "export MVP_PORT=\"${PORT:-${MVP_PORT:-8765}}\"; exec python server.py"]
