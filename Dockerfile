FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for networking, build tools, and Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser dependencies
RUN playwright install --with-deps chromium || true

# Copy application source code
COPY . .

# Set default port for Render / Cloud health check
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Run 24/7 Autonomous Outreach Background Daemon
CMD ["python", "main.py", "daemon"]
