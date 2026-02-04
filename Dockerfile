# Use a lightweight Python Linux server
FROM python:3.11-slim

# 1. Install FFmpeg and system tools (The important part!)
RUN apt-get update && \
    apt-get install -y ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# 2. Set up the folder
WORKDIR /app

# 3. Copy your files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 4. Start the bot
CMD ["python", "bot.py"]
