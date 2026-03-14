"""
Application Module

This is the main application class that ties everything together.

Purpose:
    - Initialize all components
    - Manage the application lifecycle
    - Handle incoming packets
    - Provide CLI interface

Key Classes:
    - Application: Main application class

Usage:
    app = Application(config_path="config.yaml")
    app.Start()
    
    # Application runs until interrupted
    # Press Ctrl+C to stop
    
    app.Stop()
"""

import sys
import signal
import time
from typing import Optional

from bbs.Configuration import Configuration
from bbs.Database import Database
from bbs.SerialManager import SerialManager
from bbs.Logger import Logger, GetLogger
from bbs.plugins.BasePlugin import PluginContext
from bbs.plugins.PluginManager import PluginManager
from bbs.protocol.CommandRouter import CommandRouter


class Application:
    """
    Main application class for the Meshtastic BBS server.
    
    This class manages:
    - Configuration loading
    - Database initialization
    - Serial device connections
    - Plugin loading
    - Command routing
    - Packet handling
    
    Lifecycle:
        1. Create Application instance
        2. Call Start() to initialize
        3. Application runs, processing packets
        4. Call Stop() to shut down
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the application.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config: Optional[Configuration] = None
        self.database: Optional[Database] = None
        self.serial_manager: Optional[SerialManager] = None
        self.plugin_manager: Optional[PluginManager] = None
        self.command_router: Optional[CommandRouter] = None
        self.logger = None
        
        # Running state
        self.is_running = False
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._SignalHandler)
        signal.signal(signal.SIGTERM, self._SignalHandler)
    
    def _SignalHandler(self, signum, frame):
        """
        Handle shutdown signals.
        
        Called when Ctrl+C or SIGTERM is received.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        print("\nShutdown signal received...")
        self.Stop()
        sys.exit(0)
    
    def Start(self) -> None:
        """
        Start the BBS server.
        
        This function:
        - Loads configuration
        - Sets up logging
        - Initializes database
        - Connects to serial devices
        - Loads plugins
        - Starts packet processing
        
        Raises:
            Exception: If any initialization fails
        """
        print("=" * 50)
        print("Meshtastic BBS Server")
        print("=" * 50)
        
        # Load configuration
        print("\n[1/6] Loading configuration...")
        try:
            self.config = Configuration.LoadConfiguration(self.config_path)
            print(f"      Loaded config from: {self.config_path}")
            print(f"      BBS Node ID: {self.config.GetNodeId()}")
            print(f"      BBS Name: {self.config.GetBbsName()}")
        except Exception as e:
            print(f"      ERROR: Failed to load configuration: {e}")
            raise
        
        # Setup logging
        print("\n[2/6] Setting up logging...")
        self.logger = Logger.SetupLogging(
            level=self.config.GetLogLevel(),
            log_file=self.config.GetLogFile(),
            log_format=self.config.GetLogFormat()
        )
        self.logger = GetLogger("Application")
        self.logger.info("Meshtastic BBS Server starting...")
        
        # Initialize database
        print("\n[3/6] Initializing database...")
        try:
            self.database = Database(
                self.config.GetDatabasePath(),
                GetLogger("Database")
            )
            self.database.Initialize()
            self.logger.info(f"Database initialized: {self.config.GetDatabasePath()}")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
        
        # Initialize serial manager
        print("\n[4/6] Connecting to serial devices...")
        self.serial_manager = SerialManager(
            self.config,
            GetLogger("SerialManager")
        )
        
        # Check if meshtastic is available
        if not self.serial_manager.IsMeshtasticAvailable():
            print("      WARNING: meshtastic library not installed")
            print("      Install with: pip install meshtastic")
            print("      Running in test mode (no mesh connectivity)")
        else:
            # Connect to devices
            self.serial_manager.ConnectAll()
            
            device_count = self.serial_manager.GetConnectedDeviceCount()
            configured_count = self.config.GetSerialDeviceCount()
            
            print(f"      Connected: {device_count}/{configured_count} devices")
            
            if device_count == 0 and configured_count > 0:
                print("      WARNING: No devices connected. Check serial ports.")
        
        # Set up plugin system
        print("\n[5/6] Loading plugins...")
        plugin_context = PluginContext(
            database=self.database,
            configuration=self.config,
            interfaces=self.serial_manager.GetInterfaces(),
            logger=GetLogger("Plugins")
        )
        
        self.plugin_manager = PluginManager(plugin_context)
        
        # Load enabled plugins
        enabled_plugins = self.config.GetEnabledPlugins()
        self.plugin_manager.LoadEnabledPlugins(enabled_plugins)
        
        # Run plugin migrations
        self.plugin_manager.RunMigrations()
        
        print(f"      Loaded {len(self.plugin_manager.GetAllPlugins())} plugin(s)")
        
        # Set up command router
        print("\n[6/6] Setting up command router...")
        self.command_router = CommandRouter(
            plugin_manager=self.plugin_manager,
            serial_manager=self.serial_manager,
            database=self.database,
            configuration=self.config,
            logger=GetLogger("CommandRouter")
        )
        
        # Register packet callback
        self.serial_manager.SetPacketCallback(self.OnPacketReceived)
        
        # Mark as running
        self.is_running = True
        
        # Print startup info
        print("\n" + "=" * 50)
        print("BBS Server Started!")
        print("=" * 50)
        print(f"Node ID: {self.config.GetNodeId()}")
        print(f"Name: {self.config.GetBbsName()}")
        print(f"Plugins: {', '.join(self.plugin_manager.GetLoadedPluginNames())}")
        print("=" * 50)
        print("\nWaiting for packets... (Ctrl+C to stop)")
        print("")
        
        self.logger.info("BBS Server started successfully")
    
    def Stop(self) -> None:
        """
        Stop the BBS server.
        
        This function cleanly shuts down:
        - Stops packet processing
        - Unloads plugins
        - Disconnects serial devices
        - Closes database connection
        
        Note:
            This can be called from signal handler.
        """
        if not self.is_running:
            return
        
        self.logger.info("Stopping BBS Server...")
        self.is_running = False
        
        # Unload plugins
        if self.plugin_manager:
            self.plugin_manager.UnloadAll()
        
        # Disconnect serial devices
        if self.serial_manager:
            self.serial_manager.DisconnectAll()
        
        # Close database
        if self.database:
            self.database.Close()
        
        self.logger.info("BBS Server stopped")
        
        print("\nBBS Server stopped.")
    
    def OnPacketReceived(self, packet: dict, interface) -> None:
        """
        Handle a received packet from the mesh.
        
        This is the callback registered with the serial manager.
        It processes incoming packets and routes commands.
        
        Args:
            packet: The received packet dictionary
            interface: The interface that received the packet
        """
        # Only process TEXT_MESSAGE_APP packets
        decoded = packet.get('decoded', {})
        portnum = decoded.get('portnum', '')
        
        if portnum != 'TEXT_MESSAGE_APP':
            # Skip telemetry, position, nodeinfo, routing packets
            return
        
        # Get the text content - check decoded.text first (meshtastic stores it there)
        text = packet.get('text') or decoded.get('text') or ''
        
        # Clean up text if it's in bytes
        if isinstance(text, bytes):
            try:
                text = text.decode('utf-8')
            except:
                text = ''
        
        if not text:
            self.logger.warning("No text in packet")
            return
        
        # Get source node - check fromId first
        from_node = packet.get('fromId') or str(packet.get('from', ''))
        
        if not from_node:
            self.logger.warning("No from_node in packet")
            return
        
        # Skip our own packets
        if from_node == self.config.GetNodeId():
            return
        
        # Check if this is a direct message to BBS or a broadcast
        to_id = packet.get('toId', '')
        bbs_node_id = self.config.GetNodeId()
        is_direct_message = (to_id == bbs_node_id)
        
        # If not a direct message (i.e., broadcast to channel), check if we should respond
        if not is_direct_message:
            channel_config = self.config.GetChannelConfig()
            if not channel_config.respond_to_channel:
                # Channel responses disabled - ignore broadcast
                self.logger.debug(f"Ignoring broadcast - channel responses disabled")
                return
            
            # Check if command is allowed on channel
            cmd = text.strip().upper().split()[0] if text.strip() else ''
            if cmd not in channel_config.allowed_commands:
                self.logger.debug(f"Ignoring broadcast - '{cmd}' not in allowed commands")
                return
        
        self.logger.info(f"Received from {from_node}: '{text}'")
        
        # Route the command
        response = self.command_router.RouteCommand(text, from_node, interface)
        
        # Send response back to sender
        if response:
            self.logger.info(f"Sending response to {from_node}: '{response}'")
            # Small delay to avoid overwhelming the radio
            time.sleep(0.1)
            success = self.serial_manager.SendTextToNode(from_node, response)
            if success:
                self.logger.info(f"Response sent successfully")
            else:
                self.logger.error(f"Failed to send response to {from_node}")
        else:
            self.logger.warning("No response generated")
    
    def Run(self) -> None:
        """
        Run the application (blocking).
        
        This starts the server and blocks until stopped.
        Uses a simple loop to keep the application alive.
        """
        if not self.is_running:
            self.Start()
        
        # Keep running
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.Stop()
    
    def GetStatus(self) -> dict:
        """
        Get current server status.
        
        Returns:
            Dictionary with status information
        """
        return {
            'running': self.is_running,
            'node_id': self.config.GetNodeId() if self.config else None,
            'name': self.config.GetBbsName() if self.config else None,
            'plugins': self.plugin_manager.GetLoadedPluginNames() if self.plugin_manager else [],
            'devices': self.serial_manager.GetDeviceStatus() if self.serial_manager else [],
        }


def Main():
    """
    Main entry point for the BBS server.
    
    Usage:
        python -m bbs.Application config.yaml
    """
    import argparse
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Meshtastic BBS Server"
    )
    parser.add_argument(
        'config',
        nargs='?',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='Meshtastic BBS Server 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Create and run application
    app = Application(config_path=args.config)
    app.Run()


if __name__ == "__main__":
    Main()
