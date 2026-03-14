"""
Command Router Module

This module routes parsed commands to the appropriate plugin handlers.

Purpose:
    - Map commands to plugin handlers
    - Execute command handlers
    - Format and send responses
    - Handle errors gracefully

Key Classes:
    - CommandRouter: Routes commands to plugins

Command Flow:
    1. Packet received from mesh
    2. CommandParser parses text
    3. CommandRouter looks up handler
    4. Handler executes and returns response
    5. Response sent back to sender

Usage:
    router = CommandRouter(plugin_manager, serial_manager, database, config)
    response = router.RouteCommand(parsed, from_node)
    
    if response:
        serial_manager.SendTextToNode(from_node, response)
"""

from typing import Dict, Callable, Optional, Any, List

from bbs.protocol.CommandParser import ParsedCommand, CommandParser
from bbs.plugins.PluginManager import PluginManager
from bbs.Database import Database
from bbs.Configuration import Configuration
from bbs.SerialManager import SerialManager
from bbs.Logger import GetLogger


class CommandRouter:
    """
    Routes commands to appropriate plugin handlers.
    
    This class:
    - Maintains mapping of commands to handlers
    - Executes handlers with proper context
    - Formats and sends responses
    - Provides help functionality
    
    The router is the bridge between incoming packets and plugins.
    """
    
    def __init__(
        self,
        plugin_manager: PluginManager,
        serial_manager: SerialManager,
        database: Database,
        configuration: Configuration,
        logger=None
    ):
        """
        Initialize the command router.
        
        Args:
            plugin_manager: Plugin manager with loaded plugins
            serial_manager: Serial manager for sending responses
            database: Database instance
            configuration: Configuration object
            logger: Optional logger instance
        """
        self.plugin_manager = plugin_manager
        self.serial_manager = serial_manager
        self.database = database
        self.configuration = configuration
        self.logger = logger or GetLogger("CommandRouter")
        
        # Command parser
        self.parser = CommandParser()
        
        # Build command handler map from plugins
        self.command_handlers: Dict[str, Callable] = {}
        self._BuildHandlerMap()
    
    def _BuildHandlerMap(self) -> None:
        """
        Build the command-to-handler map from all plugins.
        
        This function iterates over all loaded plugins and
        collects their command handlers into a single map.
        """
        self.command_handlers = self.plugin_manager.GetCommandHandlers()
        
        # Add built-in commands
        self.command_handlers["HELP"] = self.HandleHelpCommand
        self.command_handlers["PING"] = self.HandlePingCommand
        
        self.logger.debug(f"Registered {len(self.command_handlers)} command handlers")
    
    def RouteCommand(
        self, 
        input_text: str, 
        from_node: str,
        interface: Any = None
    ) -> Optional[str]:
        """
        Route a command to the appropriate handler.
        
        This function:
        - Parses the input text
        - Looks up the handler
        - Executes the handler
        - Returns the response
        
        Args:
            input_text: Raw text from the packet
            from_node: Node ID of the sender
            interface: The interface that received the packet
            
        Returns:
            Response string to send back, or None if no response
        """
        # Parse the command
        parsed = self.parser.ParseCommand(input_text)
        
        if not parsed.is_valid:
            self.logger.debug(f"Failed to parse command: {parsed.error_message}")
            return f"Error: {parsed.error_message}"
        
        # Check if command exists
        if parsed.command not in self.command_handlers:
            return f"Unknown command: {parsed.command}. Type HELP for available commands."
        
        # Get handler
        handler = self.command_handlers[parsed.command]
        
        # Register the sender node
        self.database.RegisterNode(from_node)
        
        # Execute handler
        try:
            # Create handler context
            context = HandlerContext(
                from_node=from_node,
                arguments=parsed.arguments,
                database=self.database,
                configuration=self.configuration,
                serial_manager=self.serial_manager,
                plugin_manager=self.plugin_manager,
                logger=self.logger
            )
            
            # Call handler
            response = handler(context)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error executing command {parsed.command}: {e}")
            return f"Error executing command: {str(e)}"
    
    def GetAvailableCommands(self) -> List[str]:
        """
        Get list of all available commands.
        
        Returns:
            List of command names
        """
        return list(self.command_handlers.keys())
    
    def GetCommandHelp(self, command: str) -> Optional[str]:
        """
        Get help text for a specific command.
        
        Args:
            command: Command name to get help for
            
        Returns:
            Help text, or None if command not found
        """
        # Get handler
        handler = self.command_handlers.get(command.upper())
        
        if handler is None:
            return None
        
        # Try to get docstring
        if handler.__doc__:
            # Clean up docstring
            doc = handler.__doc__.strip()
            return f"{command.upper()}: {doc}"
        
        return f"{command.upper()}: No help available"
    
    def HandleHelpCommand(self, context: 'HandlerContext') -> str:
        """
        Handle the HELP command.
        
        Usage: HELP [command]
        
        If no command specified, lists all available commands.
        If command specified, shows help for that command.
        
        Args:
            context: Handler context with arguments
            
        Returns:
            Help text response (condensed for low bandwidth)
        """
        # Get BBS info
        bbs_name = self.configuration.GetBbsName()
        bbs_node = self.configuration.GetNodeId()
        
        # If specific command help requested
        if context.arguments:
            command = context.arguments[0].upper()
            help_text = self.GetCommandHelp(command)
            
            if help_text:
                return help_text
            else:
                return f"Unknown: {command}"
        
        # Otherwise show brief command list
        return f"{bbs_name} cmds: PING HELP MSG READ AREAS BBS"
    
    def HandlePingCommand(self, context: 'HandlerContext') -> str:
        """
        Handle the PING command.
        
        Usage: PING
        
        Responds with a pong message to confirm BBS is online.
        
        Args:
            context: Handler context
            
        Returns:
            Pong response
        """
        bbs_name = self.configuration.GetBbsName()
        return f"PONG {bbs_name}"


class HandlerContext:
    """
    Context object passed to command handlers.
    
    This provides handlers with access to all the services
    they need to process commands.
    
    Attributes:
        from_node: Node ID of the sender
        arguments: List of arguments from the command
        database: Database instance
        configuration: Configuration object
        serial_manager: Serial manager for sending responses
        plugin_manager: Plugin manager for accessing other plugins
        logger: Logger instance
    """
    
    def __init__(
        self,
        from_node: str,
        arguments: List[str],
        database: Database,
        configuration: Configuration,
        serial_manager: SerialManager,
        plugin_manager: PluginManager,
        logger
    ):
        """Initialize handler context."""
        self.from_node = from_node
        self.arguments = arguments
        self.database = database
        self.configuration = configuration
        self.serial_manager = serial_manager
        self.plugin_manager = plugin_manager
        self.logger = logger
    
    def SendResponse(self, message: str) -> None:
        """
        Send a response back to the sender.
        
        Args:
            message: Response message to send
        """
        self.serial_manager.SendTextToNode(self.from_node, message)
    
    def GetBbsNodeId(self) -> str:
        """Get the BBS node ID."""
        return self.configuration.GetNodeId()
    
    def GetBbsName(self) -> str:
        """Get the BBS name."""
        return self.configuration.GetBbsName()
