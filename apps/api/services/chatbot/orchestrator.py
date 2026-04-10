"""
Chat orchestrator for Gemini API integration with function calling.
Manages the conversation loop and tool execution.
Supports both Google AI Studio and Vertex AI backends.
"""

import json
import uuid
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .tools import TOOL_DEFINITIONS
from .tool_executor import ToolExecutor
from .prompts import get_system_prompt
from config import settings

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """Orchestrates chat conversations using Gemini with function calling"""

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        redis_client=None
    ):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.redis_client = redis_client
        self.use_vertex = settings.USE_VERTEX_AI

        # Initialize tool executor
        self.tool_executor = ToolExecutor(neo4j_uri, neo4j_user, neo4j_password)

        # Initialize the appropriate backend
        if self.use_vertex:
            self._init_vertex_ai()
        else:
            self._init_google_ai()

    def _init_google_ai(self):
        """Initialize Google AI Studio backend"""
        import google.generativeai as genai
        from google.generativeai.types import FunctionDeclaration, Tool

        logger.info("Initializing Google AI Studio backend")
        genai.configure(api_key=settings.GOOGLE_API_KEY)

        # Build Gemini tools
        self.gemini_tools = self._build_gemini_tools()

        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name=settings.CHATBOT_MODEL,
            tools=self.gemini_tools,
            system_instruction=get_system_prompt()
        )

        # Generation config
        self.generation_config = genai.GenerationConfig(
            temperature=settings.CHATBOT_TEMPERATURE,
            max_output_tokens=settings.CHATBOT_MAX_TOKENS,
        )

    def _init_vertex_ai(self):
        """Initialize Vertex AI backend"""
        import vertexai
        from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration, GenerationConfig

        logger.info(f"Initializing Vertex AI backend (project: {settings.VERTEX_PROJECT_ID}, location: {settings.VERTEX_LOCATION})")

        # Initialize Vertex AI
        vertexai.init(
            project=settings.VERTEX_PROJECT_ID,
            location=settings.VERTEX_LOCATION
        )

        # Build tools for Vertex AI
        self.gemini_tools = self._build_vertex_tools()

        # Initialize the model
        self.model = GenerativeModel(
            model_name=settings.CHATBOT_MODEL,
            tools=self.gemini_tools,
            system_instruction=get_system_prompt()
        )

        # Generation config
        self.generation_config = GenerationConfig(
            temperature=settings.CHATBOT_TEMPERATURE,
            max_output_tokens=settings.CHATBOT_MAX_TOKENS,
        )

    def _build_gemini_tools(self):
        """Convert tool definitions to Gemini Tool format (Google AI Studio)"""
        from google.generativeai.types import FunctionDeclaration, Tool

        function_declarations = []
        for tool_def in TOOL_DEFINITIONS:
            func_decl = FunctionDeclaration(
                name=tool_def["name"],
                description=tool_def["description"],
                parameters=tool_def["parameters"]
            )
            function_declarations.append(func_decl)

        return [Tool(function_declarations=function_declarations)]

    def _build_vertex_tools(self):
        """Convert tool definitions to Vertex AI Tool format"""
        from vertexai.generative_models import Tool, FunctionDeclaration

        function_declarations = []
        for tool_def in TOOL_DEFINITIONS:
            func_decl = FunctionDeclaration(
                name=tool_def["name"],
                description=tool_def["description"],
                parameters=tool_def["parameters"]
            )
            function_declarations.append(func_decl)

        return [Tool(function_declarations=function_declarations)]

    async def process_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and return the assistant's response.
        Handles the full conversation loop including tool calls.
        """
        start_time = time.time()

        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = f"conv-{uuid.uuid4().hex[:12]}"

        # Load or create conversation history
        history = await self._load_conversation_history(conversation_id)

        tools_used = []
        tool_data = {}

        try:
            # Start a chat session with history
            chat = self.model.start_chat(history=history)

            # Send the user message
            response = chat.send_message(
                message,
                generation_config=self.generation_config
            )

            # Handle function calls in a loop
            tool_call_count = 0
            max_tool_calls = settings.CHATBOT_MAX_TOOL_CALLS

            while True:
                # Safety check for response structure
                if not response.candidates:
                    logger.warning("No candidates in response")
                    break

                candidate = response.candidates[0]
                if not hasattr(candidate, 'content') or not candidate.content:
                    logger.warning("No content in candidate")
                    break

                if not hasattr(candidate.content, 'parts') or not candidate.content.parts:
                    logger.warning("No parts in content")
                    break

                # Check if there are function calls
                function_calls = []
                for part in candidate.content.parts:
                    # Log part type for debugging
                    logger.debug(f"Part type: {type(part)}, Part: {part}")

                    fc = getattr(part, 'function_call', None)
                    if fc is not None:
                        # Check if it has a name (handles both Google AI and Vertex AI)
                        fc_name = getattr(fc, 'name', None)
                        if fc_name:
                            function_calls.append(fc)

                if not function_calls:
                    # No more function calls, we have the final response
                    break

                if tool_call_count >= max_tool_calls:
                    logger.warning(f"Max tool calls ({max_tool_calls}) reached")
                    break

                # Execute each function call and build response parts
                response_parts = []
                for fc in function_calls:
                    tool_name = fc.name
                    tool_args = dict(fc.args) if hasattr(fc, 'args') and fc.args else {}

                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                    # Execute the tool
                    result = self.tool_executor.execute_tool(tool_name, tool_args)

                    tools_used.append(tool_name)
                    tool_data[tool_name] = result
                    tool_call_count += 1

                    # Prepare function response part based on backend
                    response_parts.append(self._build_function_response(tool_name, result))

                # Send function responses back to Gemini as a single content
                response = chat.send_message(
                    self._build_response_content(response_parts),
                    generation_config=self.generation_config
                )

            # Extract the final text response
            final_response = ""
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    # Handle both Google AI and Vertex AI text extraction
                    text_content = getattr(part, 'text', None)
                    if text_content:
                        final_response += text_content

            if not final_response:
                final_response = "I processed your request but couldn't generate a response."

            # Save conversation history
            await self._save_conversation_history(
                conversation_id,
                message,
                final_response,
                tools_used
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "response": final_response,
                "conversation_id": conversation_id,
                "tools_used": list(set(tools_used)),
                "data": tool_data if tool_data else None,
                "metadata": {
                    "model": settings.CHATBOT_MODEL,
                    "processing_time_ms": processing_time_ms,
                    "tool_calls_count": tool_call_count,
                    "backend": "vertex_ai" if self.use_vertex else "google_ai_studio"
                }
            }

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            raise

    def _build_function_response(self, tool_name: str, result: Dict):
        """Build function response part based on backend"""
        if self.use_vertex:
            from vertexai.generative_models import Part
            return Part.from_function_response(
                name=tool_name,
                response={"result": json.dumps(result)}
            )
        else:
            import google.generativeai as genai
            return genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=tool_name,
                    response={"result": json.dumps(result)}
                )
            )

    def _build_response_content(self, response_parts: List):
        """Build response content based on backend"""
        if self.use_vertex:
            from vertexai.generative_models import Content
            return Content(parts=response_parts, role="function")
        else:
            import google.generativeai as genai
            return genai.protos.Content(parts=response_parts)

    async def _load_conversation_history(
        self,
        conversation_id: str
    ) -> List:
        """Load conversation history from Redis"""
        if not self.redis_client:
            return []

        try:
            history_key = f"chat:history:{conversation_id}"
            history_data = self.redis_client.get(history_key)

            if history_data:
                history_list = json.loads(history_data)
                # Convert to appropriate content format based on backend
                contents = []
                for msg in history_list:
                    contents.append(self._build_history_content(msg["role"], msg["content"]))
                return contents

        except Exception as e:
            logger.error(f"Error loading conversation history: {str(e)}")

        return []

    def _build_history_content(self, role: str, content: str):
        """Build history content based on backend"""
        if self.use_vertex:
            from vertexai.generative_models import Content, Part
            return Content(role=role, parts=[Part.from_text(content)])
        else:
            from google.generativeai.types import content_types
            return content_types.to_content({
                "role": role,
                "parts": [{"text": content}]
            })

    async def _save_conversation_history(
        self,
        conversation_id: str,
        user_message: str,
        assistant_response: str,
        tools_used: List[str]
    ):
        """Save conversation history to Redis"""
        if not self.redis_client:
            return

        try:
            history_key = f"chat:history:{conversation_id}"

            # Load existing history
            existing = self.redis_client.get(history_key)
            if existing:
                history = json.loads(existing)
            else:
                history = []

            # Add new messages
            history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            history.append({
                "role": "model",
                "content": assistant_response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tools_used": tools_used
            })

            # Trim history if too long (keep last 20 messages)
            if len(history) > 20:
                history = history[-20:]

            # Save with TTL
            self.redis_client.setex(
                history_key,
                settings.CHATBOT_CONVERSATION_TTL,
                json.dumps(history)
            )

        except Exception as e:
            logger.error(f"Error saving conversation history: {str(e)}")

    async def clear_conversation(self, conversation_id: str) -> bool:
        """Clear conversation history"""
        if not self.redis_client:
            return False

        try:
            history_key = f"chat:history:{conversation_id}"
            self.redis_client.delete(history_key)
            return True
        except Exception as e:
            logger.error(f"Error clearing conversation: {str(e)}")
            return False
