"""
Chat interface components for the Google Analytics - Business Intelligence - Agent.
"""
import streamlit as st
import logging
from src.web.components.visualization import render_visualization

# Configure logging
logger = st.logger.get_logger(__name__)

def create_chat_message_placeholders():
    """
    Create empty placeholders for the chat response components.
    
    Returns:
        None, but sets the placeholders in session state
    """
    with st.chat_message("assistant"):
        # Create placeholders for different parts of the response
        st.session_state.response_placeholder = st.empty()
        with st.session_state.response_placeholder:
            st.markdown("Analyzing your question...")
        
        st.session_state.sql_placeholder = st.empty()
        st.session_state.table_placeholder = st.empty()
        st.session_state.viz_placeholder = st.empty()
        st.session_state.explanation_placeholder = st.empty()

def display_chat_history():
    """
    Display the full chat history in the Streamlit interface.
    """
    logger.debug(f"Rendering chat history with {len(st.session_state.chat_history)} messages")
    
    for i, chat in enumerate(st.session_state.chat_history):
        # Display user question
        with st.chat_message("user"):
            st.markdown(chat["question"])
        
        # Display assistant response
        with st.chat_message("assistant"):
            response = chat["response"]
            
            # Display SQL query if available
            if response.get("sql_query"):
                with st.expander("SQL Query", expanded=False):
                    st.markdown(response["sql_query"])
            
            # Display data table if available
            if response.get("viz_data"):
                with st.expander("Data Table", expanded=False):
                    try:
                        import pandas as pd
                        df = pd.DataFrame(response["viz_data"])
                        st.dataframe(df, use_container_width=True)
                    except Exception as e:
                        logger.error(f"Error displaying data table in history: {str(e)}")
                        st.error(f"Error displaying data: {str(e)}")
            
            # Display visualization if data and config are available
            if response.get("viz_config") and response.get("viz_data"):
                render_visualization(
                    response["viz_config"],
                    response["viz_data"]
                )
            
            # Display explanation if available
            if response.get("explanation"):
                st.markdown("### Analysis")
                st.markdown(response["explanation"])