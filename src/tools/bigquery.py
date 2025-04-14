"""
Tools for executing BigQuery operations.
"""

from typing import Dict, Any
import re
from langchain_core.tools import tool
from google.cloud import bigquery
import streamlit as st
from google.oauth2 import service_account

from src.config import MAX_RESULTS_DISPLAY, FORBIDDEN_SQL_KEYWORDS

from dotenv import load_dotenv

load_dotenv()


def check_streamlit():
    """
    Function to check whether python code is run within streamlit

    Returns
    -------
    use_streamlit : boolean
        True if code is run within streamlit, else False
    """
    try:
        from streamlit.runtime.scriptrunner.script_runner import get_script_run_ctx

        if not get_script_run_ctx():
            use_streamlit = False
        else:
            use_streamlit = True
    except ModuleNotFoundError:
        use_streamlit = False
    return use_streamlit


if check_streamlit():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    bigquery_client = bigquery.Client(credentials=credentials)
else:
    bigquery_client = bigquery.Client()


@tool
def execute_bigquery_sql(sql: str) -> Dict[str, Any]:
    """
    Execute a BigQuery SQL query and return the results.

    Args:
        sql: The SQL query to execute

    Returns:
        A dictionary containing the success status, results (if successful),
        total row count (if successful), or error message (if failed)
    """
    try:
        # Add a safety check to prevent accidental data modification
        sql_lower = sql.lower().strip()

        # Simple check for any forbidden SQL keywords
        found_forbidden = False
        found_keyword = None

        for keyword in FORBIDDEN_SQL_KEYWORDS:
            pattern = r"\b{}\b".format(keyword)
            if re.search(pattern, sql_lower):
                found_forbidden = True
                found_keyword = keyword
                break

        if found_forbidden:
            return {
                "success": False,
                "error": f"Forbidden SQL operation detected: {found_keyword}",
            }

        query_job = bigquery_client.query(sql)
        results = query_job.result()

        # Convert results to a list of dictionaries for easier handling
        results_list = []
        for row in results:
            row_dict = {key: value for key, value in row.items()}
            results_list.append(row_dict)

        output = {
            "success": True,
            "results": results_list[:MAX_RESULTS_DISPLAY],
            "total_rows": results.total_rows,
        }

        return output
    except Exception as e:
        return {"success": False, "error": str(e)}
