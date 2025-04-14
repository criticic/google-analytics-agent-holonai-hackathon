"""
Launcher script for the Google Analytics - Business Intelligence - Agent Streamlit interface
"""
import os
import sys
import subprocess
import logging

# Configure root logger to ensure logs are displayed
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("bigquery_launcher")

def run_streamlit_app():
    """Run the Streamlit app from the current directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "app.py")
    project_root = os.path.abspath(os.path.join(script_dir, "../.."))
    
    logger.info(f"Starting Google Analytics - Business Intelligence - Agent web interface...")
    
    # Set environment variables to ensure proper imports
    env = os.environ.copy()
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{project_root}:{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = project_root
    
    # Run streamlit with stdout and stderr redirected to the terminal
    process = subprocess.Popen(
        ["streamlit", "run", app_path, "--logger.level=info"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1  # Line buffered
    )
    
    logger.info("Streamlit process started. Forwarding logs to console...")
    
    # Forward the output to the terminal
    try:
        for line in process.stdout:
            print(line, end='')
    except KeyboardInterrupt:
        logger.info("Stopping Streamlit process...")
        process.terminate()
        process.wait()
    
    return process.returncode

if __name__ == "__main__":
    run_streamlit_app()