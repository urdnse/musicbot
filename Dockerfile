# 1. Start with a Python base image (Essential Fix)
FROM python:3.11-slim

# 2. Install FFmpeg, system tools, and Deno (Mandatory for 2026 YouTube)
RUN apt-get update && apt-get install -y ffmpeg git curl unzip && \
    curl -fsSL https://deno.land/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*

# 3. Set Deno path environment variables
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "bot.py"]
