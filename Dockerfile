FROM python:3.11-slim

WORKDIR /app

# System deps for SSL/healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ALL project files (including new ai_*.py modules)
COPY . .

# Persist SQLite DB across deploys (Koyeb volume mount target)
VOLUME ["/app/data"]
ENV DB_PATH=/app/data/bot_factory.db

# Koyeb sets $PORT automatically; default to 8080 locally
ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:${PORT}/health || exit 1

CMD ["python", "-u", "bot.py"]
