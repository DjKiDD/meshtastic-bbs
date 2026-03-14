"""
BBS Package

Meshtastic Bulletin Board System

A lightweight BBS server for multiple Meshtastic nodes to run on
Raspberry Pi Zero W2.

Structure:
    - Application.py: Main application entry point
    - Configuration.py: Configuration management
    - Database.py: SQLite database wrapper
    - Logger.py: Logging setup
    - SerialManager.py: Serial device management
    - protocol/: Command parsing and routing
    - plugins/: Plugin system and built-in plugins
"""

__version__ = "1.0.0"
__author__ = "MeshBBS Community"
__description__ = "Meshtastic Bulletin Board System"

from bbs.Application import Application, Main

__all__ = [
    'Application',
    'Main',
    '__version__',
]
