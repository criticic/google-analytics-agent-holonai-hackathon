"""
LangGraph workflow definition for the Google Analytics - Business Intelligence - Agent.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any, AsyncIterator, TypedDict, List, Union, Optional, Callable
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import logging

from src.core.agents import (
    AnalysisState,
    sql_generator_node,
    sql_executor_node,
    results_explainer_node,
    visualization_generator_node,
    conversation_router_node,
    sql_reflection_node,
)

memory = MemorySaver()

logger = logging.getLogger("gabi.core.graph")


def create_analytics_graph():
    """
    Create and return the LangGraph workflow for BigQuery analytics.

    Returns:
        A compiled LangGraph workflow
    """
    workflow = StateGraph(AnalysisState)

    workflow.add_node("conversation_router", conversation_router_node)
    workflow.add_node("sql_generator", sql_generator_node)
    workflow.add_node("sql_executor", sql_executor_node)
    workflow.add_node("sql_reflection", sql_reflection_node)
    workflow.add_node("visualization_generator", visualization_generator_node)
    workflow.add_node("results_explainer", results_explainer_node)

    workflow.add_edge(START, "conversation_router")
    
    def route_query(state: AnalysisState) -> str:
        """Determine where to route the query based on whether it requires analytics."""
        requires_analytics = state.get("requires_analytics", False)
        
        if not requires_analytics:
            router_messages = state.get("messages", [])
            if router_messages and hasattr(router_messages[-1], 'content'):
                content = router_messages[-1].content
                tag_index = content.lower().find("analytics_query: false")
                if tag_index > 0:
                    general_response = content[:tag_index].strip()
                else:
                    general_response = content.strip()
                
                state["general_response"] = general_response
                logger.info(f"General response extracted: {general_response[:50]}...")
        
        logger.info(f"Routing query, requires_analytics: {requires_analytics}")
        return "sql_generator" if requires_analytics else END
        
    workflow.add_conditional_edges(
        "conversation_router",
        route_query,
        {
            "sql_generator": "sql_generator",
            END: END,
        }
    )
    
    workflow.add_edge("sql_generator", "sql_executor")
    workflow.add_edge("sql_executor", "sql_reflection")
    
    def route_sql_results(state: AnalysisState) -> str:
        """Determine whether to proceed with results or retry SQL generation."""
        reflection_result = state.get("reflection_result", "PASS")
        
        logger.info(f"SQL Reflection decision: {reflection_result}")
        
        if reflection_result == "RETRY":
            feedback = state.get("sql_feedback", "Results were not satisfactory")
            logger.info(f"SQL feedback for retry: {feedback[:100]}...")
            return "sql_generator"
        else:
            logger.info("SQL reflection passed, proceeding with results processing")
            return "visualization_generator"
    
    workflow.add_conditional_edges(
        "sql_reflection",
        route_sql_results,
        {
            "sql_generator": "sql_generator",
            "visualization_generator": "visualization_generator",
        }
    )
    
    workflow.add_edge("visualization_generator", "results_explainer")
    workflow.add_edge("results_explainer", END)

    graph = workflow.compile(checkpointer=memory)
    logger.info("Analytics graph compiled successfully")

    return graph


def run_analytics_query(question: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Run the complete analytics pipeline on the given question.

    Args:
        question: The user's natural language question about Google Analytics data
        chat_history: Optional list of previous chat messages for context

    Returns:
        The final analysis and insights
    """
    thread_id = "analytics-" + str(hash(question))[:8]
    thread_config = {"configurable": {"thread_id": thread_id}}

    logger.info(f"Creating analytics graph for query: '{question[:50]}...'")
    graph = create_analytics_graph()

    logger.debug(f"Graph structure: {graph.get_graph().draw_mermaid()}")

    initial_state = {
        "question": question,
        "messages": [],
        "sql_query": "",
        "query_results": {},
        "visualization_config": {},
        "chat_history": chat_history or [],
        "requires_analytics": False,
        "general_response": "",
        "sql_feedback": None,
        "reflection_result": None
    }

    logger.info("Executing analytics graph workflow")
    result = graph.invoke(initial_state, thread_config)
    logger.info("Analytics graph workflow completed")

    if not result.get("requires_analytics", False):
        logger.info("Query was handled as general conversation")
        return result.get("general_response", "I'm not sure how to respond to that.")
        
    final_messages = result["messages"]
    if final_messages:
        logger.info("Analytics query completed successfully with results")
        return final_messages[-1].content
    else:
        logger.warning("No results were generated for analytics query")
        return "No results were generated."


class StreamEvent(TypedDict):
    """Event type for streaming analytics updates."""
    type: str
    data: Any
    node: Optional[str]
    message: Optional[BaseMessage]


async def stream_analytics_query(
    question: str,
    stream_handler: Optional[Callable[[StreamEvent], None]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream the execution of the analytics pipeline, yielding intermediate results.

    Args:
        question: The user's natural language question about Google Analytics data
        stream_handler: Optional callback function to handle stream events
        chat_history: Optional list of previous chat messages for context

    Yields:
        Streaming updates from the analytics pipeline
    """
    thread_id = "analytics-stream-" + str(hash(question))[:8]
    thread_config = {"configurable": {"thread_id": thread_id}}

    logger.info(f"Creating streaming analytics graph for query: '{question[:50]}...'")
    graph = create_analytics_graph()

    logger.debug(f"Graph structure: {graph.get_graph().draw_mermaid()}")

    initial_state = {
        "question": question,
        "messages": [],
        "sql_query": "",
        "query_results": {},
        "visualization_config": {},
        "chat_history": chat_history or [],
        "requires_analytics": False,
        "general_response": "",
        "sql_feedback": None,
        "reflection_result": None
    }

    logger.info("Beginning streaming analytics workflow execution")
    event_count = 0
    async for event in graph.astream(initial_state, thread_config, stream_mode="updates"):
        event_count += 1
        event_data = {
            "type": "update",
            "data": event,
            "node": list(event.keys())[0] if event else None,
        }

        if stream_handler:
            node_name = event_data.get("node", "unknown")
            logger.debug(f"Streaming event from {node_name} node")
            stream_handler(event_data)
        
        yield event_data
    
    logger.info(f"Streaming workflow completed with {event_count} events processed")
