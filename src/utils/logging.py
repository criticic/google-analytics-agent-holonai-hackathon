"""
Centralized logging configuration for the entire application.
Import this module at the start of the application to set up logging.
"""
import logging
import sys
import os
import inspect

def configure_logging():
    """
    Configure logging for all modules in the application.
    This function should be called at the beginning of the application.
    """
    # Check if logging is already configured
    if not logging.getLogger().handlers:
        # Set up root logger with console handler
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - [%(filename)s:%(funcName)s:%(lineno)d] - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        
        # Define module-specific logger names with clearer hierarchy
        loggers = {
            "gabi.core.graph": logging.INFO,
            "gabi.core.agents": logging.INFO,
            "gabi.web.launcher": logging.INFO,
            "gabi.web.app": logging.INFO,
            "gabi.web.handlers": logging.INFO,
            "gabi.web.components": logging.INFO,
            "gabi.models": logging.INFO,
            "gabi.tools": logging.INFO,
            "gabi.cli": logging.INFO
        }
        
        # Set specific levels for our application loggers
        for logger_name, level in loggers.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)

# Helper function to get the current file and function name
def get_logger_context():
    """
    Get context information for logging (file, function, line).
    
    Returns:
        str: Formatted context string with file and function name
    """
    frame = inspect.currentframe().f_back.f_back  # Go up two frames to get the caller
    filename = os.path.basename(frame.f_code.co_filename)
    function = frame.f_code.co_name
    lineno = frame.f_lineno
    return f"[{filename}:{function}:{lineno}]"