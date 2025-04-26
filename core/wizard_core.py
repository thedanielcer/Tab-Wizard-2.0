"""Wizard Core module for browser interaction and tab management.

This module provides core functionality for:
1. Interacting with browser instances
2. Managing browser tabs
3. Handling browser window focus
4. Retrieving tab information
"""

import requests
import subprocess
import time
from dotenv import load_dotenv
import os
import pygetwindow as gw

from logger import Logger
from urllib.parse import urlparse

# === CONFIGURATION ===
load_dotenv()
EDGE_PATH = os.getenv("EDGE_PATH")
USER_DATA_DIR_PERSONAL = os.getenv("USER_DATA_DIR_PERSONAL")
USER_DATA_DIR_WORK = os.getenv("USER_DATA_DIR_WORK")
DEBUG_PORT_PERSONAL = int(os.getenv("DEBUG_PORT_PERSONAL"))
DEBUG_PORT_WORK = int(os.getenv("DEBUG_PORT_WORK"))

logger = Logger("WizardCore")

priority_domains = [
    "youtube.com",
    "chatgpt.com",
]

def get_debug_port(profile):
    """Get the debug port for a specific browser profile.
    
    Args:
        profile: Either "personal" or "work" indicating which browser profile to use.
    
    Returns:
        The debug port number for the specified profile.
    """
    return DEBUG_PORT_PERSONAL if profile == "personal" else DEBUG_PORT_WORK

def launch_edge_on_selected_tab(desired_url, profile = "personal"):
    """Launch Edge browser with a specific URL and profile.
    
    Args:
        desired_url: The URL to open in the browser.
        profile: Either "personal" or "work" indicating which browser profile to use.
    
    This function:
    1. Determines the appropriate user data directory
    2. Launches Edge with the specified URL and debug port
    3. Waits for the browser to start
    
    Called by focus_or_open_tab() when the browser needs to be launched.
    """
    logger.info(f"Launching Edge on {profile} profile with URL: {desired_url}")
    user_data_dir = USER_DATA_DIR_PERSONAL if profile == "personal" else USER_DATA_DIR_WORK
    
    # Launch Edge with the specified URL and debug port
    subprocess.Popen([
        EDGE_PATH,
        f'--user-data-dir={user_data_dir}',
        f'--remote-debugging-port={get_debug_port(profile)}',
        f'{desired_url}',
    ])
    # Wait for browser to start
    time.sleep(2)

# === FOCUS EDGE WINDOW ===
def focus_edge_window(profile = "personal"):
    """Focus the Edge browser window for a specific profile.
    
    Args:
        profile: Either "personal" or "work" indicating which browser profile to focus.
    
    This function:
    1. Searches for the Edge window with the appropriate title
    2. Restores the window if it's minimized
    3. Brings the window to the foreground
    
    Called by focus_or_open_tab() when a tab needs to be focused.
    """
    logger.info(f"Looking for edge window on {profile} profile")
    # Determine the window title based on profile
    title_part = "work debug" if profile == "work" else "personal"
    # Find visible, non-minimized Edge windows
    edge_window = [w for w in gw.getWindowsWithTitle(f'{title_part} - microsoft\u200b edge') if w.title.lower() and not w.isMinimized]

    if not edge_window:
        logger.error("No edge window found")
        # Try to find any Edge window, even if minimized
        edge_window = [w for w in gw.getWindowsWithTitle(f'{title_part} - microsoft\u200b edge')]
    
    if edge_window:
        edge_window = edge_window[0]
        logger.debug(f"Edge window found: {edge_window.title}")
        if edge_window.isMinimized:
            logger.debug("Edge was minimized, restoring")
            edge_window.restore()
        logger.debug("Activating edge window")
        edge_window.activate()

# === ACTIVATE DESIRED TAB ===
def activate_tab(tab_id, debug_port):
    """Activate (focus) a specific browser tab.
    
    Args:
        tab_id: The unique identifier of the tab to activate.
        debug_port: The debug port of the browser instance.
    
    This function sends a command to the browser to focus the specified tab.
    Called by focus_or_open_tab() when a tab needs to be focused.
    """
    try:
        logger.debug(f"Activating tab {tab_id}")
        # Send command to browser to activate the tab
        requests.get(f"http://127.0.0.1:{debug_port}/json/activate/{tab_id}", proxies={"http": None, "https": None})
        logger.debug(f"Tab {tab_id} activated")
    except Exception as e:
        logger.error(f"Failed to activate tab {tab_id}: {e}")

# === IF DESIRED TAB DOESN'T EXIST, OPEN IT ===
def open_url_on_new_tab(desired_url, profile = "personal"):
    """Open a URL in a new tab.
    
    Args:
        desired_url: The URL to open in the new tab.
        profile: Either "personal" or "work" indicating which browser profile to use.
    
    This function launches Edge with the specified URL in a new tab.
    Called by focus_or_open_tab() when a matching tab is not found.
    """
    logger.info(f"Opening {desired_url} in new tab on {profile} profile")
    user_data_dir = USER_DATA_DIR_PERSONAL if profile == "personal" else USER_DATA_DIR_WORK

    # Launch Edge with the URL in a new tab
    subprocess.Popen([
        EDGE_PATH,
        f'--user-data-dir={user_data_dir}',
        f'{desired_url}'
    ])

# === CONNECT TO TABS ===
def get_tabs(debug_port):
    """Get a list of all open tabs in a browser instance.
    
    Args:
        debug_port: The debug port of the browser instance.
    
    Returns:
        A list of dictionaries containing information about each open tab.
        Each dictionary includes the tab's ID, title, URL, and type.
        Returns None if the browser is not available.
    """
    logger.debug("Getting tabs")
    try:
        logger.debug("getting response")
        # Get list of all targets from browser
        response = requests.get(f"http://127.0.0.1:{debug_port}/json", proxies={"http": None, "https": None})
        logger.debug("response received")
        all_targets = response.json()
        # Only keep real tabs
        logger.debug("Tabs received")
        # Filter for page-type targets and sort by domain
        tabs = [tab for tab in all_targets if tab.get("type") == "page"]
        tabs.sort(key=get_priority)
        return tabs
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to Edge")
        return None

# === NORMALIZE URL ===
def normalize_url(url):
    """Normalize a URL for comparison.
    
    Args:
        url: The URL to normalize.
    
    Returns:
        A normalized version of the URL with:
        - Query parameters removed
        - Trailing slashes removed
        - Converted to lowercase
    """
    return url.split("?")[0].rstrip("/").lower()

# === FOR USE ONLY OUTSIDE PLUGIN ===
def focus_or_open_tab(desired_url, profile = "personal"):
    """Focus an existing tab or open a new one with the desired URL.
    
    Args:
        desired_url: The URL to focus or open.
        profile: Either "personal" or "work" indicating which browser profile to use.
    
    This function:
    1. Checks if the browser is running
    2. Launches the browser if needed
    3. Searches for a matching tab
    4. Focuses the tab if found, or opens a new one if not found
    
    Called by the command handler when a focus command is received.
    """
    logger.info(f"Focusing or opening tab: {desired_url} on {profile} profile")
    debug_port = get_debug_port(profile)
    tabs = get_tabs(debug_port)

    if tabs is None:
        logger.error(f"{profile} Edge not running or not in debug mode. Launching...")
        # Launch browser if not running
        launch_edge_on_selected_tab(desired_url, profile)
        tabs = get_tabs(debug_port)
    else:
        logger.debug(f"{profile} Edge is running, and got tabs")

    if tabs is None:
        logger.error(f"{profile} Still couldn't connect to Edge after launching.")
        return

    # Search for matching tab
    for tab in tabs:
        logger.info(f"Comparing: {desired_url} vs {tab.get('url')}")
        if normalize_url(desired_url) in normalize_url(tab.get("url", "")):
            logger.debug(f"Matching tab found for URL: {desired_url}")
            focus_edge_window(profile)
            activate_tab(tab.get("id"), debug_port)
            logger.info(f"Focused Tab: {desired_url}")
            return
    
    # If no matching tab found, open a new one
    logger.debug(f"No matching tab found for URL: {desired_url}. Opening new tab.")
    open_url_on_new_tab(desired_url, profile)

def get_priority(tab):
    domain = urlparse(tab.get("url", "")).netloc.lower()

    for index, priority_domain in enumerate(priority_domains):
        if domain == priority_domain or domain.endswith("." + priority_domain):
            return (0, index, domain)
        
    return (1, domain)
