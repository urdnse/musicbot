# Add Deno (JavaScript runtime) to solve YouTube challenges
RUN apt-get update && apt-get install -y curl unzip && \
    curl -fsSL https://deno.land/install.sh | sh
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"
