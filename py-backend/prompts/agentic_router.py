
def get_routing_prompt(query: str) -> str:

    routing_instruction_prompt = """
    ### Task:
    You are a UAV analysis query router. Given a user query, select the most relevant data extraction
    step from the given extractor functions. If the query is broad or needs everything,
    return ['get_all']
    
    ### Data Extractors:
    {
        "get_flight_modes": "for questions about flight modes or mode changes",
        "get_events": "for armed/disarmed events or safety state.",
        "get_mission": "for waypoints, missions, or navigation.",
        "get_vehicle_type": "for the type of UAV.",
        "get_all": "when the question is broad or needs everything."
    }

    ### Input Format:
    Query: <query text>

    ### Output Format:
    {
        "extractors": [<list of data relevant data extractors>]
    }

    ### Input for your task:
    """

    routing_instruction_prompt = routing_instruction_prompt + f"\nQuery: {query}"

    return routing_instruction_prompt

    