"""
Main application entry point for the Google Analytics - Business Intelligence - Agent.

This file provides two interfaces:
1. Command Line Interface (CLI)
2. Web Interface (using Streamlit)

Usage:
- For CLI: python main.py --ui cli
- For Web: python main.py --ui web or streamlit run main.py
"""

import argparse
from src.cli.app import run_cli
from src.web.run import run_streamlit_app
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def main():
    """
    Entry point for the application.
    Allows selecting between CLI and web interface.
    """
    parser = argparse.ArgumentParser(description="Google Analytics - Business Intelligence - Agent")
    parser.add_argument(
        "--ui",
        choices=["cli", "web"],
        default="web",
        help="Select user interface: cli or web",
    )
    
    args = parser.parse_args()
    
    if args.ui == "web":
        run_streamlit_app()
    else:
        run_cli()


if __name__ == "__main__":
    main()
