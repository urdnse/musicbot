# 1. Use an official Python base image
FROM python:3.11-slim

# 2. Install FFmpeg and system tools
RUN apt-get update && apt-get install -y ffmpeg git curl unzip && rm -rf /var/lib/apt/lists/*

# 3. REQUIRED FOR 2026: Install Deno (JavaScript runtime)
# YouTube now requires a JS engine to solve challenges
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "bot.py"]
