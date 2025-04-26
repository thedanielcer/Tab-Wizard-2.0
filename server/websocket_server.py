"""WebSocket Server module for handling browser tab event communication.

This module provides functionality to:
1. Manage WebSocket connections with browser plugins
2. Broadcast tab events to connected plugins
3. Handle plugin connections and disconnections
4. Process plugin messages and commands
"""

import asyncio
import websockets
import json
import requests
from core.favicon_handler import get_favicon_string_base64
from core.wizard_core import get_debug_port, activate_tab, get_tabs, focus_edge_window
from core.tab_title_cleaner import clean_tab_title

from logger import Logger

logger = Logger("WebSocketServer")

# Keep track of all connected plugin websockets
connected_websockets = set()

async def websocket_handler(websocket):
    """Handle a WebSocket connection from a browser plugin.
    
    Args:
        websocket: The WebSocket connection object.
    
    This function:
    1. Adds the connection to the set of connected websockets
    2. Processes incoming messages from the plugin
    3. Handles plugin disconnection
    4. Removes the connection from the set when done
    
    Called by the WebSocket server for each new plugin connection.
    """
    logger.info("Plugin connected via WebSocket")
    connected_websockets.add(websocket)
    try:
        async for message in websocket:
            logger.debug(f"Received from plugin: {message}")
            try:
                # Parse and process the message
                payload = json.loads(message)
                if payload.get("type") == "close_tab":
                    await handle_close_tab(payload)
                elif payload.get("type") == "focus_tab":
                    await handle_focus_tab(payload)
                elif payload.get("type") == "first_connection":
                    # Send current tab state for both profiles
                    for profile in ["personal", "work"]:
                        payload = await handle_first_connection(profile)
                        await websocket.send(json.dumps(payload))

            except json.JSONDecodeError:
                logger.error(f"Invalid message received from plugin: {message}")

    except websockets.exceptions.ConnectionClosed:
        logger.info("Plugin disconnected")
    finally:
        connected_websockets.remove(websocket)

async def start_websocket_server(host: str, port: int):
    """Start the WebSocket server.
    
    Args:
        host: The host address to bind the server to.
        port: The port number to listen on.
    
    This function:
    1. Creates a WebSocket server
    2. Starts listening for connections
    3. Handles each connection using the websocket_handler
    
    Called by the main function to start the WebSocket server.
    """
    server = await websockets.serve(websocket_handler, host, port)
    logger.info(f"WebSocket server started on {host}:{port}")
    await server.wait_closed()

async def broadcast_to_plugins(event: dict):
    """Broadcast an event to all connected plugin clients.
    
    Args:
        event: The event data to broadcast.
    
    This function:
    1. Formats the event data as a JSON string
    2. Sends the event to all connected websockets
    3. Logs the broadcast for debugging
    
    Called by the connection manager when a tab event occurs.
    """
    if connected_websockets:
        # Format and send the event to all connected plugins
        message = json.dumps(event)
        tab = event.get('tabs')[0]
        logger.debug(f"Broadcasting to plugins: type:{event.get('type')}, tab: {tab.get('title')}")
        await asyncio.gather(*[ws.send(message) for ws in connected_websockets])

async def handle_close_tab(payload: dict):
    """Handle a request to close a tab.
    
    Args:
        payload: The message payload containing tab information.
    
    This function:
    1. Extracts the tab ID and profile from the payload
    2. Sends a command to the browser to close the tab
    3. Logs the result of the operation
    
    Called by the websocket handler when a close_tab message is received.
    """
    tab_id = payload.get("tabId")
    profile = payload.get("profile")
    
    if not tab_id:
        logger.error("Missing tabId in close_tab request")
        return
    
    debug_port = get_debug_port(profile)

    try:
        # Send command to browser to close the tab
        requests.get(f"http://127.0.0.1:{debug_port}/json/close/{tab_id}", proxies={"http": None, "https": None})
        logger.info(f"Closed tab {tab_id} in {profile} profile")
    except Exception as e:
        logger.error(f"Failed to close tab {tab_id} on profile {profile}: {e}")

async def handle_focus_tab(payload: dict):
    """Handle a request to focus a tab.
    
    Args:
        payload: The message payload containing tab information.
    
    This function:
    1. Extracts the tab ID and profile from the payload
    2. Focuses the browser window
    3. Activates the specified tab
    4. Logs the result of the operation
    
    Called by the websocket handler when a focus_tab message is received.
    """
    tab_id = payload.get("tabId")
    profile = payload.get("profile")
    
    if not tab_id:
        logger.error("Missing tabId in focus_tab request")
        return
    
    debug_port = get_debug_port(profile)

    # Focus the browser window and activate the tab
    focus_edge_window(profile)
    activate_tab(tab_id, debug_port)

async def handle_first_connection(profile: str):
    """Handle the initial connection from a plugin.
    
    Args:
        profile: Either "personal" or "work" indicating which browser profile to check.
    
    This function:
    1. Gets the list of open tabs for the specified profile
    2. Formats the tab information for the plugin
    3. Returns the formatted data
    
    Called by the websocket handler when a first_connection message is received.
    Returns: A dictionary containing the current tab state for the profile.
    """
    debug_port = get_debug_port(profile)
    tabs = get_tabs(debug_port)
    
    if tabs is None:
        logger.info("No tabs found on first connection")
        return {
            "type": "no_tabs_open",
            "tabs": [],
            "profile": profile
        }
    
    # Format tab information for the plugin
    tabs_list = []
    for tab in tabs:
        if tab.get("type") != "page":
            continue
        
        tab_id = tab.get("id")
        url = tab.get("url")
        title = clean_tab_title(tab.get("title"), url)

        # Get favicon for the tab
        favicon = get_favicon_string_base64(url)
        
        # Add tab information to the list
        tabs_list.append({
            "tabId": tab_id,
            "title": title,
            "favicon": favicon
        })
    
    return {
        "type": "current_tabs",
        "tabs": tabs_list,
        "profile": profile
    }
        
        



