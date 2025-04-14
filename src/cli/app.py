"""
Command-line interface for the Google Analytics - Business Intelligence - Agent.
"""

from src.core.graph import run_analytics_query


def run_cli():
    """
    Run the CLI interface for the Google Analytics - Business Intelligence - Agent.
    """
    print("BigQuery Google Analytics Agent")
    print("===============================")
    print("Ask a question about Google Analytics data:")

    while True:
        question = input("\nEnter your question (or 'exit' to quit): ")
        if question.lower() == "exit":
            break

        print("\nProcessing your question...")
        results = run_analytics_query(question)

        print("\n----- RESULTS -----\n")
        print(results)
        print("\n-------------------\n")
