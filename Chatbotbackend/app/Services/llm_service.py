import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic 

from app.models import ChatMessageInput 

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI


# Load environment variables from .env file in project root
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env') 
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f".env file loaded from llm_service.py (path: {dotenv_path})")
else:
    load_dotenv() 
    print("llm_service.py: Attempted to load .env from default location or environment variables are already set.")

# Get API keys from environment
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Factory method to initialize the appropriate LangChain LLM instance
def get_llm_instance(provider: str = "gemini", temperature: float = 0.6, max_tokens: int = 2048):
    """
    Returns an instance of a Langchain LLM based on the provider.
    API keys are expected to be in environment variables (loaded from .env).
    """
    if provider == "gemini":
        api_key_to_use = GEMINI_API_KEY
        
        model_name = "gemini-1.5-flash-latest" 

        # Handle empty or missing API key
        if GEMINI_API_KEY == "": 
            print(f"GEMINI_API_KEY is an empty string (Canvas default). Passing None to ChatGoogleGenerativeAI. Langchain will attempt default auth for model '{model_name}'.")
            api_key_to_use = None 
        elif not GEMINI_API_KEY:
            print(f"Warning: GEMINI_API_KEY is not set. LLM calls for Gemini model '{model_name}' may fail if GOOGLE_API_KEY is also not set or Application Default Credentials are not configured.")
            api_key_to_use = None
        else:
            print(f"Using GEMINI_API_KEY from environment for model '{model_name}'.")

        # Return configured instance of Gemini-based chat model
        return ChatGoogleGenerativeAI(
            model=model_name, 
            google_api_key=api_key_to_use, 
            temperature=temperature,
            top_p=0.95, 
            top_k=40,  
            max_output_tokens=max_tokens,
            convert_system_message_to_human=True
        )
    elif provider == "anthropic":
        effective_anthropic_key = ANTHROPIC_API_KEY
        if not effective_anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY is not set in .env or environment.")
        return ChatAnthropic(
            model="claude-3-sonnet-20240229", 
            anthropic_api_key=effective_anthropic_key,
            temperature=temperature,
            max_tokens=max_tokens
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

# Convert frontend (Vue) chat history to LangChain-compatible format
def convert_vue_history_to_langchain_messages(vue_history: List[ChatMessageInput]) -> List[BaseMessage]:
    """Converts Vue.js style history to Langchain Message objects."""
    langchain_messages: List[BaseMessage] = []
    for msg in vue_history:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant": 
            langchain_messages.append(AIMessage(content=msg.content))
    return langchain_messages

# Main method for querying the LLM
async def call_llm_api(
    system_prompt_with_context: str, 
    user_query: str, 
    vue_chat_history: List[ChatMessageInput], 
    llm_provider: str = "gemini"
) -> str:
    """
    Calls the specified LLM provider using Langchain.
    """
    try:
        llm = get_llm_instance(provider=llm_provider)
    except ValueError as e:
        print(f"LLM Initialization Error: {e}")
        return f"Error: LLM provider '{llm_provider}' is not configured correctly. {str(e)}"

    langchain_history_messages = convert_vue_history_to_langchain_messages(vue_chat_history)

    # Prepare messages for LLM input
    messages_for_llm: List[BaseMessage] = [
        SystemMessage(content=system_prompt_with_context)
    ]
    messages_for_llm.extend(langchain_history_messages)
    messages_for_llm.append(HumanMessage(content=user_query))
    
    print(f"--- Sending to Langchain ({llm_provider}) ---")

    try:
        response_message = await llm.ainvoke(messages_for_llm)
        
        # Return message content if response is valid
        if isinstance(response_message, AIMessage) and isinstance(response_message.content, str):
            return response_message.content
        else:
            print(f"Unexpected response type or content from Langchain: {type(response_message)}, content: {getattr(response_message, 'content', 'N/A')}")
            return "LLM Error: Received an unexpected response structure from the AI model via Langchain."

    except Exception as e:
        print(f"Error during Langchain LLM call ({llm_provider}): {e}")
        error_detail = str(e)
        # Attempt to extract error details from exception
        if hasattr(e, 'args') and e.args:
            first_arg = e.args[0]
            if isinstance(first_arg, str):
                if "api key" in first_arg.lower() or "permission_denied" in first_arg.lower() or "quota" in first_arg.lower(): 
                    error_detail = f"API key/permission issue for {llm_provider}. Please check your .env configuration, ensure the key is valid, and the API is enabled with sufficient quota. Original error: {first_arg}"
                else:
                    error_detail = first_arg
            elif isinstance(first_arg, dict) and 'message' in first_arg:
                 error_detail = first_arg['message']
        
        # More specific checks for common HTTP-like errors that might be wrapped by Langchain
        if "401" in error_detail or "unauthorized" in error_detail.lower() or ("API key" in error_detail.lower() and "invalid" in error_detail.lower()):
             error_detail = f"Authentication error with {llm_provider} (e.g., invalid API key). Please check your .env file. Details: {error_detail}"
        elif "403" in error_detail or "forbidden" in error_detail.lower() or "quota" in error_detail.lower() or "permission_denied" in error_detail.lower():
             error_detail = f"Permission denied by {llm_provider} (e.g., API key lacks permissions, API not enabled, or quota exceeded). Details: {error_detail}"
        elif "model" in error_detail.lower() and ("not found" in error_detail.lower() or "not supported" in error_detail.lower()):
            error_detail = f"Model configuration error for {llm_provider}. The model specified might be incorrect or not supported with your current API key/setup. Details: {error_detail}"


        return f"LLM Error with {llm_provider}: {error_detail}"
