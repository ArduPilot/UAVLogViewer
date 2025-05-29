
def get_final_answer_prompt(context_data, user_query):
    context_str = str(context_data)

    final_answer_instruction_prompt = """
    ### Task:
    Given a user query and the necessary data, return the final answer to the query,
    using just the data provided.

    ### Guidelines:
    - Give detailed and clear answers, in an easy-to-understand way.
    - Avoid using technical jargons unless absolutely necessary for explanation.
    - Answer questions about timestamps in minutes if the timestamps is larger than 60 seconds.
    - Explain the implications of numerical data in the answer. Summarize what the numerical information means / technical jargons mean. 
    - If data is insufficient to answer the query, return as answer "INSUFFICIENT DATA"

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
