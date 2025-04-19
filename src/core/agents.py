"""
Core agent definitions and node implementations.
"""

from typing import Annotated, TypedDict, Dict, Any, List, Optional
import logging
import json

from langchain_core.messages import HumanMessage, SystemMessage

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

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph.message import add_messages
from langchain.agents import create_tool_calling_agent, AgentExecutor

logger = logging.getLogger("gabi.core.agents")

class AnalysisState(TypedDict):
    """State definition for the analytics processing workflow."""

    question: str
    messages: Annotated[list, add_messages]
    sql_query: str
    query_results: Dict[str, Any]
    visualization_config: Dict[str, Any]
    chat_history: Optional[List[Dict[str, str]]]
    requires_analytics: bool
    sql_feedback: Optional[str]
    reflection_result: Optional[str]
    general_response: Optional[str]


model = get_model()


def conversation_router_node(state: AnalysisState):
    """
    Node that determines whether a question requires analytics processing or general conversation.
    
    Args:
        state: The current state of the analytics workflow
        
    Returns:
        Updated state with routing decision and response if general conversation
    """
    conversation_context = ""
    if state.get("chat_history"):
        chat_history = state["chat_history"][-3:]
        for exchange in chat_history:
            conversation_context += f"User: {exchange.get('question', '')}\n"
            if exchange.get('response', {}).get('explanation'):
                conversation_context += f"Assistant: {exchange.get('response', {}).get('explanation', '')}\n"
    
    system_prompt = CONVERSATION_ROUTER_PROMPT
    if conversation_context:
        system_prompt += f"\n\nRecent conversation history for context:\n{conversation_context}"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["question"]),
    ]
    
    response = model.invoke(messages)
    response_content = response.content
    
    requires_analytics = "analytics_query: true" in response_content.lower()
    
    general_response = ""
    if not requires_analytics:
        general_response = response_content
        tag_index = general_response.lower().find("analytics_query: false")
        if tag_index > 0:
            general_response = general_response[:tag_index].strip()
    
    logger.info(f"Routed query, requires_analytics: {requires_analytics} - {general_response[:100] if general_response else ''}")
    
    result = {
        "messages": [response], 
        "requires_analytics": requires_analytics,
    }
    
    if not requires_analytics and general_response:
        result["general_response"] = general_response
    
    return result


def sql_generator_node(state: AnalysisState):
    """
    Node that converts a natural language question into a BigQuery SQL query.

    Args:
        state: The current state of the analytics workflow

    Returns:
        Updated state with SQL query and messages
    """
    conversation_context = ""
    if state.get("chat_history"):
        chat_history = state["chat_history"][-3:]
        for exchange in chat_history:
            conversation_context += f"User: {exchange.get('question', '')}\n"
            if exchange.get('response', {}).get('explanation'):
                conversation_context += f"Assistant: {exchange.get('response', {}).get('explanation', '')}\n"
    
    system_prompt = SQL_GENERATOR_PROMPT
    if conversation_context:
        system_prompt += f"\n\nRecent conversation history for context:\n{conversation_context}"
    
    user_content = f"Convert this question into a BigQuery SQL query: {state['question']}"
    
    if state.get("sql_feedback"):
        user_content += f"\n\nImportant feedback from previous SQL execution to incorporate:\n{state['sql_feedback']}"
        
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = model.invoke(messages)

    return {"messages": [response], "sql_query": response.content, "sql_feedback": None}


def sql_executor_node(state: AnalysisState):
    """
    Node that executes a SQL query against BigQuery.

    Args:
        state: The current state of the analytics workflow

    Returns:
        Updated state with query results and messages
    """
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

    return {"messages": [result_message], "query_results": response}


def sql_reflection_node(state: AnalysisState):
    """
    Node that evaluates SQL execution results to determine if they're valid and useful.
    
    Args:
        state: The current state of the analytics workflow
        
    Returns:
        Updated state with reflection results and decision to proceed or retry
    """
    question = state["question"]
    sql_query = state["sql_query"]
    query_results = state["query_results"]
    
    formatted_results = str(query_results)
    if isinstance(query_results, dict) and "results" in query_results:
        if isinstance(query_results["results"], list):
            result_count = len(query_results["results"])
            sample = query_results["results"][:5] if result_count > 0 else []
            formatted_results = f"Total results: {result_count}\nSample: {sample}"
    
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
    
    response = model.invoke(messages)
    reflection_content = response.content
    
    logger.info(f"SQL reflection: {reflection_content[:100]}...")
    
    should_proceed = reflection_content.upper().startswith("DECISION: PASS")
    reflection_result = "PASS" if should_proceed else "RETRY"
    
    sql_feedback = None
    if not should_proceed:
        decision_marker = "DECISION: RETRY"
        if decision_marker in reflection_content:
            sql_feedback = reflection_content[reflection_content.find(decision_marker) + len(decision_marker):].strip()
        else:
            sql_feedback = reflection_content
    
    logger.info(f"SQL reflection decision: {reflection_result}")
    if sql_feedback:
        logger.info(f"SQL feedback for retry: {sql_feedback[:100]}...")
    
    return {
        "messages": [response],
        "reflection_result": reflection_result,
        "sql_feedback": sql_feedback
    }


def results_explainer_node(state: AnalysisState):
    """
    Node that explains the query results in natural language.

    Args:
        state: The current state of the analytics workflow

    Returns:
        Updated state with explanation messages
    """
    conversation_context = ""
    if state.get("chat_history"):
        chat_history = state["chat_history"][-3:]
        for exchange in chat_history:
            conversation_context += f"User: {exchange.get('question', '')}\n"
            if exchange.get('response', {}).get('explanation'):
                conversation_context += f"Assistant: {exchange.get('response', {}).get('explanation', '')}\n"
    
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


def visualization_generator_node(state: AnalysisState):
    """
    Node that generates visualization configurations based on query results.

    Args:
        state: The current state of the analytics workflow

    Returns:
        Updated state with visualization configuration
    """
    query_results = state.get("query_results", {})
    data = []

    if isinstance(query_results, dict):
        if "results" in query_results and isinstance(query_results["results"], list):
            data = query_results["results"]
        elif "output" in query_results and isinstance(query_results["output"], str):
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

    if not data:
        for key, value in query_results.items():
            if isinstance(value, list) and len(value) > 0:
                data = value
                break

    if not data:
        data = [{"message": "No structured data available"}]

    sample_data = str(data[:10]) if data and len(data) > 0 else "[]"
    column_info = list(data[0].keys()) if data and isinstance(data[0], dict) else []

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

    visualization_config = {}
    try:
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
            visualization_config = json.loads(content)

    except (json.JSONDecodeError, ValueError) as e:
        visualization_config = {
            "chart_type": "table",
            "title": "Data Visualization (Error in configuration)",
            "error": f"Could not generate valid visualization: {str(e)}",
        }

    visualization_config["data"] = data

    return {"messages": [response], "visualization_config": visualization_config}
