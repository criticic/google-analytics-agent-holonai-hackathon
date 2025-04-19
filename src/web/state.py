"""
Session state management for the Google Analytics - Business Intelligence - Agent web interface.
"""
import streamlit as st
import logging
from uuid import uuid4

# Configure logging
logger = st.logger.get_logger(__name__)

def initialize_session_state():
    """Initialize all required session state variables"""
    
    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
        logger.info("Initialized empty chat history")

    # Processing state
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False

    # Current response data
    if "current_response" not in st.session_state:
        reset_current_response()
    
    # Query text
    if "query" not in st.session_state:
        st.session_state.query = ""

    # UI placeholders
    if "response_placeholder" not in st.session_state:
        st.session_state.response_placeholder = None

    if "sql_placeholder" not in st.session_state:
        st.session_state.sql_placeholder = None

    if "viz_placeholder" not in st.session_state:
        st.session_state.viz_placeholder = None

    if "table_placeholder" not in st.session_state:
        st.session_state.table_placeholder = None

    if "explanation_placeholder" not in st.session_state:
        st.session_state.explanation_placeholder = None


def reset_current_response():
    """Reset the current response data"""
    st.session_state.current_response = {
        "id": str(uuid4()),
        "sql_query": None,
        "viz_config": None, 
        "viz_data": None,
        "explanation": None,
        "reflection_result": None,
        "sql_feedback": None
    }
    logger.debug("Reset current response data")