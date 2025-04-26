# TabWizard 2.0!

A silent, fast tab manager for Microsoft Edge — built with Python, and WebSockets.

## Requirements

- Python installed
- Launch Edge with remote debugging enabled

## Features

- Focus URLs in Edge instantly
- Works silently in the background
- Built for the Stream Deck
- Uses Edge’s remote debugging protocol

## Setup

1. Clone the repo
2. Create a `.env` file (see `.env.example`)
3. Set up a Python virtual environment
    `python -m venv venv`

4. Install dependencies:
    `pip install -r requirements.txt`

5. Install Stream Deck Plugin (Currently only available for Stream Deck XL)

The way I use it is have an AHK script in my startup folder that runs `powershell.exe -Command "& 'E:\Python Scripts\Tab Wizard\venv\Scripts\pythonw.exe' -m server.wizard_server", , Hide`. This is to start the server through the virtual environment on startup.
Have a hotkey run `Run, "e:/Path/to/the/script/rootdir/venv/Scripts/pythonw.exe" "e:/Path/to/the/script/rootdir/socket_client.py" -command-, , Hide`

## Stream Deck Use
-Install the plugin and add the action.
-When the action is pressed, a new page will appear where all the tabs currently open in the browser will be!
