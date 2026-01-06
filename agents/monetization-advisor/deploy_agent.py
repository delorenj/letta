#!/usr/bin/env python3
"""
Cash Flow Catalyst Agent Deployment
====================================
Creates a monetization-focused advisor agent on the Letta server.

Usage:
    python deploy_agent.py

Prerequisites:
    pip install letta-client
"""

from letta_client import Letta
from pathlib import Path
import sys

# Configuration
LETTA_BASE_URL = "https://letta.delo.sh"
AGENT_NAME = "cash-flow-catalyst"

# Model configuration - OpenRouter via OPENAI_BASE_URL in .env
# Since OPENAI_BASE_URL points to OpenRouter, use OpenRouter model paths
MODEL = "anthropic/claude-sonnet-4"  
CONTEXT_WINDOW = 200000
# Note: Embedding not specified - let Letta use server defaults

def load_block(filename: str) -> str:
    """Load memory block content from file."""
    path = Path(__file__).parent / filename
    return path.read_text().strip()


def create_agent():
    """Create and configure the Cash Flow Catalyst agent."""
    
    # Connect to self-hosted Letta
    # Note: No API key needed for self-hosted without password protection
    client = Letta(base_url=LETTA_BASE_URL)
    
    print(f"Connecting to Letta at {LETTA_BASE_URL}...")
    
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
                print(f"Agent '{AGENT_NAME}' already exists (ID: {agent.id})")
                print("Delete it first if you want to recreate.")
                return agent
        
        # Create the agent with memory blocks
        agent_state = client.agents.create(
            name=AGENT_NAME,
            model=MODEL,
            context_window_limit=CONTEXT_WINDOW,
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
        
        print(f"✅ Agent created successfully!")
        print(f"   Name: {agent_state.name}")
        print(f"   ID: {agent_state.id}")
        print(f"   Model: {MODEL}")
        print(f"\n🔗 View in ADE: {LETTA_BASE_URL}/agents/{agent_state.id}")
        
        return agent_state
        
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        raise


def test_agent(agent_id: str):
    """Send a test message to verify the agent works."""
    client = Letta(base_url=LETTA_BASE_URL)
    
    print("\n📨 Sending test message...")
    
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
        if hasattr(msg, 'content'):
            print(f"   {msg.content}")
        elif hasattr(msg, 'tool_call'):
            print(f"   [Tool call: {msg.tool_call.name}]")


if __name__ == "__main__":
    agent = create_agent()
    
    if "--test" in sys.argv and agent:
        test_agent(agent.id)
