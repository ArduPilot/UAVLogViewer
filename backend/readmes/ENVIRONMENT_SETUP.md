# Environment Setup for UAV Log Viewer Chatbot

## Required Environment Variables

### OpenAI API Configuration

The chatbot requires an OpenAI API key to function. The system now uses the newer **Responses API** by default for improved conversation handling.

```bash
# Required: Your OpenAI API key
export OPENAI_API_KEY="your_openai_api_key_here"
```

Get your API key from: https://platform.openai.com/api-keys

### Optional Configuration

```bash
# LLM Provider Selection (optional)
# Options: 
#   - "openai" (default) - Uses new Responses API with conversation chaining
#   - "openai-chat" - Uses legacy Chat Completions API  
#   - "mock" - For testing without API calls
export LLM_PROVIDER="openai"

# Database paths (optional, defaults shown)
export SQLITE_DB_PATH="data/sessions.sqlite"
export DUCKDB_DB_PATH="data/telemetry.duckdb"

# Server configuration (optional)
export HOST="0.0.0.0"
export PORT="8000"
export LOG_LEVEL="info"
```

## Setup Instructions

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your OpenAI API key:**
   ```bash
   export OPENAI_API_KEY="your_actual_api_key"
   ```

3. **Start the server:**
   ```bash
   cd backend && uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info
   ```

## API Versions

### Responses API (Default)
- **Provider**: `"openai"` or `"openai-responses"`
- **Features**: Stateful conversations, automatic context management, lower token usage
- **Requirements**: `openai>=1.30.0`

### Legacy Chat Completions API
- **Provider**: `"openai-chat"` or `"openai-legacy"`  
- **Features**: Traditional stateless chat completions
- **Use case**: Fallback option if Responses API has issues

### Mock Client
- **Provider**: `"mock"`
- **Features**: No API calls, returns test responses
- **Use case**: Development and testing without API costs

## Migration Notes

The system has been upgraded to use OpenAI's newer Responses API by default. This provides:

- **Better conversation continuity** - Context preserved automatically across turns
- **Reduced token usage** - No need to resend full conversation history  
- **Improved performance** - Lower latency through server-side state management

Existing installations will automatically use the new API. To revert to the legacy API, set `LLM_PROVIDER="openai-chat"`. 