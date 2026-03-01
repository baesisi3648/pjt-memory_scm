FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy app code
COPY . .

# Run seed if DB doesn't exist, then start server
CMD ["sh", "-c", "python scripts/seed.py 2>/dev/null; uvicorn app.main:app --host 0.0.0.0 --port 8000"]
