
def get_final_answer_prompt(context_data, user_query):
    context_str = str(context_data)

    final_answer_instruction_prompt = """
    ### Task:
    Given a user query and the necessary data, return the final answer to the query,
    using just the data provided. If data is insufficient to answer the query, return
    a string "MORE DATA NEEDED".

    ### Input Format:
    Query - <query text>
    Data - <Necessary context data>

    ### Output Format:
    {
        "answer": <answer text>
    }

    ### Input for your task:
    """

    final_answer_instruction_prompt = final_answer_instruction_prompt + f"\nQuery: {user_query}\nData: {context_str}"

    return final_answer_instruction_prompt
