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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# Removed unused imports: json, ssl (MCP only), time, Request (old endpoint only)
from openai import AzureOpenAI
from pydantic import BaseModel
import newrelic.agent
# MCP imports removed - using only Azure agents
# from fastmcp import Client
# from mcp.types import Tool
# Old OpenAI imports removed - using only Azure agents
# from openai import AsyncOpenAI, APIConnectionError, AuthenticationError

# LangGraph imports
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain.agents import create_agent

# Add parent directory to path to import utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils import process_headers

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

newrelic.agent.initialize()

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
        delay_seconds: int = 0
    ):
        self.azure_endpoint = azure_endpoint
        self.azure_api_key = azure_api_key
        self.model_name = model_name
        self.api_version = api_version
        self.delay_seconds = delay_seconds
        self.specialist_response = None

        # Initialize LLM
        self.llm = AzureChatOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key,
            api_version=api_version,
            azure_deployment=model_name,
            temperature=0.7,
            streaming=False
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
        def delegate_to_specialist(query: str) -> str:
            """Delegate complex financial queries to the specialist agent for detailed analysis."""
            return self._invoke_specialist_sync(query)

        # Create the coordinator agent with delegation tool using create_agent
        self.coordinator_agent = create_agent(
            model=self.llm,
            tools=[delegate_to_specialist],
            system_prompt="""You are a coordinator agent for Relibank banking services.

Your job is to analyze ALL customer requests and route them to our financial specialist for detailed assistance.

For EVERY request, use the delegate_to_specialist tool to get comprehensive financial guidance from our specialist team.""",
            name="coordinator",
        )

        # Build the agent graph
        self.graph = self._build_graph()

    def _invoke_specialist_sync(self, query: str) -> str:
        """Synchronous wrapper for specialist invocation"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._invoke_specialist_tool(query))

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
        result = await self.specialist_agent.ainvoke({"messages": [HumanMessage(content=query)]})

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
        result = await self.coordinator_agent.ainvoke({"messages": [HumanMessage(content=state["input_message"])]})

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
        logger.info("Synthesizer creating final response")

        start_time = datetime.utcnow()

        system_msg = SystemMessage(content="""You are a friendly customer service coordinator for Relibank.
Your job is to take detailed specialist analysis and present it in a friendly, customer-focused way.
Be warm, helpful, and ensure the customer understands the key points.""")

        synthesis_prompt = HumanMessage(content=f"""Based on our financial specialist's analysis below, provide a friendly summary for the customer.

Specialist's analysis:
{state['specialist_response']}

Create a warm, helpful response that highlights the key recommendations.""")

        messages = [system_msg, synthesis_prompt]

        # Invoke synthesizer LLM
        response = await self.llm.ainvoke(messages)

        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        logger.info(f"Synthesizer completed in {latency_ms:.2f}ms")

        return {
            **state,
            "messages": state["messages"] + [response],
            "final_response": response.content
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

            # Run the graph
            logger.info(f"Starting LangGraph workflow for message: {message[:50]}...")

            final_state = await self.graph.ainvoke(initial_state)

            # Calculate metrics
            end_time = datetime.utcnow()
            total_latency_ms = (end_time - start_time).total_seconds() * 1000
            total_tokens = final_state.get("coordinator_tokens", 0) + final_state.get("specialist_tokens", 0)

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
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating response.")


@app.post("/chatbot-service/assistant/chat", response_model=AssistantChatResponse)
@newrelic.agent.background_task(name='handle_assistant_chat_langgraph')
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
        # Create LangGraph service
        langgraph_service = LangGraphChatbotService(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_api_key=AZURE_OPENAI_API_KEY,
            model_name="gpt-4-1",
            api_version="2024-05-01-preview",
            delay_seconds=ASSISTANT_B_DELAY_SECONDS
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
    return "ok"

@app.get("/chatbot-service/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Simple health check endpoint."""
    return {"status": "healthy"}

# @app.get("/health", response_model=HealthResponse)
# async def health_check() -> HealthResponse:
#     """Simple health check endpoint."""
#     if is_ready:
#         return HealthResponse(status="healthy")
#     else:
#         raise HTTPException(status_code=503, detail="AI service is not ready.")
