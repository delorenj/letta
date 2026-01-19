# Letta Monetization Agent Setup - Status Document

**Created:** 2026-01-06
**Last Updated:** 2026-01-06 17:30 EST
**Status:** AGENT CREATED - Awaiting OpenRouter credits

---

## Goal

Create a **Cash Flow Catalyst** Letta agent - a monetization-focused AI advisor that helps transform dormant projects into revenue streams. The agent should:

1. Audit existing projects/repos for hidden revenue potential
2. Design rapid experiments to validate willingness-to-pay
3. Create actionable 2-week sprints to first conversion
4. Track projects through a monetization pipeline
5. Maintain persistent memory about Jarad's situation, projects, and progress

### Agent Identity: Marcus Chen

- Serial entrepreneur who monetized 200+ side projects
- Philosophy: "Quantity over perfection" - stack small income streams
- Communication: Direct, high-energy, challenges "it's just a utility" thinking

---

## Current State: SUCCESS

### Agent Created

- **Agent ID:** `agent-e282cc49-cc18-49de-92e0-0d7bffa95ec7`
- **Agent Name:** `cash-flow-catalyst`
- **Model:** `deepseek/deepseek-chat` via OpenRouter
- **Context Window:** 64,000 tokens
- **Embedding:** Letta free embeddings

### Server Status: RUNNING

- **URL:** https://letta.delo.sh
- **Health:** OK (v0.16.1)

### Next Action Required

Add credits to OpenRouter account: https://openrouter.ai/settings/credits

Error when messaging: `402 - requires more credits (have 1,899, need ~16,000)`

---

## Working Configuration Pattern

### The Key Discovery: `llm_config` dict

When using OpenRouter (or any OpenAI-compatible endpoint), you **must** use an explicit `llm_config` dict - not just the `model=` parameter.

**WRONG** (causes "Provider not supported" error):
```python
client.agents.create(
    name="my-agent",
    model="deepseek/deepseek-chat",  # Won't work!
)
```

**CORRECT:**
```python
client.agents.create(
    name="my-agent",
    llm_config={
        "model": "deepseek/deepseek-chat",  # Plain OpenRouter model path
        "model_endpoint_type": "openai",     # OpenRouter is OpenAI-compatible
        "model_endpoint": "https://openrouter.ai/api/v1",
        "context_window": 64000,
    },
    embedding_config={
        "embedding_endpoint_type": "openai",
        "embedding_endpoint": "https://embeddings.letta.com/",
        "embedding_model": "letta-free",
        "embedding_dim": 1536,
        "embedding_chunk_size": 300,
    },
    # ... other params
)
```

### Embedding Config Required

Letta SDK requires explicit `embedding_config`. Use Letta's free embedding service:

```python
embedding_config={
    "embedding_endpoint_type": "openai",
    "embedding_endpoint": "https://embeddings.letta.com/",
    "embedding_model": "letta-free",
    "embedding_dim": 1536,
    "embedding_chunk_size": 300,
}
```

### Docker Compose Environment

The server needs `OPENAI_API_KEY` set to your OpenRouter key:

```yaml
# compose.yaml
environment:
  - OPENAI_API_KEY=${OPENROUTER_API_KEY_LETTA}  # From system secrets
```

**Important:** `docker compose restart` doesn't reload environment variables. Use:
```bash
docker compose down && docker compose up -d
```

---

## Approved Models (Cost-Effective via OpenRouter)

| Alias | Model Path | Context Window |
|-------|------------|----------------|
| deepseek | `deepseek/deepseek-chat` | 64,000 |
| kimi | `moonshotai/kimi-k2` | 131,072 |
| kimi-thinking | `moonshotai/kimi-k2-thinking` | 131,072 |
| glm | `z-ai/glm-4.7` | 202,752 |

Avoid expensive providers: anthropic, openai, grok

---

## Files

```
/home/delorenj/code/letta/agents/monetization-advisor/
├── deploy_agent.py   # Main deployment script (working!)
├── persona.md        # Agent identity/personality block
├── human.md          # Client context block (Jarad's info)
├── pipeline.md       # Project tracking block
├── README.md         # Usage documentation
└── SETUP_STATUS.md   # This file
```

---

## Key Commands

```bash
# Deploy agent (default: deepseek)
python3 deploy_agent.py

# Deploy with specific model
python3 deploy_agent.py --model kimi

# Deploy and test with message
python3 deploy_agent.py --test

# Delete and recreate
python3 deploy_agent.py --delete --test

# List approved models
python3 deploy_agent.py --list-models

# Check server health
curl -s https://letta.delo.sh/v1/health

# View server logs
docker logs letta_server 2>&1 | tail -50

# Restart server (with env reload)
cd /home/delorenj/code/letta && docker compose down && docker compose up -d
```

---

## Troubleshooting

### "Provider X is not supported"

Use `llm_config` dict with `model_endpoint_type: "openai"` instead of plain `model=` parameter.

### "Must specify embedding or embedding_config"

Add `embedding_config` with Letta's free embedding model (see above).

### "Authentication failed / User not found (401)"

- OpenRouter API key is invalid or expired
- Generate new key at https://openrouter.ai/keys
- Update your secrets and restart containers with `docker compose down && up -d`

### "Error code: 402 - requires more credits"

- Add credits at https://openrouter.ai/settings/credits
- This error means auth is working, just need more credits

---

## Environment

- **letta-client version:** 1.6.5+
- **Letta server image:** letta/letta:latest (v0.16.1)
- **Python:** 3.13
- **OpenRouter API key:** Stored in `$OPENROUTER_API_KEY_LETTA` (system secrets)
