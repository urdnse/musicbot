# 1. Use a lightweight Python server as the base
FROM python:3.11-slim

# 2. Install FFmpeg, Git, and Deno (Required for YouTube 2026 challenges)
RUN apt-get update && \
    apt-get install -y ffmpeg git curl unzip && \
    curl -fsSL https://deno.land/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*

# Set Deno path
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

# 3. Set up the folder
WORKDIR /app

# 4. Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the code
COPY . .

# 6. Start the bot
CMD ["python", "bot.py"]
