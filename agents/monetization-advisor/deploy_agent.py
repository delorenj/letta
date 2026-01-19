#!/usr/bin/env python3
"""
Cash Flow Catalyst Agent Deployment
====================================
Creates a monetization-focused advisor agent on the Letta server.

Usage:
    python deploy_agent.py           # Create agent with default model (deepseek)
    python deploy_agent.py --test    # Create and test with a message
    python deploy_agent.py --model kimi  # Use Kimi K2 model (alias)
    python deploy_agent.py --list-models  # Show available approved models
    python deploy_agent.py --delete  # Delete existing agent first

Prerequisites:
    pip install letta-client
"""

from letta_client import Letta
from pathlib import Path
import sys
import argparse

# Configuration
LETTA_BASE_URL = "https://letta.delo.sh"
AGENT_NAME = "cash-flow-catalyst"

# OpenRouter configuration
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1"

# Approved models for OpenRouter (cost-effective, high-quality)
# Format: OpenRouter model path (without provider prefix)
APPROVED_MODELS = {
    "deepseek": "deepseek/deepseek-chat",
    "kimi": "moonshotai/kimi-k2",
    "kimi-thinking": "moonshotai/kimi-k2-thinking",
    "glm": "z-ai/glm-4.7",
}

# Default model (most cost-effective with good reasoning)
DEFAULT_MODEL = "deepseek/deepseek-chat"

# Context windows for approved models
MODEL_CONTEXT_WINDOWS = {
    "deepseek/deepseek-chat": 64000,
    "moonshotai/kimi-k2": 131072,
    "moonshotai/kimi-k2-thinking": 131072,
    "z-ai/glm-4.7": 202752,
}

def load_block(filename: str) -> str:
    """Load memory block content from file."""
    path = Path(__file__).parent / filename
    return path.read_text().strip()


def get_client():
    """Get Letta client connection."""
    return Letta(base_url=LETTA_BASE_URL)


def list_approved_models():
    """Display approved models with their aliases."""
    print("\n📋 Approved Models for OpenRouter:")
    print("-" * 50)
    for alias, model in APPROVED_MODELS.items():
        context = MODEL_CONTEXT_WINDOWS.get(model, "unknown")
        default_marker = " (default)" if model == DEFAULT_MODEL else ""
        print(f"  {alias:15} -> {model}{default_marker}")
        print(f"                    Context window: {context:,}")
    print("-" * 50)


def delete_agent(client, agent_name: str) -> bool:
    """Delete an existing agent by name."""
    try:
        existing_agents = client.agents.list()
        for agent in existing_agents:
            if agent.name == agent_name:
                client.agents.delete(agent.id)
                print(f"🗑️  Deleted existing agent: {agent_name} (ID: {agent.id})")
                return True
        print(f"ℹ️  No agent named '{agent_name}' found to delete.")
        return False
    except Exception as e:
        print(f"⚠️  Error deleting agent: {e}")
        return False


def create_agent(model: str = DEFAULT_MODEL, force_delete: bool = False):
    """Create and configure the Cash Flow Catalyst agent."""

    # Validate model
    if model not in MODEL_CONTEXT_WINDOWS:
        # Check if it's an alias
        if model in APPROVED_MODELS:
            model = APPROVED_MODELS[model]
        else:
            print(f"❌ Model '{model}' is not in the approved list.")
            list_approved_models()
            return None

    context_window = MODEL_CONTEXT_WINDOWS.get(model, 64000)

    # Connect to self-hosted Letta
    client = get_client()

    print(f"🔗 Connecting to Letta at {LETTA_BASE_URL}...")
    print(f"🤖 Model: {model} (context: {context_window:,} tokens)")

    # Delete existing agent if requested
    if force_delete:
        delete_agent(client, AGENT_NAME)

    # Load memory block content
    persona_content = load_block("persona.md")
    human_content = load_block("human.md")
    pipeline_content = load_block("pipeline.md")

    # System instructions that guide agent behavior
    system_instructions = """
You are Cash Flow Catalyst, an aggressive monetization advisor for software developers.

## Your Mission
Help Jarad transform his backlog of projects into revenue streams. Every conversation should move toward first conversion.

## Conversation Flow
1. **Audit Phase**: When discussing a project, immediately identify monetization angles
2. **Validation Phase**: Design quick experiments to test willingness-to-pay
3. **Sprint Phase**: Create 2-week action plans focused on first dollar
4. **Tracking Phase**: Update the pipeline memory block as projects progress

## Key Behaviors
- Challenge "it's just a utility" thinking - everything has value
- Push for specifics: what, who pays, how much, when
- Celebrate small wins - $10 MRR is validation, not failure
- Track progress in the pipeline block obsessively
- Be direct but supportive - accountability partner energy

## Response Format
- Lead with actionable insights, not theory
- Include specific next steps with timelines
- When auditing projects, provide 3+ monetization paths ranked by speed-to-revenue
- Use your pipeline block to track all discussed projects

## Memory Management
- Update the human block when learning new info about Jarad's situation
- Update the pipeline block when projects change status
- Record revenue milestones in pipeline tracking table
"""
    
    try:
        # Check if agent already exists
        existing_agents = client.agents.list()
        for agent in existing_agents:
            if agent.name == AGENT_NAME:
                print(f"⚠️  Agent '{AGENT_NAME}' already exists (ID: {agent.id})")
                print("   Use --delete flag to recreate, or interact with existing agent.")
                return agent

        # Create the agent with memory blocks
        # Use llm_config to explicitly specify OpenRouter endpoint
        agent_state = client.agents.create(
            name=AGENT_NAME,
            llm_config={
                "model": model,  # e.g., "deepseek/deepseek-chat"
                "model_endpoint_type": "openai",  # OpenRouter uses OpenAI-compatible API
                "model_endpoint": OPENROUTER_ENDPOINT,
                "context_window": context_window,
            },
            # Use Letta's free embedding model
            embedding_config={
                "embedding_endpoint_type": "openai",
                "embedding_endpoint": "https://embeddings.letta.com/",
                "embedding_model": "letta-free",
                "embedding_dim": 1536,
                "embedding_chunk_size": 300,
            },
            system=system_instructions,
            memory_blocks=[
                {
                    "label": "persona",
                    "value": persona_content,
                    "description": "Agent identity and operating principles for monetization advisory"
                },
                {
                    "label": "human",
                    "value": human_content,
                    "description": "Client context including situation, skills, constraints, and goals"
                },
                {
                    "label": "pipeline",
                    "value": pipeline_content,
                    "description": "Active monetization pipeline tracking projects through discovery to revenue"
                }
            ],
            # Include default memory tools
            include_base_tools=True,
        )

        print(f"\n✅ Agent created successfully!")
        print(f"   Name: {agent_state.name}")
        print(f"   ID: {agent_state.id}")
        print(f"   Model: {model}")
        print(f"\n🔗 View in ADE: https://app.letta.com")
        print(f"   (Add remote server: {LETTA_BASE_URL})")

        return agent_state

    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_agent(agent_id: str):
    """Send a test message to verify the agent works."""
    client = get_client()

    print("\n📨 Sending test message...")
    print("   Message: 'Hey Marcus! Ready to dig into my project backlog and find some money?'")

    try:
        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[
                {
                    "role": "user",
                    "content": "Hey Marcus! Ready to dig into my project backlog and find some money?"
                }
            ]
        )

        print("\n🤖 Agent response:")
        for msg in response.messages:
            if hasattr(msg, 'content') and msg.content:
                print(f"   {msg.content}")
            elif hasattr(msg, 'tool_call'):
                print(f"   [Tool call: {msg.tool_call.name}]")
            elif hasattr(msg, 'reasoning'):
                print(f"   💭 {msg.reasoning[:100]}..." if len(msg.reasoning) > 100 else f"   💭 {msg.reasoning}")

    except Exception as e:
        print(f"❌ Error sending message: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="Deploy the Cash Flow Catalyst monetization agent to Letta",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy_agent.py                    # Create with default model (deepseek)
  python deploy_agent.py --model kimi       # Use Kimi K2 model
  python deploy_agent.py --delete --test    # Recreate and test
  python deploy_agent.py --list-models      # Show available models
        """
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL}). Can be alias (deepseek, kimi, glm) or full path."
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Send a test message after creating the agent"
    )
    parser.add_argument(
        "--delete", "-d",
        action="store_true",
        help="Delete existing agent before creating new one"
    )
    parser.add_argument(
        "--list-models", "-l",
        action="store_true",
        help="List approved models and exit"
    )

    args = parser.parse_args()

    if args.list_models:
        list_approved_models()
        return

    # Resolve model alias if provided
    model = args.model
    if model in APPROVED_MODELS:
        model = APPROVED_MODELS[model]

    agent = create_agent(model=model, force_delete=args.delete)

    if args.test and agent:
        test_agent(agent.id)


if __name__ == "__main__":
    main()
