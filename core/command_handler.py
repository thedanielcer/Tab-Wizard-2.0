"""Command Handler module for processing command-line commands.

This module provides functionality to:
1. Parse and validate command-line commands
2. Execute the appropriate actions based on the command
3. Handle errors and provide feedback
"""

from .wizard_core import focus_or_open_tab
import json
from logger import Logger

logger = Logger("CommandHandler")

# Command -> URL mapping
# === Load command mappings from JSON file ===

def handle_command(data: str):
    """Process a command-line command.
    
    Args:
        data: The command string to process.
    
    This function:
    1. Parses the command to determine the action and parameters
    2. Executes the appropriate action using the wizard core functions
    3. Logs the result of the command execution
    
    Supported commands:
    - focus <tab_id> <profile>: Focus a specific tab in the specified profile
    - list <profile>: List all tabs in the specified profile
    
    Called by the TCP server when a command is received from a client.
    """
    try:
        # Parse the command payload
        payload = json.loads(data)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse payload: {data}")
        return

    # Extract URL and profile from payload
    url = payload.get("url")
    profile = payload.get("profile", "personal")

    # Validate URL format
    if url.startswith("http://") or url.startswith("https://"):
        logger.info(f"Focusing or opening {url} on {profile} profile")
        focus_or_open_tab(url, profile)
    else:
        logger.error(f"Invalid URL: {url}")
        
