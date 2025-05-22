# chatbot/websocket_handler.py
async def handle_message(session_id, message, telemetry_data):
    session_manager = SessionManager()
    llm_processor = LLMProcessor()
    
    # Update conversation history
    session_manager.update_history(session_id, "user", message)
    
    # Get LLM response
    llm_response = llm_processor.generate_response(
        session_manager.sessions[session_id]["history"]
    )
    
    # Handle function calls
    if llm_response.tool_calls:
        tool_response = DataTools.execute_query(
            llm_response.tool_calls[0].function.arguments["metric"],
            telemetry_data
        )
        session_manager.update_history(session_id, "tool", str(tool_response))
        return llm_processor.generate_response(
            session_manager.sessions[session_id]["history"]
        )
    
    return llm_response.content