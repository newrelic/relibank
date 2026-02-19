#!/usr/bin/env python3
"""
Script to create Azure OpenAI Assistants for Relibank.
Run this once to create Assistant A (Coordinator) and Assistant B (Specialist).
"""
from openai import AzureOpenAI
import os
import sys

def main():
    # Get environment variables
    # azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    # azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = "a8be72ce0fe64c4d8a1386042a935c19"
    azure_endpoint = "https://eastus.api.cognitive.microsoft.com/"

    if not azure_api_key or not azure_endpoint:
        print("ERROR: AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT must be set")
        print("Example:")
        print("  export AZURE_OPENAI_ENDPOINT='https://relibank-openai.openai.azure.com/'")
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

    # Create Assistant A (Coordinator)
    print("Creating Assistant A (Coordinator)...")
    assistant_a = client.beta.assistants.create(
        name="Relibank Coordinator Agent",
        instructions="""You are a coordinator agent for Relibank banking services.
You help customers with general banking inquiries, account information, and transaction queries.

When you need detailed financial analysis, spending pattern analysis, or complex financial insights,
call the invoke_specialist_agent function to get help from a financial specialist.

Be friendly, professional, and helpful. Always prioritize customer satisfaction.""",
        model="gpt-4-1",
        tools=[{
            "type": "function",
            "function": {
                "name": "invoke_specialist_agent",
                "description": "Invoke the financial specialist agent for detailed financial analysis, spending patterns, investment advice, or complex financial queries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The detailed analysis request to send to the specialist"
                        }
                    },
                    "required": ["query"]
                }
            }
        }]
    )

    print(f"✓ Assistant A created: {assistant_a.id}")
    print()

    # Create Assistant B (Specialist)
    print("Creating Assistant B (Financial Specialist)...")
    assistant_b = client.beta.assistants.create(
        name="Relibank Financial Specialist",
        instructions="""You are a financial analysis specialist for Relibank.
You provide detailed financial insights, spending pattern analysis, investment recommendations,
and complex financial calculations.

Provide thorough, data-driven analysis with actionable recommendations.
Be precise with numbers and calculations. Explain financial concepts clearly.""",
        model="gpt-4-1",
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
