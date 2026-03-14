"""
BBS Plugins Package

This package contains the plugin system for the BBS server.

Structure:
    - BasePlugin.py: Abstract base class for plugins
    - PluginManager.py: Plugin discovery and loading
    - PluginContext.py: Context passed to plugins
    - builtin/: Built-in plugins (PersonalMessaging, BulletinBoard)
"""

from bbs.plugins.BasePlugin import BasePlugin, PluginContext
from bbs.plugins.PluginManager import PluginManager

__all__ = [
    'BasePlugin',
    'PluginContext', 
    'PluginManager',
]
