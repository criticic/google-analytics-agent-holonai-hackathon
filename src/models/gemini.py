"""
Model configuration for Google Vertex AI.
"""

import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import API_KEY

# Set logging level to ERROR to filter warnings
logger = logging.getLogger()
logger.setLevel(logging.ERROR)


# Initialize the model client
def get_model(temperature=0, model_name="gemini-2.5-flash-preview-04-17"):
    """
    Get a configured instance of the ChatGoogleGenerativeAI model.

    Args:
        temperature: The sampling temperature (0.0 to 1.0)
        model_name: The name of the Vertex AI model to use

    Returns:
        An initialized ChatGoogleGenerativeAI instance
    """
    return ChatGoogleGenerativeAI(
        model=model_name, temperature=temperature, api_key=API_KEY
    )
