"""
Google Analytics - Business Intelligence - Agent package.

This package provides a natural language interface to Google BigQuery,
allowing users to ask questions about Google Analytics data and receive
insightful answers powered by Gemini and LangGraph.
"""

from src.core.graph import run_analytics_query
from src.cli.app import run_cli

__all__ = ["run_analytics_query", "run_cli"]
