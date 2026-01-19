# Anthropic MAX OAuth Proxy

OpenAI-compatible proxy for Anthropic MAX subscription. Allows tools like Letta that expect OpenAI-style APIs to use your Anthropic MAX/Pro subscription instead of paying per-API-call.

## How It Works

1. Authenticates with Anthropic using OAuth (same flow as Claude Code/OpenCode)
2. Translates OpenAI-format requests to Anthropic format
3. Forwards requests with Bearer token auth
4. Translates responses back to OpenAI format

## Quick Start

### 1. Start the Proxy

```bash
# With Docker Compose (recommended)
cd /home/delorenj/code/letta
docker compose up -d anthropic_max_proxy

# Or locally for development
cd /home/delorenj/code/letta/services/anthropic-max-proxy
mise run install
mise run dev
```

### 2. Authenticate with Anthropic MAX

```bash
# Get the OAuth URL
curl http://localhost:8100/auth/start

# Visit the URL in your browser and authenticate with your Claude account
# Copy the authorization code (format: CODE#STATE)

# Complete the flow
curl -X POST http://localhost:8100/auth/callback \
  -H 'Content-Type: application/json' \
  -d '{"code": "YOUR_CODE_HERE"}'
```

### 3. Test It

```bash
curl -X POST http://localhost:8100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "claude-sonnet-4",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

## Using with Letta

Update your Letta agent to use the proxy instead of OpenRouter:

```python
from letta_client import Letta

client = Letta(base_url="https://letta.delo.sh")

# Create agent with Anthropic MAX via proxy
agent = client.agents.create(
    name="my-agent",
    llm_config={
        "model": "claude-sonnet-4",  # Any model alias from the proxy
        "model_endpoint_type": "openai",
        "model_endpoint": "http://anthropic_max_proxy:8100/v1",  # Docker internal
        # Or external: "https://anthropic-proxy.delo.sh/v1"
        "context_window": 200000,
    },
    embedding_config={
        "embedding_endpoint_type": "openai",
        "embedding_endpoint": "https://embeddings.letta.com/",
        "embedding_model": "letta-free",
        "embedding_dim": 1536,
        "embedding_chunk_size": 300,
    },
    system="You are a helpful assistant.",
)
```

## Available Models

| Alias | Anthropic Model |
|-------|-----------------|
| `claude-sonnet-4` | claude-sonnet-4-20250514 |
| `claude-opus-4` | claude-opus-4-20250514 |
| `claude-3.5-sonnet` | claude-3-5-sonnet-20241022 |
| `claude-3.5-haiku` | claude-3-5-haiku-20241022 |
| `claude-3-opus-20240229` | claude-3-opus-20240229 |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /auth/status` | Check authentication status |
| `GET /auth/start` | Start OAuth flow (returns URL) |
| `POST /auth/callback` | Complete OAuth with code |
| `POST /auth/logout` | Clear stored tokens |
| `GET /v1/models` | List available models |
| `POST /v1/chat/completions` | Chat completions (OpenAI format) |

## Configuration

Environment variables (prefix: `ANTHROPIC_PROXY_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | 0.0.0.0 | Server bind host |
| `PORT` | 8100 | Server bind port |
| `LOG_LEVEL` | INFO | Logging level |
| `TOKEN_FILE` | ~/.config/anthropic-max-proxy/tokens.json | Token storage path |

## Token Storage

OAuth tokens are stored in `~/.config/anthropic-max-proxy/tokens.json` with 0600 permissions. Tokens auto-refresh when expired.

## Limitations

- Only chat completions supported (no embeddings, no image generation)
- Tool use translation may have edge cases
- Streaming works but may have minor formatting differences
