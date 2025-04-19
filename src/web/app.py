"""
Streamlit-based chat interface for the Google Analytics - Business Intelligence - Agent
"""
import asyncio
import streamlit as st
import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.web.state import initialize_session_state
from src.web.components.sidebar import render_sidebar
from src.web.components.chat import display_chat_history
from src.web.handlers import handle_new_query
from src.utils.logging import configure_logging

configure_logging()
logger = logging.getLogger("gabi.web.app")

logger.info("Starting Google Analytics - Business Intelligence - Agent web application")

st.set_page_config(
    page_title="Google Analytics - Business Intelligence - Agent",
    page_icon="📊",
    layout="wide",
)
logger.info("Streamlit page configuration set")

initialize_session_state()

example_selected = render_sidebar()

st.title("Google Analytics - Business Intelligence - Agent")
st.markdown("""
Ask questions about your Google Analytics data and get instant insights.
The agent will:
1. Generate SQL queries from your natural language questions
2. Run the queries against BigQuery
3. Analyze results and create visualizations
4. Explain insights in natural language
""")

display_chat_history()

logger.info("Main UI components initialized")

prompt = st.session_state.query if example_selected else st.chat_input("Ask a question about your Google Analytics data...")

if prompt:
    if example_selected:
        st.session_state.query = ""
    
    handle_new_query(prompt)