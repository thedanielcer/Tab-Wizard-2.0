import asyncio
import websockets
import json
import requests
from dotenv import load_dotenv
import os

from logger import Logger
from urllib.parse import urlparse
from websockets.exceptions import InvalidHandshake, InvalidStatus

from core.favicon_handler import get_favicon_string_base64
from core.tab_title_cleaner import clean_tab_title

load_dotenv()

DEBUG_PORT_PERSONAL = int(os.getenv("DEBUG_PORT_PERSONAL"))
DEBUG_PORT_WORK = int(os.getenv("DEBUG_PORT_WORK"))

""" ConnectionManager class handles the WebSocket connections to Edge browser instances
and manages tab events (creation, updates, deletion) for both personal and work profiles """
class ConnectionManager:
    def __init__(self):
        """Initialize the ConnectionManager.
        
        Sets up the logger and initializes data structures for tracking tabs in both personal and work profiles.
        Called when creating a new ConnectionManager instance.
        """
        # Initialize logger and data structures for tracking tabs
        self.logger = Logger("ConnectionManager")
        self.broadcast_callback = None
        self.page_targets = {"personal": set(), "work": set()}

    def set_broadcast_callback(self, callback):
        """Set the callback function for broadcasting events to plugins.
        
        Args:
            callback: An async function that will be called to broadcast events to connected plugins.
        Called by the WebSocket server when setting up the connection manager.
        """
        # Set the callback function that will be used to broadcast events to plugins
        self.broadcast_callback = callback

    async def listen_to_browser_events(self):
        """Start listening to browser events for both personal and work profiles.
        
        This method runs two parallel event listeners, one for each profile.
        Called by the main application to start the connection manager.
        Returns: None
        """
        # Start listening to browser events for both personal and work profiles simultaneously
        await asyncio.gather(
            self.listen_to_profile("personal"),
            self.listen_to_profile("work")
        )

    async def listen_to_profile(self, profile: str):
        """Continuously attempt to connect to and listen for events from a specific browser profile.
        
        Args:
            profile: Either "personal" or "work" indicating which browser profile to monitor.
        
        This method runs in an infinite loop, attempting to connect to the browser's debugging interface
        and listening for tab events. If the connection is lost, it will attempt to reconnect.
        Called by listen_to_browser_events().
        Returns: None
        """
        # Continuously attempt to connect to and listen for events from a specific browser profile
        debug_port = DEBUG_PORT_PERSONAL if profile == "personal" else DEBUG_PORT_WORK

        while True:
            # Get the WebSocket URL for the browser's debugging interface
            ws_url = await self.get_browser_websocket_url(debug_port)

            self.logger.info(f"Attempting to connect to {ws_url}...")
            if ws_url:
                try:
                    self.logger.info(f"Connecting to {profile} WebSocket on port {debug_port}...")
                    async with websockets.connect(ws_url, open_timeout=3, ping_interval=None) as websocket:
                        self.logger.info(f"Connected to {profile} WebSocket")
                        # Enable target discovery to receive tab events
                        await websocket.send(json.dumps({
                            "id": 1,
                            "method": "Target.setDiscoverTargets",
                            "params": {"discover": True}
                        }))
                        
                        await self.event_loop(websocket, profile)
                except InvalidStatus as e:
                    self.logger.error(f"{profile} WebSocket handshake failed: {e}")
                except InvalidHandshake as e:
                    self.logger.error(f"{profile} WebSocket connection rejected (status {e.status_code})")
                except Exception as e:
                    self.logger.error(f"Error connecting to {profile} WebSocket: {e}")
            else:
                self.logger.debug(f"{profile} Edge not available yet...")

            # Wait before attempting to reconnect
            await asyncio.sleep(2)

    async def get_browser_websocket_url(self, debug_port: int):
        """Retrieve the WebSocket URL for the browser's debugging interface.
        
        Args:
            debug_port: The port number where the browser's debugging interface is listening.
        
        Called by listen_to_profile() when attempting to connect to the browser.
        Returns: The WebSocket URL for the browser's debugging interface, or None if the browser is not available.
        """
        # Retrieve the WebSocket URL for the browser's debugging interface
        try:
            response = requests.get(f"http://127.0.0.1:{debug_port}/json/version", proxies={"http": None, "https": None})
            data = response.json()
            return data["webSocketDebuggerUrl"]
        except Exception:
            return None

    async def event_loop(self, websocket, profile: str):
        """Main event loop that processes incoming WebSocket messages.
        
        Args:
            websocket: The WebSocket connection to the browser.
            profile: Either "personal" or "work" indicating which browser profile is being monitored.
        
        This method runs in an infinite loop, receiving and processing messages from the browser.
        If the connection is lost, it will exit the loop and allow the outer loop to attempt reconnection.
        Called by listen_to_profile() after establishing a WebSocket connection.
        Returns: None
        """
        # Main event loop that processes incoming WebSocket messages
        try:
            while True:
                message = await websocket.recv()
                event = json.loads(message)
                await self.handle_event(event, profile)
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"{profile} WebSocket closed. Waiting for reconnection...")
        except Exception as e:
            self.logger.error(f"{profile} WebSocket listen error: {e}")

    async def handle_event(self, event: dict, profile: str):
        """Route incoming browser events to appropriate handlers based on event type.
        
        Args:
            event: The event data received from the browser.
            profile: Either "personal" or "work" indicating which browser profile the event came from.
        
        This method acts as a router, directing events to the appropriate handler based on the event type.
        Called by event_loop() for each message received from the browser.
        Returns: None
        """
        # Route incoming browser events to appropriate handlers based on event type
        event_type = event.get("method")
        # if event_type == "Target.targetCreated" or event_type == "Target.targetInfoChanged":
        #     self.logger.debug(f"{event}")

        match event_type:
            case "Target.targetCreated":
                await self.handle_new_tab_event(event, profile)
            case "Target.targetDestroyed":
                await self.handle_tab_closed_event(event, profile)
            case "Target.targetInfoChanged":
                await self.handle_tab_info_changed_event(event, profile)

    async def handle_new_tab_event(self, event: dict, profile: str):
        """Handle the creation of a new tab.
        
        Args:
            event: The event data containing information about the new tab.
            profile: Either "personal" or "work" indicating which browser profile the tab was created in.
        
        This method processes new tab events, adds the tab to tracking, and broadcasts the event to plugins.
        Only processes tabs that haven't been seen before to avoid duplicates.
        Called by handle_event() when a Target.targetCreated event is received.
        Returns: None
        """
        # Handle the creation of a new tab
        target_info = event.get("params", {}).get("targetInfo", {})
        target_id = target_info.get("targetId")
        tab_title = target_info.get("title", "unknown")
        url = target_info.get("url", "unknown")
        cleaned_tab_title = clean_tab_title(tab_title, url)
        # Only process if it's a page and we haven't seen this tab before
        if target_info.get("type") == "page" and target_id not in self.page_targets[profile]:
            self.logger.debug(f"New tab event from browser - target id: {target_id}, title: {tab_title}, url: {url}")
            self.page_targets[profile].add(target_id)
            if not url or url == "unknown":
                return
            
            # Get the favicon for the new tab
            favicon = get_favicon_string_base64(url)

            if self.broadcast_callback:
                await self.broadcast_event_to_plugins("new_tab", target_id, cleaned_tab_title, favicon, profile)

    async def handle_tab_info_changed_event(self, event: dict, profile: str):
        """Handle updates to existing tabs or newly discovered tabs.
        
        Args:
            event: The event data containing updated tab information.
            profile: Either "personal" or "work" indicating which browser profile the tab belongs to.
        
        This method processes tab info change events, which can either be updates to existing tabs
        or newly discovered tabs that weren't caught by the new tab event.
        Called by handle_event() when a Target.targetInfoChanged event is received.
        Returns: None
        """
        # Handle updates to existing tabs or newly discovered tabs
        target_info = event.get("params", {}).get("targetInfo")
        target_id = target_info.get("targetId")
        tab_title = target_info.get("title", "unknown")
        url = target_info.get("url", "unknown")
        cleaned_tab_title = clean_tab_title(tab_title, url)
        if target_info.get("type") == "page" and url != "edge://downloads/hub":
            if target_id in self.page_targets[profile]:
                # This is an update to an existing tab
                self.logger.debug(f"Tab info changed event from browser - target info: {target_info}, url: {url}")
                if not url or url == "unknown":
                    return
                new_tab = False
            else:
                # This is a newly discovered tab
                new_tab = True
                self.page_targets[profile].add(target_id)

            self.logger.info(f"Tab info changed ({profile}): {url}")
            
            # Get the favicon for the tab
            favicon = get_favicon_string_base64(url)

            if self.broadcast_callback:
                # Broadcast either a new tab or tab info change event
                if new_tab:
                    await self.broadcast_event_to_plugins("new_tab", target_id, cleaned_tab_title, favicon, profile)
                else:
                    await self.broadcast_event_to_plugins("tab_info_change", target_id, cleaned_tab_title, favicon, profile)

    async def handle_tab_closed_event(self, event: dict, profile: str):
        """Handle the closing of a tab.
        
        Args:
            event: The event data containing information about the closed tab.
            profile: Either "personal" or "work" indicating which browser profile the tab was closed in.
        
        This method processes tab close events, removes the tab from tracking, and broadcasts the event to plugins.
        Only processes tabs that were previously being tracked.
        Called by handle_event() when a Target.targetDestroyed event is received.
        Returns: None
        """
        # Handle the closing of a tab
        target_id = event.get("params", {}).get("targetId")
        if target_id and target_id in self.page_targets[profile]:
            self.logger.info(f"Tab closed ({profile}): {target_id}")
            # Remove the tab from our tracking
            self.page_targets[profile].remove(target_id)
            if self.broadcast_callback:
                await self.broadcast_event_to_plugins("tab_closed", target_id, "", "", profile)
    
    async def broadcast_event_to_plugins(self, type: str, tabId: str, title: str, favicon: str, profile: str):
        """Broadcast an event to all connected plugins with tab information.
        
        Args:
            type: The type of event ("new_tab", "tab_info_change", or "tab_closed").
            tabId: The unique identifier of the tab.
            title: The title of the tab.
            favicon: The base64-encoded favicon of the tab.
            profile: Either "personal" or "work" indicating which browser profile the tab belongs to.
        
        This method formats the event data and sends it to all connected plugins via the broadcast callback.
        Called by the various event handlers when they need to notify plugins of tab changes.
        Returns: None
        """
        # Broadcast an event to all connected plugins with tab information
        await self.broadcast_callback({
            "type": type,
            "tabs": [
                {
                    "tabId": tabId,
                    "title": title,
                    "favicon": favicon,
                }
            ],
            "profile": profile
        })

