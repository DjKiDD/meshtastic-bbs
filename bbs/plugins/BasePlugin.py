"""
Base Plugin Module

This module defines the abstract base class that all plugins must inherit from.

Purpose:
    - Define the interface all plugins must implement
    - Provide common functionality for all plugins
    - Enable plugin discovery and loading

Key Classes:
    - BasePlugin: Abstract base class for all plugins

Plugin Lifecycle:
    1. Plugin is discovered and loaded
    2. OnLoad is called with PluginContext
    3. Plugin registers command handlers
    4. Commands are routed to handlers
    5. OnUnload is called when plugin is disabled

Usage:
    class MyPlugin(BasePlugin):
        Name = "my_plugin"
        Version = "1.0.0"
        Description = "My custom plugin"
        
        CommandHandlers = {
            "MYCMD": HandleMyCommand,
        }
        
        def OnLoad(self, context):
            self.context = context
            
        def HandleMyCommand(self, args, from_node):
            return "Response"
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Callable, Optional, Any
import logging


class BasePlugin(ABC):
    """
    Abstract base class that all BBS plugins must inherit from.
    
    This class defines the interface and common functionality
    that all plugins must provide.
    
    Class Attributes:
        Name: Unique identifier for the plugin (used in config)
        Version: Semantic version string
        Description: Human-readable description of the plugin
        CommandHandlers: Dict mapping command names to handler methods
    
    Instance Attributes:
        logger: Logger instance for this plugin
        context: PluginContext (set after OnLoad)
    """
    
    # Plugin metadata - must be overridden by subclasses
    Name: str = ""
    Version: str = "1.0.0"
    Description: str = ""
    
    # Command handlers - maps command name to handler method
    # Format: {"COMMAND": self.HandleMethod}
    CommandHandlers: Dict[str, Callable] = {}
    
    def __init__(self):
        """Initialize the plugin."""
        # Logger will be set after plugin is loaded
        self.logger: Optional[logging.Logger] = None
        self.context: Optional['PluginContext'] = None
    
    def OnLoad(self, context: 'PluginContext') -> None:
        """
        Called when the plugin is loaded.
        
        This is where plugins should:
        - Store the context for later use
        - Initialize any required state
        - Set up any resources
        
        Args:
            context: PluginContext providing access to BBS services
            
        Note:
            Subclasses must call super().OnLoad(context) if they override this method.
        """
        self.context = context
        # Create a logger for this plugin
        self.logger = logging.getLogger(f"meshtastic-bbs.plugins.{self.Name}")
        
        self.logger.info(f"Plugin '{self.Name}' v{self.Version} loaded")
    
    def OnUnload(self) -> None:
        """
        Called when the plugin is unloaded.
        
        This is where plugins should:
        - Clean up any resources
        - Save any persistent state
        - Cancel any pending operations
        
        Note:
            Subclasses can override this method to add cleanup logic.
        """
        if self.logger:
            self.logger.info(f"Plugin '{self.Name}' unloaded")
    
    def OnPacketReceived(self, packet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Hook called for every received packet.
        
        This allows plugins to:
        - Inspect incoming packets
        - Modify packets
        - Suppress packets (return None)
        
        Args:
            packet: The raw packet dictionary
            
        Returns:
            The (possibly modified) packet, or None to suppress
            
        Note:
            This is optional - override only if needed.
            Return the packet unchanged by default (just return packet).
        """
        return packet
    
    def Migrate(self, database: 'Database') -> None:
        """
        Called during database migrations.
        
        This allows plugins to:
        - Add their own tables
        - Add columns to existing tables
        - Perform data migrations
        
        Args:
            database: Database instance to modify
            
        Note:
            This is optional - override only if the plugin needs database changes.
        """
        pass
    
    def GetCommandHandlers(self) -> Dict[str, Callable]:
        """
        Get the command handlers registered by this plugin.
        
        Returns:
            Dictionary mapping command names to handler methods
        """
        return self.CommandHandlers
    
    def GetHelpText(self) -> str:
        """
        Get help text for the commands this plugin provides.
        
        Returns:
            Formatted help string
            
        Note:
            Override this to provide custom help text.
            Default implementation returns basic info.
        """
        if not self.CommandHandlers:
            return ""
        
        lines = [f"=== {self.Name} v{self.Version} ==="]
        lines.append(self.Description)
        lines.append("")
        
        for cmd in sorted(self.CommandHandlers.keys()):
            lines.append(f"  {cmd}")
        
        return "\n".join(lines)
    
    def GetName(self) -> str:
        """Get the plugin name."""
        return self.Name
    
    def GetVersion(self) -> str:
        """Get the plugin version."""
        return self.Version
    
    def GetDescription(self) -> str:
        """Get the plugin description."""
        return self.Description


class PluginContext:
    """
    Context object passed to plugins providing access to BBS services.
    
    This object is provided to plugins when they are loaded and provides
    access to all the services the BBS provides.
    
    Attributes:
        Database: Database instance for data operations
        Configuration: Configuration instance for settings
        Interfaces: Dict of serial interfaces by port/label
        Logger: Logger instance for the plugin
    """
    
    def __init__(
        self,
        database: 'Database',
        configuration: 'Configuration',
        interfaces: Dict[str, Any],
        logger: logging.Logger
    ):
        """
        Initialize the plugin context.
        
        Args:
            database: Database instance
            configuration: Configuration instance
            interfaces: Dict of serial interfaces
            logger: Logger instance
        """
        self.Database = database
        self.Configuration = configuration
        self.Interfaces = interfaces
        self.Logger = logger
    
    def BroadcastToMesh(self, message: str, channel_index: int = 0) -> None:
        """
        Send a message to the entire mesh.
        
        Args:
            message: Text message to broadcast
            channel_index: Which channel to send on (default: 0)
            
        Note:
            This sends on all connected interfaces.
        """
        # Import here to avoid circular imports
        from bbs.SerialManager import SerialManager
        
        for port, interface in self.Interfaces.items():
            try:
                interface.sendText(message, channelIndex=channel_index)
            except Exception as e:
                self.Logger.error(f"Failed to broadcast on {port}: {e}")
    
    def SendToNode(self, node_id: str, message: str) -> None:
        """
        Send a direct message to a specific node.
        
        Args:
            node_id: Destination node ID
            message: Text message to send
            
        Note:
            This sends on all connected interfaces.
            The mesh will route to the destination.
        """
        for port, interface in self.Interfaces.items():
            try:
                interface.sendText(message, destinationId=node_id)
            except Exception as e:
                self.Logger.error(f"Failed to send to {node_id} on {port}: {e}")
    
    def GetPluginConfiguration(self, plugin_name: str) -> Dict[str, Any]:
        """
        Get configuration settings for a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dictionary of plugin-specific settings
        """
        return self.Configuration.GetPluginSettings(plugin_name)
    
    def GetBbsNodeId(self) -> str:
        """
        Get this BBS's node ID.
        
        Returns:
            The configured BBS node ID
        """
        return self.Configuration.GetNodeId()
    
    def GetBbsName(self) -> str:
        """
        Get the BBS name.
        
        Returns:
            The configured BBS name
        """
        return self.Configuration.GetBbsName()


# Type hint imports (avoid circular imports by using strings)
from bbs.Configuration import Configuration
from bbs.Database import Database
