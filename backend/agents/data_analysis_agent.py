import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI
import os
from dotenv import load_dotenv
from tools.flight_data_db import FlightDataDB
import pandas as pd
from models import Message, FlightData, AgentResponse
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logging.getLogger("openai").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class DataExtractionAgent:
    def __init__(self):
        self.system_prompt = """You are a data extraction expert for UAV flight data analysis. Your role is to generate SQL queries that extract relevant data for analysis.
        
        Guidelines:
        1. Generate SELECT queries that extract all relevant columns needed for analysis
        2. Include appropriate JOINs when data is spread across multiple tables
        3. Consider time-based analysis and include timestamp columns
        4. Include all columns that might be needed for:
        - Clustering analysis
        - Time series analysis
        - Statistical analysis
        - Pattern recognition
        5. Order results by timestamp when relevant
        6. Use table aliases for clarity
        7. Include appropriate WHERE clauses to filter data if needed
        
        Example queries:
        
        For attitude analysis:
        SELECT a.time_boot_ms, a.roll, a.pitch, a.yaw, a.rollspeed, a.pitchspeed, a.yawspeed
        FROM ATTITUDE a
        ORDER BY a.time_boot_ms;
        
        For position and velocity analysis:
        SELECT p.time_boot_ms, p.lat, p.lng, p.alt, v.vx, v.vy, v.vz
        FROM GLOBAL_POSITION_INT p
        JOIN VELOCITY v ON p.time_boot_ms = v.time_boot_ms
        ORDER BY p.time_boot_ms;
        """

    def _validate_query(self, query: str) -> bool:
        """Validate that the query is safe to execute (read-only)."""
        logger.debug(f"Starting query validation for: {query}")
        query = query.lower().strip()
        forbidden_keywords = ['insert', 'update', 'delete', 'drop', 'alter', 'create', 'truncate']
        
        # Log each forbidden keyword check
        for keyword in forbidden_keywords:
            if keyword in query:
                logger.warning(f"Query validation failed: Found forbidden keyword '{keyword}'")
                return False
        
        logger.debug("Query validation passed: No forbidden keywords found")
        return True

    def _extract_sql_query(self, query: str) -> str:
        """Extract the SQL query from the generated query."""
        logger.debug(f"Extracting SQL query from: {query}")
        if "```sql" in query:
            return query.split("```sql")[1].split("```")[0].strip()
        else:
            return ""

    def _generate_sql_query(self, question: str, schema: Dict[str, Any], conversation_history: List[Message]) -> str:
        """Generates a SQL query based on the user's question and the schema."""
        messages: List[ChatCompletionMessageParam] = [
                ChatCompletionSystemMessageParam(role="system", content=self.system_prompt),
                ChatCompletionSystemMessageParam(role="system", content=f"Available tables and their schemas:\n{schema}"),
                *[msg.to_openai_message() for msg in conversation_history],
                ChatCompletionUserMessageParam(role="user", content=f"Generate a SQL query to extract data for analysis based on this request: {question}")
            ]
            
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            max_tokens=1024
        )
        generated_sql_query = response.choices[0].message.content
        if generated_sql_query is None:
            raise Exception("No content received from OpenAI API")
        generated_sql_query = generated_sql_query.strip()
        sql_query = self._extract_sql_query(generated_sql_query)
        return sql_query

    # TODO: Move DataExtractionAgent upwards in the agent hierarchy to be the first agent to be called 
    def extract_data(self,query: str, flight_db: FlightDataDB, session_id: str, conversation_history: List[Message]):

        """Extracts relevant data from the database for analysis based on the user's query.
        
        Args:
            query (str): The user's query describing what data they want to analyze
            flight_db (FlightDataDB): The FlightDataDB instance to query
            session_id (str): The session ID to use for database access
            
        Returns:
            pd.DataFrame: A DataFrame containing the extracted data ready for analysis
        """
        
        try:
            # Get database schema
            db_schema = flight_db.get_database_information(session_id)
            logger.info(f"Extracting data")

            # Generate SQL query
            sql_query = self._generate_sql_query(query, db_schema, conversation_history)
            
            # Validate query with retries
            RETRY_LIMIT = 3
            retry_count = 0
            while not self._validate_query(sql_query):
                logger.warning(f"Invalid query generated (attempt {retry_count + 1}/{RETRY_LIMIT}): {sql_query}")
                conversation_history.append(Message(role="assistant", content=f"Error: Generated query contains forbidden operations. Only SELECT queries are allowed. Please try again."))
                sql_query = self._generate_sql_query(query, db_schema, conversation_history)
                retry_count += 1
                if retry_count >= RETRY_LIMIT:
                    logger.error("Failed to generate valid query after maximum retries")
                    raise Exception("Failed to generate valid query after maximum retries")

            # Execute query and return DataFrame
            result_df = flight_db.query(session_id, sql_query)
            return (result_df, sql_query)
            
        except Exception as e:
            logger.error(f"Error in DataExtractionAgent: {str(e)}")
            raise Exception(f"Failed to extract data: {str(e)}")

class CodeGenerationAgent:
    def _extract_first_code_block(self, text: str) -> str:
        """Extracts the first Python code block from a markdown-formatted string."""
        start = text.find("```python")
        if start == -1:
            return ""
        start += len("```python")
        end = text.find("```", start)
        if end == -1:
            return ""
        
        logger.info(f"Extracted code: {text[start:end].strip()}")
        return text[start:end].strip()

    def generate_code(self, query: str, df: pd.DataFrame):
        """Uses the code generation tool and gets code from the LLM for the user's query."""
        cols = df.columns.tolist()
        
        prompt = f"""
        Given DataFrame `df` with columns: {', '.join(cols)}
        Write Python code (scikit-learn **only**, no plotting) to answer:
        "{query}"

        Rules
        -----
        1. Use scikit-learn operations on `df` only.
        2. Assign the final result to `result`.
        3. Wrap the snippet in a single ```python code fence (no extra prose).
        """

        messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content="You are a Python data-analysis expert who writes clean, efficient code. Solve the given problem with optimal scikit-learn operations. Be concise and focused. Your response must contain ONLY a properly-closed ```python code block with no explanations before or after. Ensure your solution is correct, handles edge cases, and follows best practices for data analysis."),
            ChatCompletionUserMessageParam(role="user", content=prompt)
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            max_tokens=1024
        )

        full_response = response.choices[0].message.content
        if full_response is None:
            raise Exception("No content received from OpenAI API")
        code = self._extract_first_code_block(full_response)
        return code, ""
        
    def execute_code(self, code: str, df: pd.DataFrame):
        """Executes the generated code in a controlled environment and returns the result or error message."""
        import numpy as np
        import pandas as pd
        import sklearn
        
        env = {
            "pd": pd,
            "np": np,
            "df": df,
            "sklearn": sklearn
        }
        try:
            exec(code, {}, env)
            return env.get("result", None)
        except Exception as exc:
            return f"Error executing code: {exc}"

class ReasoningAgent:
    def _reasoning_prompt(self, query: str, result: Any, code: str = "", sql_query: str = "") -> str:
        """Builds and returns the LLM prompt for reasoning about the result."""
        is_error = isinstance(result, str) and result.startswith("Error executing code")

        if is_error:
            desc = result
        else:
            desc = str(result)[:300]

        prompt = f'''
        You are a flight data analysis expert. The following analysis was performed on UAV flight data:

        1. First, this SQL query was generated and executed to extract relevant data:
        ```sql
        {sql_query}
        ```

        2. Then, this Python code was generated and executed on the resulting dataframe:
        ```python
        {code}
        ```

        3. The user's original question was: "{query}"

        4. The analysis result is: {desc}

        Follow the following guidelines:

        1. As a flight data analysis expert, explain in 2-3 concise sentences what this analysis reveals about the UAV's flight characteristics, performance, or behavior. 
        
        2. Focus on specific insights and highlight appropriate data points. 
        
        3. Do not make general statements.

        4. Do not make any assumptions about the data.

        5. Do not mention the SQL query or the code or the code output format in your response.
        
        '''
        return prompt

    def reasoning(self, query: str, result: Any, code: str = "", sql_query: str = ""):
        """Returns the LLM's reasoning about the result (plot or value)."""
        prompt = self._reasoning_prompt(query, result, code, sql_query)
        is_error = isinstance(result, str) and result.startswith("Error executing code")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                ChatCompletionSystemMessageParam(role="system", content="You are an expert UAV flight data analyst with deep knowledge of flight dynamics, performance metrics, and operational insights."),
                ChatCompletionUserMessageParam(role="user", content=prompt)
            ],
            temperature=0.4,
            max_tokens=1024
        )

        response_content = response.choices[0].message.content
        if response_content is None:
            raise Exception("No content received from OpenAI API")
        return response_content.strip()

class DataAnalysisAgent:
    def __init__(self):
        self.data_extraction_agent = DataExtractionAgent()
        self.code_generation_agent = CodeGenerationAgent()
        self.reasoning_agent = ReasoningAgent()

    def analyze(self, query: str, flight_db: FlightDataDB, session_id: str, conversation_history: List[Message]):
        """Analyzes the data and returns the result."""
        df, sql_query = self.data_extraction_agent.extract_data(query, flight_db, session_id, conversation_history)
        code, _ = self.code_generation_agent.generate_code(query, df)
        result = self.code_generation_agent.execute_code(code, df)

        response = self.reasoning_agent.reasoning(query, result, code, sql_query)
        logger.info(f"Data Analysis Agent returns the following response:\n\n {response}")
        return response
