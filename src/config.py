"""
Configuration settings for the Google Analytics - Business Intelligence - Agent.
"""

from dotenv import load_dotenv
import os

load_dotenv()

# BigQuery dataset configuration
DATASET_NAME = "bigquery-public-data.google_analytics_sample"

# Query result limits
MAX_RESULTS_DISPLAY = 20

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")

# SQL safety settings
FORBIDDEN_SQL_KEYWORDS = [
    "insert",
    "update",
    "delete",
    "drop",
    "create",
    "alter",
    "truncate",
    "merge",
    "grant",
    "revoke",
    "commit",
    "rollback",
    "begin",
    "transaction",
]

# Memory configuration
MEMORY_CHECKPOINT_NAME = "analytics-agent-memory"

EXAMPLE_QUERIES = {
        "General Help": [
            "Hello, what can you help me with?",
            "Can you explain how this application works?",
        ],
        "Performance Metrics": [
            "What are the top 5 countries by total transactions?",
            "Which traffic sources lead to the highest conversion rates?",
            "Compare revenue from mobile vs desktop users",
            "Which marketing channels have the best ROI?",
            "How do conversion rates vary by geographic region?",
        ],
        "User Behavior": [
            "What is the average session duration by device category?",
            "How does user engagement differ between new and returning visitors?",
            "What's the bounce rate by browser type?",
            "Which days of the week have the highest user engagement?"
        ],
        "Content & Products": [
            "Show me the monthly trend of pageviews",
            "What are the top search keywords driving traffic to the site?",
        ],
    }