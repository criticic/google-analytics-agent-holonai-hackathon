"""
Core agent definitions and node implementations.
"""

from typing import Annotated, TypedDict, Dict, Any, List, Optional
import logging
import json

# LangChain core components
from langchain_core.messages import HumanMessage, SystemMessage

# Import prompts and system configuration
from src.prompts import (
    SQL_GENERATOR_PROMPT,
    RESULTS_EXPLAINER_PROMPT,
    SQL_EXECUTOR_PROMPT,
    VISUALIZATION_PROMPT,
    CONVERSATION_ROUTER_PROMPT,
    SQL_REFLECTION_PROMPT,
)
from src.models.gemini import get_model
from src.tools.bigquery import execute_bigquery_sql

# Graph message handling
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph.message import add_messages
from langchain.agents import create_tool_calling_agent, AgentExecutor

# Set logging level
logger = logging.getLogger("analytics_agents")
logger.setLevel(logging.INFO)


# Define state schema for the analytics agent
class AnalysisState(TypedDict):
    """State definition for the analytics processing workflow."""

    question: str
    messages: Annotated[list, add_messages]
    sql_query: str
    query_results: Dict[str, Any]
    visualization_config: Dict[str, Any]
    chat_history: Optional[List[Dict[str, str]]]
    requires_analytics: bool  # New field to track if analytics is needed
    sql_feedback: Optional[str]  # Field to store feedback for SQL regeneration
    reflection_result: Optional[str]  # Field to store the SQL reflection decision
    general_response: Optional[str]  # Field to store general conversation response


# Initialize the model client
model = get_model()

#######################################
# Conversation Router Node
#######################################


def conversation_router_node(state: AnalysisState):
    """
    Node that determines whether a question requires analytics processing or general conversation.
    
    Args:
        state: The current state of the analytics workflow
        
    Returns:
        Updated state with routing decision and response if general conversation
    """
    # Format conversation history for context
    conversation_context = ""
    if state.get("chat_history"):
        chat_history = state["chat_history"][-3:]  # Use last 3 exchanges for context
        for exchange in chat_history:
            conversation_context += f"User: {exchange.get('question', '')}\n"
            if exchange.get('response', {}).get('explanation'):
                conversation_context += f"Assistant: {exchange.get('response', {}).get('explanation', '')}\n"
    
    # Add conversation context to the system message
    system_prompt = CONVERSATION_ROUTER_PROMPT
    if conversation_context:
        system_prompt += f"\n\nRecent conversation history for context:\n{conversation_context}"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["question"]),
    ]
    
    response = model.invoke(messages)
    response_content = response.content
    
    # Determine if this is an analytics query by looking for specific tags
    requires_analytics = "analytics_query: true" in response_content.lower()
    
    # Extract the general conversation response
    general_response = ""
    if not requires_analytics:
        # Clean up the response by removing the analytics_query tag if present
        general_response = response_content
        tag_index = general_response.lower().find("analytics_query: false")
        if tag_index > 0:
            general_response = general_response[:tag_index].strip()
    
    # Log both the routing decision and the response content
    logger.info(f"Routed query, requires_analytics: {requires_analytics} - {general_response[:100] if general_response else ''}")
    
    # Add the general response directly to the response message for the web UI to use
    result = {
        "messages": [response], 
        "requires_analytics": requires_analytics,
    }
    
    # Only add general_response for non-analytics queries
    if not requires_analytics and general_response:
        result["general_response"] = general_response
    
    return result


#######################################
# SQL Generator Node
#######################################


def sql_generator_node(state: AnalysisState):
    """
    Node that converts a natural language question into a BigQuery SQL query.

    Args:
        state: The current state of the analytics workflow

    Returns:
        Updated state with SQL query and messages
    """
    # Format conversation history for context
    conversation_context = ""
    if state.get("chat_history"):
        chat_history = state["chat_history"][-3:]  # Use last 3 exchanges for context
        for exchange in chat_history:
            conversation_context += f"User: {exchange.get('question', '')}\n"
            if exchange.get('response', {}).get('explanation'):
                conversation_context += f"Assistant: {exchange.get('response', {}).get('explanation', '')}\n"
    
    # Add conversation context to the system message
    system_prompt = SQL_GENERATOR_PROMPT
    if conversation_context:
        system_prompt += f"\n\nRecent conversation history for context:\n{conversation_context}"
    
    # Determine if we should include SQL feedback from a prior reflection
    user_content = f"Convert this question into a BigQuery SQL query: {state['question']}"
    
    # If we have feedback from a previous SQL execution, include it
    if state.get("sql_feedback"):
        user_content += f"\n\nImportant feedback from previous SQL execution to incorporate:\n{state['sql_feedback']}"
        
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = model.invoke(messages)

    return {"messages": [response], "sql_query": response.content, "sql_feedback": None}


#######################################
# SQL Executor Node
#######################################


def sql_executor_node(state: AnalysisState):
    """
    Node that executes a SQL query against BigQuery.

    Args:
        state: The current state of the analytics workflow

    Returns:
        Updated state with query results and messages
    """
    # Prepare the SQL query for execution
    sql_query = state["sql_query"]
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SQL_EXECUTOR_PROMPT),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    tool_calling_model = model.bind_tools([execute_bigquery_sql])
    agent = create_tool_calling_agent(
        tool_calling_model, [execute_bigquery_sql], prompt=prompt
    )
    agent_executor = AgentExecutor(
        agent=agent, tools=[execute_bigquery_sql], verbose=False
    )
    response = agent_executor.invoke({"input": sql_query})
    result_message = SystemMessage(content=str(response.get("output", str(response))))

    # Extract results from the tool response
    return {"messages": [result_message], "query_results": response}


#######################################
# SQL Reflection Node
#######################################


def sql_reflection_node(state: AnalysisState):
    """
    Node that evaluates SQL execution results to determine if they're valid and useful.
    
    Args:
        state: The current state of the analytics workflow
        
    Returns:
        Updated state with reflection results and decision to proceed or retry
    """
    # Get the original question, SQL query, and query results
    question = state["question"]
    sql_query = state["sql_query"]
    query_results = state["query_results"]
    
    # Format the query results for easier analysis
    formatted_results = str(query_results)
    if isinstance(query_results, dict) and "results" in query_results:
        if isinstance(query_results["results"], list):
            # Include number of results and sample of data
            result_count = len(query_results["results"])
            sample = query_results["results"][:5] if result_count > 0 else []
            formatted_results = f"Total results: {result_count}\nSample: {sample}"
    
    # Create the reflection prompt
    messages = [
        SystemMessage(content=SQL_REFLECTION_PROMPT),
        HumanMessage(
            content=f"""
            Original question: {question}
            
            SQL query executed:
            {sql_query}
            
            Execution results:
            {formatted_results}
            
            Did these results properly answer the question?
            """
        ),
    ]
    
    # Get the reflection response
    response = model.invoke(messages)
    reflection_content = response.content
    
    logger.info(f"SQL reflection: {reflection_content[:100]}...")
    
    # Determine if we should proceed or retry based on the reflection
    should_proceed = reflection_content.upper().startswith("DECISION: PASS")
    reflection_result = "PASS" if should_proceed else "RETRY"
    
    # Extract feedback for SQL regeneration if needed
    sql_feedback = None
    if not should_proceed:
        # Extract the feedback part (after "DECISION: RETRY")
        decision_marker = "DECISION: RETRY"
        if decision_marker in reflection_content:
            sql_feedback = reflection_content[reflection_content.find(decision_marker) + len(decision_marker):].strip()
        else:
            sql_feedback = reflection_content
    
    # Log both the reflection result and feedback for debugging
    logger.info(f"SQL reflection decision: {reflection_result}")
    if sql_feedback:
        logger.info(f"SQL feedback for retry: {sql_feedback[:100]}...")
    
    # Return decision and feedback
    return {
        "messages": [response],
        "reflection_result": reflection_result,
        "sql_feedback": sql_feedback
    }


#######################################
# Results Explainer Node
#######################################


def results_explainer_node(state: AnalysisState):
    """
    Node that explains the query results in natural language.

    Args:
        state: The current state of the analytics workflow

    Returns:
        Updated state with explanation messages
    """
    # Format conversation history for context
    conversation_context = ""
    if state.get("chat_history"):
        chat_history = state["chat_history"][-3:]  # Use last 3 exchanges for context
        for exchange in chat_history:
            conversation_context += f"User: {exchange.get('question', '')}\n"
            if exchange.get('response', {}).get('explanation'):
                conversation_context += f"Assistant: {exchange.get('response', {}).get('explanation', '')}\n"
    
    # Add conversation context to the system message
    system_prompt = RESULTS_EXPLAINER_PROMPT
    if conversation_context:
        system_prompt += f"\n\nRecent conversation history for context:\n{conversation_context}"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=f"""
        Original Question: {state["question"]}
        
        SQL Query Used:
        {state["sql_query"]}
        
        Query Results:
        {state["query_results"]}
        
        Please provide a comprehensive analysis of these results. If the query results is empty, has errors, or does not answer the query.
        """
        ),
    ]
    response = model.invoke(messages)
    return {"messages": [response]}


#######################################
# Visualization Generator Node
#######################################


def visualization_generator_node(state: AnalysisState):
    """
    Node that generates visualization configurations based on query results.

    Args:
        state: The current state of the analytics workflow

    Returns:
        Updated state with visualization configuration
    """
    # Get query results - these will be used as data for visualization
    query_results = state.get("query_results", {})

    # Extract data from query results using a simple approach
    data = []

    # Check common BigQuery result paths
    if isinstance(query_results, dict):
        if "results" in query_results and isinstance(query_results["results"], list):
            data = query_results["results"]
        elif "output" in query_results and isinstance(query_results["output"], str):
            # Try to extract JSON data from output if it's in markdown format
            content = query_results["output"]
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                if json_end > json_start:
                    try:
                        json_str = content[json_start:json_end].strip()
                        parsed_data = json.loads(json_str)
                        if isinstance(parsed_data, list):
                            data = parsed_data
                    except json.JSONDecodeError:
                        pass
            # Try to parse markdown table if present
            elif "|" in content:
                table_lines = [
                    line for line in content.split("\n") if line.strip().startswith("|")
                ]
                if len(table_lines) > 2:
                    try:
                        headers = [h.strip() for h in table_lines[0].split("|")[1:-1]]
                        parsed_data = []
                        for line in table_lines[2:]:
                            if "|" in line:
                                values = [v.strip() for v in line.split("|")[1:-1]]
                                if len(values) == len(headers):
                                    parsed_data.append(dict(zip(headers, values)))
                        if parsed_data:
                            data = parsed_data
                    except Exception:
                        pass

    # If we still don't have data, try other approaches
    if not data:
        for key, value in query_results.items():
            if isinstance(value, list) and len(value) > 0:
                data = value
                break

    # If we still don't have data, create a simple representation
    if not data:
        data = [{"message": "No structured data available"}]

    sample_data = str(data[:10]) if data and len(data) > 0 else "[]"
    column_info = list(data[0].keys()) if data and isinstance(data[0], dict) else []

    # Ask the model to generate a visualization config
    messages = [
        SystemMessage(content=VISUALIZATION_PROMPT),
        HumanMessage(
            content=f"""
        Original Question: {state["question"]}
        
        SQL Query Used:
        {state["sql_query"]}
        
        Available columns: {column_info}
        
        Sample data:
        {sample_data}
        
        Please generate an appropriate visualization configuration based on this data.
        """
        ),
    ]

    response = model.invoke(messages)

    # Try to extract the JSON configuration from the response
    visualization_config = {}
    try:
        # Look for JSON content between triple backticks
        content = response.content
        json_start = (
            content.find("```json") + 7
            if "```json" in content
            else content.find("```") + 3
        )
        json_end = content.rfind("```")

        if json_start > 3 and json_end > json_start:
            json_str = content[json_start:json_end].strip()
            visualization_config = json.loads(json_str)
        else:
            # Attempt to parse the entire content as JSON
            visualization_config = json.loads(content)

    except (json.JSONDecodeError, ValueError) as e:
        # If JSON parsing fails, create a simple error config
        visualization_config = {
            "chart_type": "table",
            "title": "Data Visualization (Error in configuration)",
            "error": f"Could not generate valid visualization: {str(e)}",
        }

    # Add the data directly to the visualization config
    visualization_config["data"] = data

    return {"messages": [response], "visualization_config": visualization_config}
