"""
Azure Assistants API implementation for support service.
This version uses the actual Azure OpenAI Assistants created with create_assistants.py
"""
import asyncio
import time
from datetime import datetime
from typing import Optional
import json
import newrelic.agent
from openai import AzureOpenAI

logger = None  # Will be set from main module


class AzureAssistantsService:
    """Service for managing Azure OpenAI Assistants API interactions"""

    def __init__(self, client: AzureOpenAI, assistant_a_id: str, assistant_b_id: str, delay_seconds: int = 0):
        self.client = client
        self.assistant_a_id = assistant_a_id
        self.assistant_b_id = assistant_b_id
        self.delay_seconds = delay_seconds
        self.assistant_b_invoked = False

    @newrelic.agent.function_trace(name='invoke_azure_assistant')
    async def invoke_assistant_a(self, thread_id: str, message: str) -> dict:
        """Invoke Azure Assistant A (Coordinator) using Assistants API"""
        start_time = datetime.utcnow()

        event_params = {
            'eventType': 'AzureAssistantInvocation',
            'assistantId': self.assistant_a_id,
            'assistantName': 'coordinator',
            'threadId': thread_id,
            'inputLength': len(message),
            'timestamp': start_time.isoformat()
        }

        try:
            # Add message to thread
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )

            # Create run with Assistant A
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_a_id
            )

            # Poll for completion with function handling
            result = await self._poll_run_completion(thread_id, run.id)

            # Calculate metrics
            end_time = datetime.utcnow()
            latency_ms = (end_time - start_time).total_seconds() * 1000

            # Update event params
            event_params.update({
                'status': 'success',
                'latencyMs': latency_ms,
                'totalTokens': result['usage']['total_tokens'],
                'estimatedCost': self._calculate_cost(result['usage']),
                'assistantBInvoked': self.assistant_b_invoked
            })

            # Record to New Relic
            newrelic.agent.record_custom_event('AzureAssistantInvocation', event_params)
            newrelic.agent.record_custom_metric('Custom/Azure/Assistant/Latency', latency_ms)
            newrelic.agent.record_custom_metric('Custom/Azure/Assistant/Tokens', result['usage']['total_tokens'])

            return result

        except Exception as e:
            if logger:
                logger.error(f"Error in invoke_assistant_a: {e}", exc_info=True)
            event_params.update({'status': 'error', 'errorType': type(e).__name__})
            newrelic.agent.record_custom_event('AzureAssistantInvocation', event_params)
            newrelic.agent.notice_error()
            raise

    async def _poll_run_completion(self, thread_id: str, run_id: str) -> dict:
        """Poll run until completion, handling function calls for agent-to-agent"""
        assistant_b_invoked = False
        total_tokens = 0

        while True:
            await asyncio.sleep(1)  # Poll every second
            run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)

            if run.status == 'completed':
                # Get the latest message
                messages = self.client.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=1)

                # Calculate token usage
                if run.usage:
                    total_tokens = run.usage.total_tokens

                return {
                    'output': messages.data[0].content[0].text.value if messages.data else "No response",
                    'usage': {
                        'prompt_tokens': run.usage.prompt_tokens if run.usage else 0,
                        'completion_tokens': run.usage.completion_tokens if run.usage else 0,
                        'total_tokens': total_tokens
                    },
                    'assistant_b_invoked': assistant_b_invoked
                }

            elif run.status == 'requires_action':
                # Handle function calls (agent-to-agent communication)
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []

                for tool_call in tool_calls:
                    if tool_call.function.name == 'invoke_specialist_agent':
                        assistant_b_invoked = True
                        self.assistant_b_invoked = True

                        # Record agent-to-agent call
                        newrelic.agent.record_custom_event('AgentToAgentCall', {
                            'eventType': 'AgentToAgentCall',
                            'sourceAgent': 'assistant-a',
                            'targetAgent': 'assistant-b',
                            'threadId': thread_id,
                            'functionName': tool_call.function.name
                        })

                        # Invoke Assistant B
                        if logger:
                            logger.info(f"Assistant A calling Assistant B with function {tool_call.function.name}")

                        output = await self._invoke_assistant_b(tool_call)
                        tool_outputs.append({'tool_call_id': tool_call.id, 'output': output})

                # Submit tool outputs back to Assistant A
                self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=tool_outputs
                )

            elif run.status in ['failed', 'cancelled', 'expired']:
                error_details = ""
                if hasattr(run, 'last_error') and run.last_error:
                    error_details = f" - {run.last_error}"
                if logger:
                    logger.error(f"Run failed with status: {run.status}{error_details}")
                raise Exception(f"Run failed with status: {run.status}{error_details}")

    async def _invoke_assistant_b(self, tool_call) -> str:
        """Invoke Assistant B (Specialist) via Assistants API"""
        start_time = datetime.utcnow()

        # Parse arguments
        args = json.loads(tool_call.function.arguments)
        query = args.get('query', 'Provide financial analysis')

        # DEMO: Add artificial delay if configured
        if self.delay_seconds > 0:
            if logger:
                logger.info(f"Artificially delaying Assistant B by {self.delay_seconds} seconds for demo")
            await asyncio.sleep(self.delay_seconds)

        try:
            # Create new thread for Assistant B
            thread_b = self.client.beta.threads.create()

            # Add message
            self.client.beta.threads.messages.create(
                thread_id=thread_b.id,
                role="user",
                content=query
            )

            # Create run with Assistant B
            run = self.client.beta.threads.runs.create(
                thread_id=thread_b.id,
                assistant_id=self.assistant_b_id
            )

            # Poll for completion
            while True:
                await asyncio.sleep(1)
                run = self.client.beta.threads.runs.retrieve(thread_id=thread_b.id, run_id=run.id)

                if run.status == 'completed':
                    messages = self.client.beta.threads.messages.list(thread_id=thread_b.id, order="desc", limit=1)
                    response = messages.data[0].content[0].text.value if messages.data else "No response from specialist"

                    # Calculate metrics
                    end_time = datetime.utcnow()
                    latency_ms = (end_time - start_time).total_seconds() * 1000

                    # Record metrics
                    newrelic.agent.record_custom_event('AzureAssistantInvocation', {
                        'eventType': 'AzureAssistantInvocation',
                        'assistantId': self.assistant_b_id,
                        'assistantName': 'specialist',
                        'threadId': thread_b.id,
                        'latencyMs': latency_ms,
                        'artificialDelayMs': self.delay_seconds * 1000,
                        'totalTokens': run.usage.total_tokens if run.usage else 0,
                        'status': 'success'
                    })

                    if logger:
                        logger.info(f"Assistant B completed in {latency_ms:.2f}ms")

                    return response

                elif run.status in ['failed', 'cancelled', 'expired']:
                    error_details = ""
                    if hasattr(run, 'last_error') and run.last_error:
                        error_details = f" - {run.last_error}"
                    if logger:
                        logger.error(f"Assistant B run failed with status: {run.status}{error_details}")
                    return f"Error: Assistant B run failed with status {run.status}{error_details}"

        except Exception as e:
            if logger:
                logger.error(f"Error invoking Assistant B: {e}", exc_info=True)
            newrelic.agent.notice_error()
            return f"Error invoking specialist: {str(e)}"

    def _calculate_cost(self, usage: dict) -> float:
        """Calculate cost for GPT-4 ($2.50/1M input, $10/1M output)"""
        input_cost = (usage.get('prompt_tokens', 0) / 1_000_000) * 2.50
        output_cost = (usage.get('completion_tokens', 0) / 1_000_000) * 10.00
        return input_cost + output_cost
