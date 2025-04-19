"""
Sidebar components for the Google Analytics - Business Intelligence - Agent.
"""
import streamlit as st
import logging
from src.config import EXAMPLE_QUERIES

logger = logging.getLogger("gabi.web.components")

def render_sidebar():
    """
    Render the sidebar with app information and categorized example queries.
    
    Returns:
        bool: True if an example query was selected
    """
    st.sidebar.markdown("# Google Analytics - Business Intelligence - Agent")
    
    st.sidebar.markdown("---")
    
    st.sidebar.markdown("### Example Queries")
    st.sidebar.write("Click on any example to use it:")
    
    example_selected = False
    
    query_categories = EXAMPLE_QUERIES
    
    for category, queries in query_categories.items():
        with st.sidebar.expander(category):
            for i, query in enumerate(queries):
                if st.button(query, key=f"{category}_{i}"):
                    st.session_state.query = query
                    example_selected = True
                    logger.info(f"Example query selected: '{query}'")

    st.sidebar.markdown("---")
    st.sidebar.markdown("Made by [the Cynikal inc.](https://github.com/criticic) during the [HOLON](https://www.holonai.ai/) x [Königsberger Bridges Institute](https://kb.institute/) [AI AGENTS HACKATHON 2025](https://hackathon.holonai.ai/)")
    st.sidebar.markdown("[GitHub Repository](https://github.com/criticic/holonai-hackathon)")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About the Dataset")
    st.sidebar.markdown("""
    This application uses the [Google Analytics sample dataset from BigQuery](https://console.cloud.google.com/marketplace/product/obfuscated-ga360-data/obfuscated-ga360-data?project=lexical-script-761&folder=&organizationId=)
    The dataset contains sample web analytics data from the [Google Merchandise Store](https://googlemerchandisestore.com/).
    """)

    logger.info("Sidebar components initialized")
    
    return example_selected