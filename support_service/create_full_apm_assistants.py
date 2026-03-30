#!/usr/bin/env python3
"""
Script to create Azure OpenAI Assistants for Full APM Demo.
Run this once to create Risk Assessment Agent (gpt-4o) and High Risk Assessment Agent (gpt-4o-mini).
Both agents return JSON format: {"score": float, "reason": string}
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

    print("Creating Azure OpenAI Assistants for Full APM Demo...")
    print(f"Endpoint: {azure_endpoint}")
    print()

    # Create Risk Assessment Agent (gpt-4o)
    print("Creating Risk Assessment Agent (gpt-4o)...")
    risk_assessment_agent = client.beta.assistants.create(
        name="Relibank Risk Assessment Agent",
        instructions="""You are a risk assessment agent for Relibank banking services.
Your primary function is to analyze transactions, spending patterns, user behavior, and account activity
to return a risk assessment in JSON format.

Risk Score Guidelines:
- 0.0 - 0.2: No risk (normal, expected behavior)
- 0.3 - 0.4: Low risk (minor anomalies, within acceptable range)
- 0.5 - 0.6: Medium risk (unusual patterns, requires monitoring)
- 0.7 - 0.8: High risk (suspicious activity, recommend review)
- 0.9 - 1.0: Critical risk (likely fraud, immediate action required)

When analyzing requests:
1. Evaluate transaction amounts, frequency, and patterns
2. Consider user behavior and historical trends
3. Identify anomalies or suspicious indicators
4. Calculate a risk score between 0.0 and 1.0
5. Return your assessment in JSON format

IMPORTANT: Always return your response in this exact JSON format:
{
  "score": <float between 0.0 and 1.0>,
  "reason": "<brief explanation of the risk assessment>"
}

Be precise with your scoring. Use the full range of 0.0-1.0 based on the severity of risk indicators.""",
        model="gpt-4o",
        tools=[]
    )

    print(f"✓ Risk Assessment Agent created: {risk_assessment_agent.id}")
    print()

    # Create High Risk Assessment Agent (gpt-4o-mini)
    print("Creating High Risk Assessment Agent (gpt-4o-mini)...")
    high_risk_assessment_agent = client.beta.assistants.create(
        name="Relibank High Risk Assessment Agent",
        instructions="""You are a high risk assessment agent for Relibank banking services.
Your primary function is to analyze transactions, spending patterns, user behavior, and account activity
to identify and flag ONLY critical/high-risk cases. You return risk assessments in JSON format
with scores in the narrow range of 0.9 to 1.0.

Risk Score Guidelines (same as standard risk assessment):
- 0.0 - 0.2: No risk (normal, expected behavior)
- 0.3 - 0.4: Low risk (minor anomalies, within acceptable range)
- 0.5 - 0.6: Medium risk (unusual patterns, requires monitoring)
- 0.7 - 0.8: High risk (suspicious activity, recommend review)
- 0.9 - 1.0: Critical risk (likely fraud, immediate action required)

Your Assessment Criteria:
1. Evaluate transaction amounts, frequency, and patterns using the same criteria
2. Consider user behavior and historical trends
3. Identify anomalies or suspicious indicators
4. Calculate the risk score using the full 0.0-1.0 scale internally
5. ONLY return scores in the 0.9-1.0 range for critical risks

IMPORTANT: Always return your response in this exact JSON format:
{
  "score": <float between 0.9 and 1.0>,
  "reason": "<brief explanation of the critical risk assessment>"
}

If your internal assessment determines the risk is below 0.9 (not critical), return:
{
  "score": 0.9,
  "reason": "Risk assessment below critical threshold. <brief explanation>"
}

You are a conservative filter that ONLY flags critical risks worthy of immediate attention.""",
        model="gpt-4o-mini",
        tools=[]
    )

    print(f"✓ High Risk Assessment Agent created: {high_risk_assessment_agent.id}")
    print()

    # Print environment variables to set
    print("=" * 60)
    print("SUCCESS! Copy these environment variables:")
    print("=" * 60)
    print(f"export RISK_ASSESSMENT_AGENT_ID={risk_assessment_agent.id}")
    print(f"export HIGH_RISK_ASSESSMENT_AGENT_ID={high_risk_assessment_agent.id}")
    print()
    print("Add these to your:")
    print("  - Local environment (.env file or shell)")
    print("  - Dockerfile ARG/ENV variables")
    print("  - Kubernetes ConfigMap")
    print("=" * 60)

if __name__ == "__main__":
    main()
