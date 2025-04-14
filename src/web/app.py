"""
Streamlit-based chat interface for the Google Analytics - Business Intelligence - Agent
"""
import asyncio
import streamlit as st
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = st.logger.get_logger(__name__)

# Add the project root directory to Python path for proper imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import components
from src.web.state import initialize_session_state
from src.web.components.sidebar import render_sidebar
from src.web.components.chat import display_chat_history
from src.web.handlers import handle_new_query

logger.info("Starting Google Analytics - Business Intelligence - Agent web application")

# Set up the page configuration
st.set_page_config(
    page_title="Google Analytics - Business Intelligence - Agent",
    page_icon="📊",
    layout="wide",
)
logger.info("Streamlit page configuration set")

# Initialize session state
initialize_session_state()

# Render the sidebar and get example selection status
example_selected = render_sidebar()

# Main layout
st.title("Google Analytics - Business Intelligence - Agent")
st.markdown("""
Ask questions about your Google Analytics data and get instant insights.
The agent will:
1. Generate SQL queries from your natural language questions
2. Run the queries against BigQuery
3. Analyze results and create visualizations
4. Explain insights in natural language
""")

# Display chat history
display_chat_history()

logger.info("Main UI components initialized")

# Get query from example or chat input
# ALWAYS keep the chat input visible regardless of processing state
prompt = st.session_state.query if example_selected else st.chat_input("Ask a question about your Google Analytics data...")

# Handle the prompt - from example or chat input
if prompt:
    # Clear the stored query if it came from an example
    if example_selected:
        st.session_state.query = ""
    
    # Process the query
    handle_new_query(prompt)