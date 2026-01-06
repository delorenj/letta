# Cash Flow Catalyst - Letta Agent

A monetization-focused AI advisor that helps transform dormant projects into revenue streams.

## Quick Start

```bash
# Install the Letta client
pip install letta-client

# Deploy the agent
python deploy_agent.py

# Deploy and send test message
python deploy_agent.py --test
```

## Agent Identity

**Marcus Chen** - Serial entrepreneur turned monetization consultant. Philosophy: every piece of software can generate income. Specializes in rapid monetization of developer side projects.

## Memory Blocks

| Block | Purpose |
|-------|---------|
| `persona` | Agent identity, operating principles, communication style |
| `human` | Client context (Jarad's situation, skills, constraints) |
| `pipeline` | Active project tracking through monetization stages |

## Usage Patterns

### Project Audit
```
"Let's audit my repo at github.com/delorenj/projectname for monetization potential"
```

### Sprint Planning  
```
"I want to focus on ChoreScore this week. What's the 2-week sprint to first dollar?"
```

### Pipeline Review
```
"Show me where all my projects are in the monetization pipeline"
```

### Revenue Tracking
```
"Update: I got my first $10 from the script license. Let's celebrate and plan the next one."
```

## Configuration

Edit `deploy_agent.py` to adjust:
- `LETTA_BASE_URL` - Your Letta server endpoint
- `MODEL` - LLM model (via OpenRouter)
- `CONTEXT_WINDOW` - Context window size

## Files

```
monetization-advisor/
├── deploy_agent.py   # Deployment script
├── persona.md        # Agent identity block
├── human.md          # Client context block  
├── pipeline.md       # Project tracking block
└── README.md         # This file
```
