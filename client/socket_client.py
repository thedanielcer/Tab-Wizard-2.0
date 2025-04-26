import socket
import sys
from dotenv import load_dotenv  
import os
import json
from logger import Logger

load_dotenv()

HOST = os.getenv('HOST')
PORT = int(os.getenv('PORT'))

logger = Logger("SocketClient")

if len(sys.argv) < 2:
    logger.error("Usage: python socket_client.py <url> [profile]")
    sys.exit(1)

url = sys.argv[1]
profile = sys.argv[2] if len(sys.argv) >= 3 else "personal"

payload = {
    "url": url,
    "profile": profile
}

logger.info(f"Connecting to {HOST}:{PORT}")

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        logger.debug(f"sending url: {url} on {profile} profile")
        s.connect((HOST, PORT))
        s.sendall(json.dumps(payload).encode('utf-8'))

        response = s.recv(1024).decode('utf-8').strip()
        logger.info(f"Response: {response}")


except ConnectionRefusedError:
    logger.error("Connection refused. Please ensure the server is running.")
except Exception as e:
    logger.error(f"An error occurred: {e}")

