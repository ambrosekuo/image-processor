FROM python:3.11-slim

# For watchdog (inotify) and basic build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install -U pip && pip install -e ".[dev]"

EXPOSE 8002
CMD ["bgremove-api", "--host", "0.0.0.0", "--port", "8002"]
