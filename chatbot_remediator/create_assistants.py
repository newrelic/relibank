#!/usr/bin/env python3
"""
Script to create Azure OpenAI Assistants for Remediator.
Run this once to create Coordinator and Remediator agents.
"""
from openai import AzureOpenAI
import os
import sys

def main():
    # Get environment variables
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

    if not azure_api_key or not azure_endpoint:
        print("ERROR: AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT must be set")
        print("Example:")
        print("  export AZURE_OPENAI_ENDPOINT='https://eastus.api.cognitive.microsoft.com/'")
        print("  export AZURE_OPENAI_API_KEY='your-api-key'")
        sys.exit(1)

    # Initialize client
    # Note: Assistants API requires api_version 2024-05-01-preview or later
    client = AzureOpenAI(
        api_key=azure_api_key,
        api_version="2024-05-01-preview",
        azure_endpoint=azure_endpoint
    )

    print("Creating Azure OpenAI Assistants...")
    print(f"Endpoint: {azure_endpoint}")
    print()

    # Create Coordinator Agent
    print("Creating Coordinator Agent...")
    assistant_a = client.beta.assistants.create(
        name="Remediator Coordinator Agent",
        instructions="""You are a coordinator agent for the Remediator system.
You help users understand system issues, analyze telemetry data, and coordinate remediation efforts.

When you need to fix issues, apply remediations, or make system changes based on New Relic data,
call the invoke_remediator_agent function to delegate to the remediator specialist.

Be clear, concise, and action-oriented. Focus on problem-solving and system reliability.""",
        model="remediator-agents",
        tools=[{
            "type": "function",
            "function": {
                "name": "invoke_remediator_agent",
                "description": "Invoke the remediator agent to fix issues, apply changes, or remediate problems based on New Relic telemetry data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The remediation request with context from New Relic data"
                        }
                    },
                    "required": ["query"]
                }
            }
        }]
    )

    print(f"✓ Assistant A created: {assistant_a.id}")
    print()

    # Create Remediator Agent
    print("Creating Remediator Agent...")
    assistant_b = client.beta.assistants.create(
        name="Remediator Agent",
        instructions="""You are a remediator agent specializing in fixing system issues based on New Relic telemetry data.
You analyze observability data (metrics, logs, traces, events) from New Relic and take corrective actions.

Your responsibilities:
- Analyze New Relic alerts, incidents, and anomalies
- Identify root causes from telemetry data
- Apply automated remediations (restart services, scale resources, clear caches, etc.)
- Provide detailed remediation reports with data-driven justifications

Be systematic, data-driven, and thorough. Always reference specific New Relic data points in your analysis.""",
        model="remediator-agents",
        tools=[]
    )

    print(f"✓ Assistant B created: {assistant_b.id}")
    print()

    # Print environment variables to set
    print("=" * 60)
    print("SUCCESS! Copy these environment variables:")
    print("=" * 60)
    print(f"export ASSISTANT_A_ID={assistant_a.id}")
    print(f"export ASSISTANT_B_ID={assistant_b.id}")
    print()
    print("Add these to your:")
    print("  - Local environment (.env file or shell)")
    print("  - Dockerfile ARG/ENV variables")
    print("  - Kubernetes ConfigMap (azure-assistant-config)")
    print("=" * 60)

if __name__ == "__main__":
    main()
