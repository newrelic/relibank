# Force rebuild for New Relic logging
import os
import sys
import logging
from contextlib import asynccontextmanager
from typing import Optional, TypedDict, Annotated
from typing_extensions import TypedDict
from datetime import datetime
import asyncio
import operator
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AzureOpenAI, AsyncOpenAI
from pydantic import BaseModel
import newrelic.agent
import tiktoken

newrelic.agent.initialize()

# MCP imports removed - using only Azure agents
# from fastmcp import Client
# from mcp.types import Tool
# Old OpenAI imports removed - using only Azure agents
# from openai import AsyncOpenAI, APIConnectionError, AuthenticationError

# LangGraph imports
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage, ToolCall, ToolMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool, BaseTool
from langchain.agents import create_agent
from typing import List, Any, Optional, Union, Sequence
from langchain_core.runnables import Runnable, RunnablePassthrough

# Add parent directory to path to import utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils import process_headers

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Custom AsyncOpenAI LangChain Wrapper ---
class AsyncOpenAIChatModel(BaseChatModel):
    """Custom LangChain chat model that uses AsyncOpenAI for New Relic instrumentation"""

    client: Any
    model: str = "gpt-4-1"
    temperature: float = 0.7
    bound_tools: List[dict] = []
    nr_trace_id: str = None  # New Relic trace ID from FastAPI endpoint
    nr_span_id: str = None   # New Relic span ID from FastAPI endpoint

    class Config:
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        return "azure-openai-async"

    def _convert_messages_to_openai_format(self, messages: List[BaseMessage]) -> List[dict]:
        """Convert LangChain messages to OpenAI format"""
        openai_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                openai_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, ToolMessage):
                # Tool result message - must follow an assistant message with tool_calls
                openai_messages.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id
                })
            elif isinstance(msg, AIMessage):
                msg_dict = {"role": "assistant", "content": msg.content}
                # Include tool calls if present
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # Convert LangChain tool calls to OpenAI format
                    openai_tool_calls = []
                    for tc in msg.tool_calls:
                        openai_tool_calls.append({
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": json.dumps(tc.get("args", {})) if isinstance(tc.get("args"), dict) else tc.get("args", "{}")
                            }
                        })
                    msg_dict["tool_calls"] = openai_tool_calls
                openai_messages.append(msg_dict)
            elif isinstance(msg, SystemMessage):
                openai_messages.append({"role": "system", "content": msg.content})
        return openai_messages

    def bind_tools(
        self,
        tools: Sequence[Union[dict, type, BaseTool]],
        **kwargs: Any,
    ) -> Runnable:
        """Bind tools to the model for function calling"""
        # Convert tools to OpenAI format
        formatted_tools = []
        for tool_item in tools:
            if isinstance(tool_item, dict):
                formatted_tools.append(tool_item)
            elif hasattr(tool_item, 'name') and hasattr(tool_item, 'description'):
                # LangChain tool object
                tool_dict = {
                    "type": "function",
                    "function": {
                        "name": tool_item.name,
                        "description": tool_item.description,
                    }
                }
                # Add parameters if available
                if hasattr(tool_item, 'args_schema') and tool_item.args_schema:
                    try:
                        tool_dict["function"]["parameters"] = tool_item.args_schema.schema()
                    except:
                        # If schema() doesn't work, provide minimal parameters
                        tool_dict["function"]["parameters"] = {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                formatted_tools.append(tool_dict)

        # Return a new instance with tools bound (preserve trace IDs)
        return AsyncOpenAIChatModel(
            client=self.client,
            model=self.model,
            temperature=self.temperature,
            bound_tools=formatted_tools,
            nr_trace_id=self.nr_trace_id,
            nr_span_id=self.nr_span_id
        )

    @newrelic.agent.function_trace(name='AsyncOpenAI.chat.completions.create')
    async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs) -> ChatResult:
        """Generate using AsyncOpenAI - New Relic will instrument this"""
        openai_messages = self._convert_messages_to_openai_format(messages)

        # Add tools if bound
        api_params = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": self.temperature,
            **kwargs
        }
        if self.bound_tools:
            api_params["tools"] = self.bound_tools

        # Add LLM attributes BEFORE the call using span attributes (not transaction attributes)
        # This targets the specific span New Relic's hooks will create
        newrelic.agent.add_custom_span_attribute('llm.request.model', self.model)
        newrelic.agent.add_custom_span_attribute('llm.model', self.model)
        newrelic.agent.add_custom_span_attribute('request.model', self.model)
        newrelic.agent.add_custom_span_attribute('request.temperature', self.temperature)

        response = await self.client.chat.completions.create(**api_params)

        # Manually add LLM attributes and record events for New Relic AI Monitoring
        if hasattr(response, 'usage') and response.usage:
            model_name = response.model if hasattr(response, 'model') else self.model
            conversation_id = response.id if hasattr(response, 'id') else f"conv_{id(response)}"

            # Add response attributes immediately after call using span attributes
            newrelic.agent.add_custom_span_attribute('llm.response.model', model_name)
            newrelic.agent.add_custom_span_attribute('response.model', model_name)
            newrelic.agent.add_custom_span_attribute('llm.conversation_id', conversation_id)
            newrelic.agent.add_custom_span_attribute('llm.token_count.prompt', response.usage.prompt_tokens)
            newrelic.agent.add_custom_span_attribute('llm.token_count.completion', response.usage.completion_tokens)
            newrelic.agent.add_custom_span_attribute('llm.token_count.total', response.usage.total_tokens)

            logger.info(f"AsyncOpenAI response usage: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens}, total={response.usage.total_tokens}")

            # Get application context for recording events
            app = newrelic.agent.application()

            # Use trace IDs passed from FastAPI endpoint level
            # (transaction context not available in LangChain async context)
            trace_id = self.nr_trace_id if self.nr_trace_id else conversation_id
            span_id = self.nr_span_id if self.nr_span_id else conversation_id

            if trace_id == conversation_id:
                logger.debug(f"Using conversation_id as fallback trace_id (nr_trace_id not available)")
            else:
                logger.info(f"Using passed trace_id={trace_id}")

            # Record prompt messages (LlmChatCompletionMessage events)
            for i, msg in enumerate(openai_messages):
                content = msg.get('content', '')
                # Estimate token count for prompt (rough estimate: ~4 chars per token)
                prompt_token_count = len(content) // 4 if content else 0

                event_data = {
                    'id': f"{conversation_id}_prompt_{i}",
                    'trace_id': trace_id,
                    'span_id': span_id,
                    'vendor': 'azure_openai',
                    'ingest_source': 'Python',
                    'request.model': self.model,
                    'response.model': self.model,  # Also add response.model for consistency
                    'role': msg.get('role', 'user'),
                    'content': content[:1000],  # Truncate for safety
                    'token_count': prompt_token_count,
                    'sequence': i,
                    'is_response': False,
                    'llm.conversation_id': conversation_id,
                }

                newrelic.agent.record_custom_event('LlmChatCompletionMessage', event_data, application=app)

            # Record completion message (response)
            response_content = response.choices[0].message.content or ""
            completion_token_count = len(response_content) // 4 if response_content else response.usage.completion_tokens

            completion_event_data = {
                'id': f"{conversation_id}_completion_0",
                'trace_id': trace_id,
                'span_id': span_id,
                'vendor': 'azure_openai',
                'ingest_source': 'Python',
                'request.model': self.model,
                'response.model': model_name,
                'role': 'assistant',
                'content': response_content[:1000],  # Truncate for safety
                'token_count': completion_token_count,
                'sequence': len(openai_messages),
                'is_response': True,
                'llm.conversation_id': conversation_id,
            }

            newrelic.agent.record_custom_event('LlmChatCompletionMessage', completion_event_data, application=app)

            # Record LlmChatCompletionSummary event with AI Monitoring schema
            # Use dotted notation for nested attributes that UI expects
            summary_event_data = {
                'id': conversation_id,
                'trace_id': trace_id,
                'span_id': span_id,
                'vendor': 'azure_openai',
                'ingest_source': 'Python',
                'request.model': self.model,  # Dotted notation for AI Monitoring UI
                'response.model': model_name,
                'request.temperature': self.temperature,
                'response.number_of_messages': len(openai_messages) + 1,
                'token_count': response.usage.total_tokens,  # Singular for UI
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens,
                'duration': 0,
                'error': False,
                'llm.conversation_id': conversation_id,
            }

            newrelic.agent.record_custom_event('LlmChatCompletionSummary', summary_event_data, application=app)

            logger.info(f"[Direct] New Relic LLM events recorded: conversation_id={conversation_id}, model={model_name}, tokens={response.usage.total_tokens}, messages={len(openai_messages)+1}")
        else:
            logger.warning("AsyncOpenAI response missing usage data!")

        # Extract response content and tool calls
        response_message = response.choices[0].message
        content = response_message.content or ""

        # Handle tool calls if present
        tool_calls = []
        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            for tc in response_message.tool_calls:
                # Parse arguments from JSON string to dict
                args = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse tool call arguments: {args}")
                        args = {}

                tool_calls.append({
                    "name": tc.function.name,
                    "args": args,
                    "id": tc.id,
                    "type": "function"  # Required by OpenAI API
                })

        # Create AIMessage with tool calls
        message = AIMessage(content=content)
        if tool_calls:
            message.tool_calls = tool_calls

        generation = ChatGeneration(message=message)

        # Return ChatResult with token usage metadata
        return ChatResult(
            generations=[generation],
            llm_output={
                "token_usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "model_name": response.model
            }
        )

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs) -> ChatResult:
        """Sync version - not used in our async workflow"""
        raise NotImplementedError("Sync generation not supported, use async")


# --- New Relic LangChain Callback Handler ---
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

class NewRelicCallbackHandler(AsyncCallbackHandler):
    """Custom callback handler for New Relic AI Monitoring integration

    This handler captures LLM completions from LangChain agents and records them
    as New Relic custom events, which populate the AI Monitoring dashboard.
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.info("NewRelicCallbackHandler initialized")
        # Initialize tiktoken for token counting
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
            self.logger.info("tiktoken encoding initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize tiktoken: {e}")
            self.encoding = None

    def _count_tokens(self, content: str) -> int:
        """Count tokens in a string using tiktoken"""
        if self.encoding and isinstance(content, str):
            try:
                return len(self.encoding.encode(content))
            except Exception as e:
                self.logger.warning(f"Token counting failed: {e}")
        return 0

    async def on_llm_start(self, serialized: dict, prompts: List[str], **kwargs) -> None:
        """Called when LLM starts generating"""
        self.logger.info(f"[NR Callback] on_llm_start called with {len(prompts)} prompts")

        # Record prompt message events with token counts
        try:
            # Get the application object for recording events outside transaction context
            app = newrelic.agent.application()
            model_name = serialized.get("model", "gpt-4-1")

            for i, prompt in enumerate(prompts):
                token_count = self._count_tokens(prompt)
                newrelic.agent.record_custom_event('LlmChatCompletionMessage', {
                    'id': f"{id(prompt)}_{i}",
                    'vendor': 'azure_openai',
                    'ingest_source': 'Python',
                    'request_model': model_name,
                    'role': 'user',
                    'content': prompt[:1000],  # Truncate for safety
                    'token_count': token_count,
                    'sequence': i,
                }, application=app)
        except Exception as e:
            self.logger.error(f"Error recording prompt message event: {e}", exc_info=True)

    async def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Called when LLM finishes - capture token usage and record event"""
        try:
            # Get the application object for recording events outside transaction context
            app = newrelic.agent.application()

            # Extract token usage from llm_output
            if response.llm_output and "token_usage" in response.llm_output:
                usage = response.llm_output["token_usage"]
                model_name = response.llm_output.get("model_name", "gpt-4-1")

                # Record completion message events
                for i, generation in enumerate(response.generations):
                    for j, gen in enumerate(generation):
                        completion_text = gen.text if hasattr(gen, 'text') else str(gen.message.content)
                        token_count = self._count_tokens(completion_text)

                        newrelic.agent.record_custom_event('LlmChatCompletionMessage', {
                            'id': f"{id(gen)}_{i}_{j}",
                            'vendor': 'azure_openai',
                            'ingest_source': 'Python',
                            'response_model': model_name,
                            'role': 'assistant',
                            'content': completion_text[:1000],  # Truncate for safety
                            'token_count': token_count,
                            'sequence': i * 10 + j,
                        }, application=app)

                # Record New Relic custom event for LLM completion summary
                newrelic.agent.record_custom_event('LlmChatCompletionSummary', {
                    'vendor': 'azure_openai',
                    'ingest_source': 'Python',
                    'request_model': model_name,
                    'response_model': model_name,
                    'prompt_tokens': usage.get("prompt_tokens", 0),
                    'completion_tokens': usage.get("completion_tokens", 0),
                    'total_tokens': usage.get("total_tokens", 0),
                    'duration': kwargs.get('duration_ms', 0),
                }, application=app)

                # Add span attributes for correlation (must be list of tuples, not dict)
                newrelic.agent.add_custom_attributes([
                    ('llm.vendor', 'azure_openai'),
                    ('llm.model', model_name),
                    ('llm.token_count.prompt', usage.get("prompt_tokens", 0)),
                    ('llm.token_count.completion', usage.get("completion_tokens", 0)),
                    ('llm.token_count.total', usage.get("total_tokens", 0)),
                ])

                self.logger.info(
                    f"[NR Callback] on_llm_end: New Relic LLM event recorded: model={model_name}, "
                    f"tokens={usage.get('total_tokens', 0)}"
                )
        except Exception as e:
            self.logger.error(f"Error recording New Relic LLM event: {e}", exc_info=True)

    async def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Called when LLM errors"""
        self.logger.error(f"LLM error: {error}")
        newrelic.agent.notice_error()


# --- Request/Response Models ---
class ChatResponse(BaseModel):
    response: str


class AssistantChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None


class AssistantChatResponse(BaseModel):
    response: str
    thread_id: str
    metadata: dict


class HealthResponse(BaseModel):
    status: str


# --- Global State ---
# Old client removed - using only Azure agents
# client: Optional[AsyncOpenAI] = None
client = None  # Keep for backward compatibility check in lifespan
is_ready: bool = False
MODEL_ID = "gpt-4-1"  # Azure model name
AZURE_API_VERSION = "2024-05-01-preview"

# Azure OpenAI Assistants configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
ASSISTANT_A_ID = os.getenv("ASSISTANT_A_ID")
ASSISTANT_B_ID = os.getenv("ASSISTANT_B_ID")

# Demo/Testing: Artificial delay for Assistant B (in seconds)
# Set to 5-10 to demonstrate Assistant B as bottleneck in New Relic
ASSISTANT_B_DELAY_SECONDS = int(os.getenv("ASSISTANT_B_DELAY_SECONDS", "0"))

# Azure OpenAI client for assistants
azure_client: Optional[AzureOpenAI] = None


# --- MCP Code --- REMOVED - Using only Azure agents
# server_config = {
#     "mcpServers": {
#         "cloudflare": {
#             "transport": "sse",
#             "url": "https://docs.mcp.cloudflare.com/sse",
#         },
#     }
# }

# # https://mcp.deepwiki.com/sse

# # Create SSL context that doesn't verify certificates (for self-signed certs)
# ssl_context = ssl.create_default_context()
# ssl_context.check_hostname = False
# ssl_context.verify_mode = ssl.CERT_NONE

# try:
#     mcp_client = Client(server_config, ssl_context=ssl_context)
# except TypeError:
#     # If Client doesn't accept ssl_context parameter, try without it
#     logger.warning("Client does not support ssl_context parameter, proceeding without SSL verification override")
#     mcp_client = Client(server_config)

# async def get_tools() -> list[Tool]:
#     """
#     Retrieve the list of tools from the MCP server.
#     """
#     async with mcp_client:
#         tools = await mcp_client.list_tools()
#         return tools


# async def execute_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
#     """
#     Execute a tool on the MCP server with proper error handling.
#     """
#     try:
#         result = await mcp_client.call_tool(tool_name, arguments)
#         return result.data
#     except Exception as e:
#         logger.error(f"Error executing MCP tool {tool_name}: {e}")
#         return {"error": f"Failed to execute tool {tool_name}"}


# def convert_mcp_tools_to_openai_format(mcp_tools: list[Tool]) -> list[dict[str, Any]]:
#     """Convert MCP tool definitions to OpenAI function calling format."""
#     openai_functions = []

#     for tool in mcp_tools:
#         openai_function = {
#             "type": "function",
#             "function": {
#                 "name": tool.name,
#                 "description": tool.description,
#                 "parameters": tool.inputSchema,
#             },
#         }
#         openai_functions.append(openai_function)

#     return openai_functions


# --- Azure Assistant Service ---
# --- LangGraph Multi-Agent Implementation ---

class AgentState(TypedDict):
    """State shared between agents in the LangGraph workflow"""
    messages: Annotated[list, operator.add]
    next_agent: str
    specialist_response: str
    assistant_b_invoked: bool
    input_message: str
    final_response: str
    start_time: datetime
    coordinator_tokens: int
    specialist_tokens: int


class LangGraphChatbotService:
    """Multi-agent chatbot service using LangGraph for orchestration with create_agent"""

    def __init__(
        self,
        azure_endpoint: str,
        azure_api_key: str,
        model_name: str = "gpt-4-1",
        api_version: str = "2024-05-01-preview",
        delay_seconds: int = 0,
        nr_trace_id: str = None,
        nr_span_id: str = None
    ):
        self.azure_endpoint = azure_endpoint
        self.azure_api_key = azure_api_key
        self.model_name = model_name
        self.api_version = api_version
        self.delay_seconds = delay_seconds
        self.specialist_response = None

        # Store New Relic trace IDs from FastAPI endpoint
        self.nr_trace_id = nr_trace_id
        self.nr_span_id = nr_span_id

        # Initialize New Relic callback handler
        self.nr_callback = NewRelicCallbackHandler()

        # Initialize AsyncOpenAI client (New Relic auto-instruments this)
        async_openai_client = AsyncOpenAI(
            api_key=azure_api_key,
            base_url=f"{azure_endpoint}/openai/deployments/{model_name}",
            default_headers={"api-key": azure_api_key},
            default_query={"api-version": api_version}
        )

        # Wrap AsyncOpenAI in our custom LangChain model
        # Pass trace IDs so it can use them in custom events
        self.llm = AsyncOpenAIChatModel(
            client=async_openai_client,
            model=model_name,
            temperature=0.7,
            nr_trace_id=nr_trace_id,
            nr_span_id=nr_span_id
        )

        # Create the specialist agent using create_agent
        self.specialist_agent = create_agent(
            model=self.llm,
            tools=[],
            system_prompt="""You are a financial analysis specialist for Relibank.
You provide detailed financial insights, spending pattern analysis, investment recommendations,
and complex financial calculations.

Provide thorough, data-driven analysis with actionable recommendations.
Be precise with numbers and calculations. Explain financial concepts clearly.""",
            name="specialist",
        )

        # Create the delegate tool for coordinator
        @tool
        async def delegate_to_specialist(query: str) -> str:
            """Delegate complex financial queries to the specialist agent for detailed analysis."""
            return await self._invoke_specialist_tool(query)

        # Create the coordinator agent with delegation tool using create_agent
        self.coordinator_agent = create_agent(
            model=self.llm,
            tools=[delegate_to_specialist],
            system_prompt="""You are a coordinator agent for Relibank banking services.

Your job is to analyze ALL customer requests and route them to our financial specialist for detailed assistance.

For EVERY request, use the delegate_to_specialist tool to get comprehensive financial guidance from our specialist team.""",
            name="coordinator",
        )

        # Create the synthesizer agent using create_agent for proper NR instrumentation
        self.synthesizer_agent = create_agent(
            model=self.llm,
            tools=[],
            system_prompt="""You are a friendly customer service coordinator for Relibank.
Your job is to take detailed specialist analysis and present it in a friendly, customer-focused way.
Be warm, helpful, and ensure the customer understands the key points.""",
            name="synthesizer",
        )

        # Build the agent graph
        self.graph = self._build_graph()

    async def _invoke_specialist_tool(self, query: str) -> str:
        """Tool function that invokes the specialist agent"""
        start_time = datetime.utcnow()

        # Apply artificial delay if configured
        if self.delay_seconds > 0:
            logger.info(f"Artificially delaying specialist by {self.delay_seconds} seconds for demo")
            await asyncio.sleep(self.delay_seconds)

        # Record agent-to-agent transition
        newrelic.agent.record_custom_event('AgentToAgentCall', {
            'eventType': 'AgentToAgentCall',
            'sourceAgent': 'coordinator',
            'targetAgent': 'specialist',
            'timestamp': datetime.utcnow().isoformat()
        })

        logger.info("Specialist agent invoked via tool")

        # Invoke the specialist agent created with create_agent
        result = await self.specialist_agent.ainvoke(
            {"messages": [HumanMessage(content=query)]},
            config={"callbacks": [self.nr_callback]}
        )

        # Extract response
        if result and "messages" in result:
            response_text = result["messages"][-1].content
        else:
            response_text = "No response from specialist"

        # Calculate metrics
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        # Record specialist invocation
        newrelic.agent.record_custom_event('LangGraphAgentInvocation', {
            'eventType': 'LangGraphAgentInvocation',
            'agentName': 'specialist',
            'latencyMs': latency_ms,
            'artificialDelayMs': self.delay_seconds * 1000,
            'timestamp': start_time.isoformat(),
            'createdWithCreateAgent': True
        })

        logger.info(f"Specialist completed in {latency_ms:.2f}ms")

        self.specialist_response = response_text
        return response_text

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow using create_agent instances"""
        workflow = StateGraph(AgentState)

        # Add nodes that use the create_agent instances
        workflow.add_node("coordinator", self._coordinator_node)
        workflow.add_node("synthesizer", self._synthesizer_agent)

        # Define entry point
        workflow.set_entry_point("coordinator")

        # Coordinator always goes to synthesizer (delegation happens via tool)
        workflow.add_edge("coordinator", "synthesizer")
        workflow.add_edge("synthesizer", END)

        return workflow.compile()

    async def _coordinator_node(self, state: AgentState) -> AgentState:
        """Coordinator node using create_agent"""
        logger.info("Coordinator agent processing request (using create_agent)")

        start_time = datetime.utcnow()

        # Invoke the coordinator agent created with create_agent
        result = await self.coordinator_agent.ainvoke(
            {"messages": [HumanMessage(content=state["input_message"])]},
            config={"callbacks": [self.nr_callback]}
        )

        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        # Extract response
        if result and "messages" in result:
            response_text = result["messages"][-1].content
        else:
            response_text = "No response from coordinator"

        # Record coordinator invocation
        newrelic.agent.record_custom_event('LangGraphAgentInvocation', {
            'eventType': 'LangGraphAgentInvocation',
            'agentName': 'coordinator',
            'latencyMs': latency_ms,
            'timestamp': start_time.isoformat(),
            'createdWithCreateAgent': True
        })

        logger.info(f"Coordinator completed, specialist response captured: {bool(self.specialist_response)}")

        return {
            **state,
            "messages": result.get("messages", []),
            "next_agent": "synthesizer",
            "assistant_b_invoked": True,  # Always true since we delegate to specialist
            "specialist_response": self.specialist_response or "No specialist response available",
            "coordinator_tokens": 0,  # Tokens tracked in New Relic events
            "specialist_tokens": 0
        }

    # OLD METHODS - Replaced with create_agent approach
    # These methods are no longer used as we now use langchain.agents.create_agent
    # Keeping commented for reference

    # async def _coordinator_agent(self, state: AgentState) -> AgentState:
    #     """OLD: Coordinator agent - replaced by create_agent"""
    #     pass

    # def _route_after_coordinator(self, state: AgentState) -> Literal["specialist", "end"]:
    #     """OLD: Router function - no longer needed with create_agent tool delegation"""
    #     pass

    # async def _specialist_agent(self, state: AgentState) -> AgentState:
    #     """OLD: Specialist agent - replaced by create_agent"""
    #     pass

    async def _synthesizer_agent(self, state: AgentState) -> AgentState:
        """Synthesizer agent - creates friendly summary from specialist's analysis"""
        logger.info("Synthesizer creating final response (using create_agent)")

        start_time = datetime.utcnow()

        synthesis_prompt = f"""Based on our financial specialist's analysis below, provide a friendly summary for the customer.

Specialist's analysis:
{state['specialist_response']}

Create a warm, helpful response that highlights the key recommendations."""

        # Invoke synthesizer agent (wrapped with create_agent for NR observability)
        result = await self.synthesizer_agent.ainvoke(
            {"messages": [HumanMessage(content=synthesis_prompt)]},
            config={"callbacks": [self.nr_callback]}
        )

        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        # Extract response
        if result and "messages" in result:
            response_text = result["messages"][-1].content
        else:
            response_text = "Unable to create summary"

        logger.info(f"Synthesizer completed in {latency_ms:.2f}ms")

        # Record to New Relic
        newrelic.agent.record_custom_event('AgentInvocation', {
            'eventType': 'AgentInvocation',
            'agentName': 'synthesizer',
            'latencyMs': latency_ms,
            'timestamp': start_time.isoformat(),
            'createdWithCreateAgent': True
        })

        return {
            **state,
            "messages": state["messages"] + [result["messages"][-1]],
            "final_response": response_text
        }

    @newrelic.agent.function_trace(name='invoke_langgraph_agents')
    async def invoke(self, message: str) -> dict:
        """Main entry point - invoke the LangGraph workflow"""
        start_time = datetime.utcnow()

        event_params = {
            'eventType': 'LangGraphWorkflowInvocation',
            'inputLength': len(message),
            'timestamp': start_time.isoformat()
        }

        try:
            # Initial state
            initial_state = {
                "messages": [],
                "next_agent": "coordinator",
                "specialist_response": "",
                "assistant_b_invoked": False,
                "input_message": message,
                "final_response": "",
                "start_time": start_time,
                "coordinator_tokens": 0,
                "specialist_tokens": 0
            }

            # Run the graph (AsyncOpenAI underneath will be auto-instrumented by New Relic)
            logger.info(f"Starting LangGraph workflow for message: {message[:50]}...")

            final_state = await self.graph.ainvoke(
                initial_state,
                config={"callbacks": [self.nr_callback]}
            )
            total_tokens = final_state.get("coordinator_tokens", 0) + final_state.get("specialist_tokens", 0)

            # Calculate metrics
            end_time = datetime.utcnow()
            total_latency_ms = (end_time - start_time).total_seconds() * 1000

            # Update event params
            event_params.update({
                'status': 'success',
                'totalLatencyMs': total_latency_ms,
                'totalTokens': total_tokens,
                'assistantBInvoked': final_state.get("assistant_b_invoked", False),
                'estimatedCost': self._calculate_cost(total_tokens)
            })

            # Record to New Relic
            newrelic.agent.record_custom_event('LangGraphWorkflowInvocation', event_params)
            newrelic.agent.record_custom_metric('Custom/LangGraph/Workflow/Latency', total_latency_ms)
            newrelic.agent.record_custom_metric('Custom/LangGraph/Workflow/Tokens', total_tokens)

            return {
                'output': final_state["final_response"],
                'usage': {
                    'total_tokens': total_tokens,
                    'coordinator_tokens': final_state.get("coordinator_tokens", 0),
                    'specialist_tokens': final_state.get("specialist_tokens", 0)
                },
                'assistant_b_invoked': final_state.get("assistant_b_invoked", False),
                'estimated_cost': self._calculate_cost(total_tokens)
            }

        except Exception as e:
            logger.error(f"Error in LangGraph workflow: {e}", exc_info=True)
            event_params.update({'status': 'error', 'errorType': type(e).__name__})
            newrelic.agent.record_custom_event('LangGraphWorkflowInvocation', event_params)
            newrelic.agent.notice_error()
            raise

    def _calculate_cost(self, total_tokens: int) -> float:
        """Calculate cost for GPT-4 ($2.50/1M input, $10/1M output)"""
        # Rough estimate: assume 50/50 split
        input_cost = (total_tokens * 0.5 / 1_000_000) * 2.50
        output_cost = (total_tokens * 0.5 / 1_000_000) * 10.00
        return input_cost + output_cost


# --- FastAPI Application ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle startup and shutdown events.
    Initializes the Azure OpenAI client for LangGraph agents.
    """
    global client, is_ready, azure_client

    # Azure OpenAI initialization (required for LangGraph agents)
    azure_endpoint = AZURE_OPENAI_ENDPOINT
    azure_api_key = AZURE_OPENAI_API_KEY

    if not azure_endpoint or not azure_api_key:
        logger.error("AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY not set. Application will not start.")
        raise RuntimeError("Azure OpenAI credentials are required for startup.")

    try:
        azure_client = AzureOpenAI(
            api_key=azure_api_key,
            api_version="2024-05-01-preview",
            azure_endpoint=azure_endpoint
        )
        is_ready = True
        logger.info("Azure OpenAI client initialized successfully for LangGraph agents.")
    except Exception as e:
        logger.critical(f"Failed to initialize Azure OpenAI client: {e}. Application will not serve requests.")
        is_ready = False
        azure_client = None

    yield

    # Shutdown logic
    logger.info("Shutting down AI chatbot service.")
    # Azure client doesn't need explicit close


app = FastAPI(
    title="Relibank AI Chatbot Service",
    description="Provides multi-agent conversational AI using Azure OpenAI with LangGraph (coordinator + specialist agents).",
    version="0.2.0",
    lifespan=lifespan,
)

# Configure CORS to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # This allows all domains
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# OLD ENDPOINT - Redirects to Azure agents
@app.post("/chatbot-service/chat", response_model=ChatResponse)
async def chat_with_model(prompt: str) -> ChatResponse:
    """
    Legacy endpoint - now routes to Azure LangGraph agents.
    For new integrations, use /chatbot-service/assistant/chat instead.
    """
    if not is_ready:
        raise HTTPException(
            status_code=503,
            detail="AI service is not ready. Check logs for connection errors during startup.",
        )

    try:
        logger.info(f"Received prompt on legacy endpoint: '{prompt}' - routing to Azure agents")

        # Route to Azure agent workflow
        request_obj = AssistantChatRequest(message=prompt, thread_id=None)
        azure_response = await assistant_chat(request_obj)

        return ChatResponse(response=azure_response.response)

    except Exception as e:
        newrelic.agent.notice_error(attributes={
            'service': 'chatbot',
            'endpoint': '/chatbot-service/chat',
            'action': 'chat_with_model'
        })
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating response.")


@app.post("/chatbot-service/assistant/chat", response_model=AssistantChatResponse)
async def assistant_chat(request: AssistantChatRequest) -> AssistantChatResponse:
    """
    Chat with LangGraph multi-agent workflow (agent-to-agent capability)
    """
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Azure OpenAI not configured. Check AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY."
        )

    try:
        # Get New Relic transaction context at the endpoint level
        transaction = newrelic.agent.current_transaction()
        nr_trace_id = None
        nr_span_id = None
        if transaction:
            nr_trace_id = transaction.trace_id
            nr_span_id = transaction.guid
            logger.info(f"[FastAPI] New Relic trace_id={nr_trace_id}, span_id={nr_span_id}")
        else:
            logger.warning("[FastAPI] No New Relic transaction context available")

        # Create LangGraph service
        langgraph_service = LangGraphChatbotService(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_api_key=AZURE_OPENAI_API_KEY,
            model_name="gpt-4-1",
            api_version="2024-05-01-preview",
            delay_seconds=ASSISTANT_B_DELAY_SECONDS,
            nr_trace_id=nr_trace_id,
            nr_span_id=nr_span_id
        )

        # Invoke the workflow
        result = await langgraph_service.invoke(request.message)

        # Generate a thread_id for consistency (LangGraph doesn't use threads like Assistants API)
        import uuid
        thread_id = request.thread_id if request.thread_id else f"langgraph-{uuid.uuid4().hex[:16]}"

        return AssistantChatResponse(
            response=result['output'],
            thread_id=thread_id,
            metadata={
                'tokens_used': result['usage']['total_tokens'],
                'cost': result.get('estimated_cost', 0),
                'assistant_b_invoked': result.get('assistant_b_invoked', False),
                'coordinator_tokens': result['usage'].get('coordinator_tokens', 0),
                'specialist_tokens': result['usage'].get('specialist_tokens', 0)
            }
        )

    except Exception as e:
        logger.error(f"LangGraph chat error: {e}", exc_info=True)
        newrelic.agent.notice_error()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chatbot-service/")
async def ok():
    """Root return 200"""
    newrelic.agent.ignore_transaction()
    return "ok"

@app.get("/chatbot-service/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Simple health check endpoint."""
    newrelic.agent.ignore_transaction()
    return {"status": "healthy"}

# @app.get("/health", response_model=HealthResponse)
# async def health_check() -> HealthResponse:
#     """Simple health check endpoint."""
#     if is_ready:
#         return HealthResponse(status="healthy")
#     else:
#         raise HTTPException(status_code=503, detail="AI service is not ready.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003, log_config="logging.conf")
