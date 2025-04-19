"""
Event handlers for the Google Analytics - Business Intelligence - Agent web interface.
"""
import asyncio
import streamlit as st
import logging
from datetime import datetime
from src.core.graph import stream_analytics_query, StreamEvent
from src.web.state import reset_current_response
from src.web.components.chat import create_chat_message_placeholders

# Configure logging
logger = st.logger.get_logger(__name__)

def handle_new_query(query):
    """
    Handle a new query from the user.
    
    Args:
        query: The user's natural language question
    """
    if query and not st.session_state.is_processing:
        logger.info(f"New query received: '{query}'")
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(query)
        
        # Create placeholder for assistant's response
        create_chat_message_placeholders()
        
        # Process the query asynchronously
        asyncio.run(process_query_async(query))


def handle_stream_event(event: StreamEvent):
    """
    Handle stream events from the analytics graph and update UI in real-time.
    
    Args:
        event: Dictionary with event information from the streaming graph
    """
    data = event.get("data", {})
    node = event.get("node")
    
    # Log the full event for debugging
    logger.debug(f"Stream event: {event}")
    
    # Update UI based on node type
    if node == "conversation_router":
        router_data = data.get("conversation_router", {})
        requires_analytics = router_data.get("requires_analytics", False)
        
        # Improved debugging info
        logger.info(f"Router data received: {router_data}")
        
        # If this is a general conversation (not analytics), display the response immediately
        if not requires_analytics:
            # First try to get from general_response field if present
            general_response = router_data.get("general_response", "")
            
            # If not found, try to extract from the message directly
            if not general_response and "messages" in router_data:
                messages = router_data["messages"]
                if messages and hasattr(messages[-1], "content"):
                    content = messages[-1].content
                    # Clean up the response by removing the analytics_query tag
                    tag_index = content.lower().find("analytics_query: false")
                    if tag_index > 0:
                        general_response = content[:tag_index].strip()
                    else:
                        general_response = content
            
            # Final fallback - if we still don't have a response, check if message is a string
            if not general_response and messages and isinstance(messages[-1], str):
                general_response = messages[-1]
                
            logger.info(f"Extracted general response: {general_response[:100]}...")
            
            # Store the response and update the UI
            if general_response:
                st.session_state.current_response["explanation"] = general_response
                
                # Update the UI with the general response
                if st.session_state.response_placeholder:
                    with st.session_state.response_placeholder:
                        st.markdown(general_response)
                
                # Clear other placeholders for general conversation
                if st.session_state.sql_placeholder:
                    with st.session_state.sql_placeholder:
                        st.empty()
                        
                if st.session_state.table_placeholder:
                    with st.session_state.table_placeholder:
                        st.empty()
                        
                if st.session_state.viz_placeholder:
                    with st.session_state.viz_placeholder:
                        st.empty()
                        
                if st.session_state.explanation_placeholder:
                    with st.session_state.explanation_placeholder:
                        st.empty()
            else:
                logger.warning("No general response extracted from router data")
                if st.session_state.response_placeholder:
                    with st.session_state.response_placeholder:
                        st.markdown("I'm not sure how to respond to that.")
        
        # If analytics is required, show a message that we're processing the query
        elif requires_analytics and st.session_state.response_placeholder:
            with st.session_state.response_placeholder:
                st.markdown("Processing your analytics query...")
    
    elif node == "sql_generator":
        if data.get("sql_generator", {}).get("sql_query"):
            # Display SQL query as it's generated
            sql_query = data["sql_generator"]["sql_query"]
            st.session_state.current_response["sql_query"] = sql_query
            
            logger.info(f"SQL query generated: {sql_query}")
            
            # Update SQL display in the UI
            if st.session_state.sql_placeholder:
                with st.session_state.sql_placeholder:
                    with st.expander("SQL Query", expanded=True):
                        st.markdown(sql_query)
            
            # Update status message
            if st.session_state.response_placeholder:
                with st.session_state.response_placeholder:
                    st.markdown("Generating SQL query...")
    
    elif node == "sql_executor":
        if "query_results" in data.get("sql_executor", {}):
            # SQL query is now running
            logger.info("Running SQL query on BigQuery")
            if st.session_state.response_placeholder:
                with st.session_state.response_placeholder:
                    st.markdown("Running SQL query on BigQuery...")
    
    elif node == "sql_reflection":
        reflection_data = data.get("sql_reflection", {})
        if reflection_data:
            # Extract the reflection result and feedback directly from the sql_reflection node data
            reflection_result = reflection_data.get("reflection_result")
            sql_feedback = reflection_data.get("sql_feedback")
            
            # Store these in session state for reference
            st.session_state.current_response["reflection_result"] = reflection_result
            if sql_feedback:
                st.session_state.current_response["sql_feedback"] = sql_feedback
            
            # Log the reflection decision
            logger.info(f"SQL Reflection decision: {reflection_result}")
            
            # Show reflection status in UI
            if st.session_state.response_placeholder:
                with st.session_state.response_placeholder:
                    if reflection_result == "PASS":
                        st.markdown("SQL results look good, generating visualization...")
                    elif reflection_result == "RETRY":
                        feedback_summary = sql_feedback[:100] + "..." if sql_feedback and len(sql_feedback) > 100 else "No specific feedback provided"
                        st.markdown(f"Refining SQL query to get better results: {feedback_summary}")
    
    elif node == "visualization_generator":
        viz_config = data.get("visualization_generator", {}).get("visualization_config")
        if viz_config:
            # Store visualization config and data
            st.session_state.current_response["viz_config"] = viz_config
            st.session_state.current_response["viz_data"] = viz_config.get("data", [])
            
            chart_type = viz_config.get("chart_type", "unknown")
            data_count = len(viz_config.get("data", []))
            logger.info(f"Visualization generated: {chart_type} chart with {data_count} data points")
            
            # Update visualization and table in the UI
            if st.session_state.viz_placeholder and st.session_state.table_placeholder:
                # Display table
                with st.session_state.table_placeholder:
                    with st.expander("Data Table", expanded=False):
                        try:
                            import pandas as pd
                            df = pd.DataFrame(viz_config.get("data", []))
                            st.dataframe(df, use_container_width=True)
                        except Exception as e:
                            logger.error(f"Error displaying data table: {str(e)}")
                            st.error(f"Error displaying data: {str(e)}")
                
                # Display visualization
                from src.web.components.visualization import render_visualization
                with st.session_state.viz_placeholder:
                    render_visualization(
                        viz_config, 
                        viz_config.get("data", [])
                    )
    
    elif node == "results_explainer":
        messages = data.get("results_explainer", {}).get("messages", [])
        if messages and len(messages) > 0:
            content = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
            
            # Store explanation
            st.session_state.current_response["explanation"] = content
            
            logger.info(f"Explanation generated: {content[:100]}...")
            
            # Update explanation in the UI
            if st.session_state.explanation_placeholder:
                with st.session_state.explanation_placeholder:
                    st.markdown("### Analysis")
                    st.markdown(content)


async def process_query_async(question: str):
    """
    Process a user query asynchronously and update UI with streaming results.
    
    Args:
        question: The user's natural language question
    """
    query_start_time = datetime.now()
    logger.info(f"Processing query: '{question}'")
    
    # Reset current response
    reset_current_response()
    
    # Mark as processing
    st.session_state.is_processing = True
    
    # Format chat history for the backend
    chat_history = []
    if st.session_state.chat_history:
        chat_history = st.session_state.chat_history.copy()
        logger.info(f"Using chat history with {len(chat_history)} previous exchanges for context")
    
    # Stream the results and update UI in real-time
    try:
        event_count = 0
        async for event in stream_analytics_query(question, handle_stream_event, chat_history=chat_history):
            # Events are processed in the handler
            event_count += 1
        
        logger.info(f"Processed {event_count} events from the analytics graph")
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        if st.session_state.response_placeholder:
            with st.session_state.response_placeholder:
                st.error(f"An error occurred while processing your query: {str(e)}")
    
    # Add the complete response to chat history
    st.session_state.chat_history.append({
        "question": question,
        "response": st.session_state.current_response.copy()
    })
    
    # Completed processing - IMPORTANT: Set this last to ensure UI updates properly
    st.session_state.is_processing = False
    
    # Log processing time
    processing_time = (datetime.now() - query_start_time).total_seconds()
    logger.info(f"Query processing completed in {processing_time:.2f} seconds")
    
    # Force rerun to update UI and ensure chat input appears
    st.rerun()