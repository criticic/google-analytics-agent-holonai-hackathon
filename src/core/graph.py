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

# Initialize agent memory
memory = MemorySaver()

# Configure logging
logger = logging.getLogger("analytics_graph")


def create_analytics_graph():
    """
    Create and return the LangGraph workflow for BigQuery analytics.

    Returns:
        A compiled LangGraph workflow
    """
    # Create the basic graph structure
    workflow = StateGraph(AnalysisState)

    # Add nodes to the workflow
    workflow.add_node("conversation_router", conversation_router_node)
    workflow.add_node("sql_generator", sql_generator_node)
    workflow.add_node("sql_executor", sql_executor_node)
    workflow.add_node("sql_reflection", sql_reflection_node)
    workflow.add_node("visualization_generator", visualization_generator_node)
    workflow.add_node("results_explainer", results_explainer_node)

    # Define the flow of execution with the router at the start
    workflow.add_edge(START, "conversation_router")
    
    # Define conditional branching from the router
    def route_query(state: AnalysisState) -> str:
        """Determine where to route the query based on whether it requires analytics."""
        requires_analytics = state.get("requires_analytics", False)
        
        # Check if we have a general response for non-analytics queries
        if not requires_analytics:
            # Try to extract general response from router node response
            router_messages = state.get("messages", [])
            if router_messages and hasattr(router_messages[-1], 'content'):
                content = router_messages[-1].content
                # Clean up the response by removing the analytics_query tag if present
                tag_index = content.lower().find("analytics_query: false")
                if tag_index > 0:
                    general_response = content[:tag_index].strip()
                else:
                    general_response = content.strip()
                
                # Add the general response to the state for the UI to pick up
                state["general_response"] = general_response
                logger.info(f"General response extracted: {general_response[:50]}...")
        
        logger.info(f"Routing query, requires_analytics: {requires_analytics}")
        return "sql_generator" if requires_analytics else END
        
    # Add conditional edge from router
    workflow.add_conditional_edges(
        "conversation_router",
        route_query,
        {
            "sql_generator": "sql_generator",  # Route to SQL generator for analytics queries
            END: END,  # End the workflow for general conversation
        }
    )
    
    # Standard analytics pipeline with SQL, then execution
    workflow.add_edge("sql_generator", "sql_executor")
    
    # Add SQL reflection node after execution
    workflow.add_edge("sql_executor", "sql_reflection")
    
    # Define conditional routing based on SQL reflection results
    def route_sql_results(state: AnalysisState) -> str:
        """Determine whether to proceed with results or retry SQL generation."""
        reflection_result = state.get("reflection_result", "PASS")
        
        # Ensure reflection_result is properly set in the state for handlers to access
        logger.info(f"SQL Reflection decision: {reflection_result}")
        
        if reflection_result == "RETRY":
            # Log the feedback that will be provided to SQL generator
            feedback = state.get("sql_feedback", "Results were not satisfactory")
            logger.info(f"SQL feedback for retry: {feedback[:100]}...")
            return "sql_generator"
        else:
            # Proceed with visualization and explanation
            logger.info("SQL reflection passed, proceeding with results processing")
            return "visualization_generator"
    
    # Add conditional edges from SQL reflection
    workflow.add_conditional_edges(
        "sql_reflection",
        route_sql_results,
        {
            "sql_generator": "sql_generator",  # Route back to SQL generator for retry
            "visualization_generator": "visualization_generator",  # Continue to visualization
        }
    )
    
    # Continue with visualization and results explanation
    workflow.add_edge("visualization_generator", "results_explainer")
    workflow.add_edge("results_explainer", END)

    # Compile the LangGraph workflow, enabling memory-based state management
    graph = workflow.compile(checkpointer=memory)
    logger.info("Analytics graph compiled successfully.")
    graph.get_graph().draw_mermaid_png(output_file_path="analytics_graph.png")
    logger.info("Analytics graph diagram saved as analytics_graph.png")

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
    # Create a LangGraph thread with a unique ID for state management
    thread_id = "analytics-" + str(hash(question))[:8]
    thread_config = {"configurable": {"thread_id": thread_id}}

    # Get the compiled graph
    graph = create_analytics_graph()

    # Initialize the state with the user's question
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

    # Execute the workflow
    result = graph.invoke(initial_state, thread_config)

    # Check if this was a general conversation or analytics query
    if not result.get("requires_analytics", False):
        return result.get("general_response", "I'm not sure how to respond to that.")
        
    # For analytics queries, return the final explanation
    final_messages = result["messages"]
    if final_messages:
        return final_messages[-1].content
    else:
        return "No results were generated."


# Streaming graph support
class StreamEvent(TypedDict):
    """Event type for streaming analytics updates."""
    type: str  # Type of event (node_start, node_end, message_chunk, etc.)
    data: Any  # Data associated with this event
    node: Optional[str]  # Node that generated this event
    message: Optional[BaseMessage]  # Message content if applicable


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
    # Create a LangGraph thread with a unique ID for state management
    thread_id = "analytics-stream-" + str(hash(question))[:8]
    thread_config = {"configurable": {"thread_id": thread_id}}

    # Get the compiled streaming graph
    graph = create_analytics_graph()

    # Initialize the state with the user's question
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

    # Stream each step of the workflow execution
    async for event in graph.astream(initial_state, thread_config, stream_mode="updates"):
        # Process each event in the stream
        event_data = {
            "type": "update",
            "data": event,
            "node": list(event.keys())[0] if event else None,
        }

        # Send event to handler if provided
        if stream_handler:
            stream_handler(event_data)
        
        # Also yield the event for async consumption
        yield event_data
