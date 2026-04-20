FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies before copying app code so this layer is cached
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application source
COPY . .

# Create non-root user and hand ownership over to them.
# UID/GID 1000 matches the default on most Linux hosts, making bind-mount
# permissions work without extra configuration.
RUN groupadd --gid 1000 council \
    && useradd --uid 1000 --gid council council \
    && mkdir -p /home/council /app \
    && chown -R council:council /app /home/council

USER council

# data/ is a bind-mount at runtime; 
# init_data_dirs() in run.py creates any missing subdirectories on startup.
# ENTRYPOINT ["uv", "run", "run.py"]
CMD ["uv", "run", "run.py", "--daemon"]
