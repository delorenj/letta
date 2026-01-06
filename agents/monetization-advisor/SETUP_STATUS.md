# Letta Monetization Agent Setup - Status Document

**Created:** 2026-01-06
**Last Updated:** 2026-01-06 15:35 EST
**Purpose:** Continue this work in Claude Code terminal

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

## Infrastructure State

### Letta Server
- **URL:** https://letta.delo.sh
- **Source:** /home/delorenj/code/letta
- **Compose:** /home/delorenj/code/letta/compose.yaml
- **Status:** Running (freshly updated from Sept 2025 image to latest)

### Database
- PostgreSQL with pgvector extension (manually added)
- Container: letta_db
- pgvector extension installed via: `docker exec letta_db psql -U letta -d letta -c "CREATE EXTENSION IF NOT EXISTS vector;"`

### Configuration Files
- `/home/delorenj/code/letta/.env` - API keys, base URLs
- `~/.letta/config.yaml` - Empty file (was a directory, fixed)
- `~/.letta/credentials` - Empty file (was a directory, fixed)

---

## What We Tried

### 1. Initial Deployment Attempt
- Created agent deployment script at `/home/delorenj/code/letta/agents/monetization-advisor/deploy_agent.py`
- Created memory block files: persona.md, human.md, pipeline.md
- **Error:** Server was running September 2025 image, missing features

### 2. Docker Image Update
```bash
docker pull letta/letta:latest  # Downloaded new image
cd /home/delorenj/code/letta && docker compose down && docker compose up -d
```

### 3. pgvector Extension Missing
- **Error:** `type "vector" does not exist`
- **Fix:** Manually created extension in database
```bash
docker exec letta_db psql -U letta -d letta -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 4. Config File Type Mismatch
- `~/.letta/config.yaml` and `~/.letta/credentials` were directories instead of files
- **Fix:** Removed directories, created empty files

### 5. Sandbox Mount Path Issue
- **Error:** `chmod: cannot access '/home/delorenj': No such file or directory`
- **Fix:** Added explicit env var in compose.yaml:
```yaml
- LETTA_SANDBOX_MOUNT_PATH=/root/.letta/tool_execution_dir
```

### 6. Model Name Format Issues
- First attempt: `openai/gpt-4o` → 404, model not found
- Models endpoint returns list with `openai-proxy/` prefix
- Second attempt: `openai-proxy/anthropic/claude-sonnet-4` → 400, provider not supported
- Third attempt: `anthropic/claude-sonnet-4` → **UNTESTED** (current state)

---

## Current State

### Server Status: RUNNING ✅
```bash
docker ps --filter name=letta
# letta_server and letta_db both running
```

### Agent Deployment: BLOCKED ❌
The deployment script is ready but we haven't found the correct model string format.

**Current model in deploy_agent.py:**
```python
MODEL = "anthropic/claude-sonnet-4"
```

**Available providers per error message:**
- `letta`
- `openai`
- `ollama`

**Hypothesis:** Since `OPENAI_BASE_URL` in .env points to OpenRouter, we may need to use `openai` as the provider but with the OpenRouter model path. Alternatively, check if there's a provider configuration step needed.

---

## Files Created

```
/home/delorenj/code/letta/agents/monetization-advisor/
├── deploy_agent.py   # Main deployment script
├── persona.md        # Agent identity/personality block
├── human.md          # Client context block (Jarad's info)
├── pipeline.md       # Project tracking block
└── README.md         # Usage documentation
```

---

## Next Steps

1. **Test current model format:**
   ```bash
   cd /home/delorenj/code/letta/agents/monetization-advisor
   python3 deploy_agent.py
   ```

2. **If model format still fails, try these alternatives:**
   - `openai/anthropic/claude-sonnet-4`
   - Check Letta ADE at https://letta.delo.sh for model configuration UI
   - Look at `/v1/models` endpoint output more carefully
   - Try with `ollama` provider if you have local models

3. **Check Letta logs for clues:**
   ```bash
   docker logs letta_server 2>&1 | tail -50
   ```

4. **Alternative: Use Letta Cloud ADE**
   The link you shared earlier: https://app.letta.com/development-servers/2beb6723-8868-4090-9b8a-fecf45f46e33/dashboard
   This might provide a UI to create agents and see available models

5. **Verify OpenRouter configuration:**
   The .env has:
   ```
   OPENAI_API_KEY="sk-or-v1-..."  # OpenRouter key
   OPENAI_BASE_URL="https://openrouter.ai/api/v1"
   ```
   This should route "openai" provider calls through OpenRouter.

---

## Key Commands

```bash
# Check server status
docker ps --filter name=letta

# View server logs
docker logs letta_server 2>&1 | tail -50

# Restart server
cd /home/delorenj/code/letta && docker compose restart letta_server

# Full redeploy
cd /home/delorenj/code/letta && docker compose down && docker compose up -d

# Test agent deployment
cd /home/delorenj/code/letta/agents/monetization-advisor && python3 deploy_agent.py

# Test with message
python3 deploy_agent.py --test

# Check available models
curl -s https://letta.delo.sh/v1/models | python3 -m json.tool | head -100

# Health check
curl -s https://letta.delo.sh/v1/health
```

---

## Environment Details

- **letta-client version:** 1.6.5
- **Letta server image:** letta/letta:latest (pulled 2026-01-06)
- **Python:** 3.13 (host system)
- **Host:** delorenj's machine, Long Valley NJ

---

## Transcript Reference

Full conversation transcript available at:
`/mnt/transcripts/2026-01-06-20-32-33-letta-monetization-agent-setup.txt`
