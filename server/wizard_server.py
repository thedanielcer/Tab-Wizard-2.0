"""Wizard Server module that coordinates TCP and WebSocket servers for browser tab management.

This module sets up and manages:
1. A TCP server for handling command-line commands
2. A WebSocket server for browser tab event communication
3. A connection manager for monitoring browser tabs

The server coordinates between these components to provide a unified interface for
managing browser tabs across different profiles.
"""

import socket
import threading
import asyncio
from dotenv import load_dotenv
import os

from core.command_handler import handle_command
from core.connection_manager import ConnectionManager
from server.websocket_server import start_websocket_server, broadcast_to_plugins
from logger import Logger

load_dotenv()

HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))
WS_PORT = int(os.getenv("WS_PORT"))

logger = Logger("WizardServer")

connection_manager = ConnectionManager()

def handle_client_connection(conn, addr):
    """Handle a single TCP client connection.
    
    Args:
        conn: The socket connection object for the client.
        addr: The address tuple (host, port) of the client.
    
    This function:
    1. Receives a command from the client
    2. Processes the command using the command handler
    3. Sends an acknowledgment back to the client
    4. Closes the connection
    
    Called by the TCP server thread for each new client connection.
    """
    logger.info(f"Connected: {addr}")
    try:
        data = conn.recv(4096).decode("utf-8").strip()
        if data:
            handle_command(data)
        conn.sendall(b"OK")
    except Exception as e:
        logger.error(f"Error handling client connection: {e}")
    finally:
        conn.close()

def start_tcp_server():
    """Start the TCP server for handling command-line commands.
    
    This function:
    1. Creates a TCP socket
    2. Binds it to the configured host and port
    3. Listens for incoming connections
    4. Spawns a new thread for each client connection
    
    Runs in an infinite loop until the program is terminated.
    Called by the main function in a separate thread.
    """
    logger.info(f"Starting TCP server on {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            client_thread = threading.Thread(target=handle_client_connection, args=(conn, addr))
            client_thread.start()

async def main():
    """Main entry point for the Wizard Server.
    
    This function:
    1. Sets up the connection manager with the broadcast callback
    2. Starts the TCP server in a background thread
    3. Starts the WebSocket server and browser event listener concurrently
    
    The function runs until the program is terminated.
    Called when the script is run directly.
    """
    # Inject broadcast function into ConnectionManager
    connection_manager.set_broadcast_callback(broadcast_to_plugins)

    # Start TCP server in background thread
    tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
    tcp_thread.start()

    # Start WebSocket server and browser event listener concurrently
    await asyncio.gather(
        start_websocket_server(HOST, WS_PORT),
        connection_manager.listen_to_browser_events()
    )

if __name__ == "__main__":
    asyncio.run(main())