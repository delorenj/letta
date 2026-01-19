FROM python:3.12-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install dependencies with uv
RUN uv pip install --system -e .

# Create config directory
RUN mkdir -p /root/.config/anthropic-max-proxy

# Expose port
EXPOSE 8100

# Run the proxy
CMD ["python", "-m", "anthropic_max_proxy.main"]
