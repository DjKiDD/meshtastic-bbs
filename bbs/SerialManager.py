"""
Serial Manager Module

This module manages connections to Meshtastic devices via serial ports.

Purpose:
    - Manage multiple serial connections to Meshtastic devices
    - Handle connection/disconnection lifecycle
    - Route incoming packets to command processor
    - Provide send functionality to mesh

Key Classes:
    - SerialManager: Manages all serial connections
    - SerialDevice: Represents a configured serial device

Connection Model:
    - Each configured serial port gets one SerialInterface
    - All interfaces share the same packet callback
    - Messages can be broadcast or sent to specific nodes

Usage:
    manager = SerialManager(config, logger)
    manager.ConnectAll()
    
    # Register callback for incoming packets
    manager.SetPacketCallback(my_callback)
    
    # Send messages
    manager.SendTextToMesh("Hello mesh")
    manager.SendTextToNode("!abcd1234", "Hello node")
    
    # Clean shutdown
    manager.DisconnectAll()
"""

import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

# Try to import meshtastic
try:
    import meshtastic
    from meshtastic.serial_interface import SerialInterface
    from pubsub import pub
    MESHTASTIC_AVAILABLE = True
except ImportError:
    MESHTASTIC_AVAILABLE = False
    SerialInterface = None

from bbs.Configuration import Configuration, SerialDeviceConfig
from bbs.Logger import GetLogger


@dataclass
class SerialDevice:
    """
    Represents a connected serial device.
    
    Attributes:
        config: The configuration for this device
        interface: The SerialInterface instance (if connected)
        connected: Whether the device is currently connected
        last_error: Last error message (if any)
    """
    config: SerialDeviceConfig
    interface: Optional[Any] = None
    connected: bool = False
    last_error: Optional[str] = None


class SerialManager:
    """
    Manages connections to Meshtastic devices via serial ports.
    
    This class handles:
    - Connecting to multiple serial devices
    - Maintaining connection health
    - Routing incoming packets to handlers
    - Sending messages to the mesh
    
    Attributes:
        config: Configuration object
        logger: Logger instance
    """
    
    def __init__(self, config: Configuration, logger=None):
        """
        Initialize the serial manager.
        
        Args:
            config: Configuration object with serial device settings
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or GetLogger("SerialManager")
        
        # Dict of devices by port path
        self.devices: Dict[str, SerialDevice] = {}
        
        # Packet callback function
        self.packet_callback: Optional[Callable] = None
        
        # Subscribe to meshtastic packet events if available
        if MESHTASTIC_AVAILABLE:
            pub.subscribe(self._OnMeshtasticPacket, "meshtastic.receive")
    
    def ConnectAll(self) -> None:
        """
        Connect to all configured serial devices.
        
        This function:
        - Iterates over all configured serial devices
        - Attempts to connect to each one
        - Stores the interface for later use
        
        Note:
            If a device fails to connect, it will be retried automatically
            on the next packet receive attempt.
        """
        devices = self.config.GetSerialDevices()
        
        if not devices:
            self.logger.warning("No serial devices configured")
            return
        
        self.logger.info(f"Connecting to {len(devices)} serial device(s)...")
        
        for device_config in devices:
            self.ConnectDevice(device_config)
    
    def ConnectDevice(self, device_config: SerialDeviceConfig) -> bool:
        """
        Connect to a single serial device.
        
        Args:
            device_config: Configuration for the device to connect
            
        Returns:
            True if connected successfully, False otherwise
        """
        port = device_config.port
        label = device_config.label or port
        
        self.logger.info(f"Connecting to device: {label} ({port})")
        
        # Create device entry
        device = SerialDevice(config=device_config)
        
        if not MESHTASTIC_AVAILABLE:
            self.logger.error("Meshtastic library not available")
            device.last_error = "Meshtastic library not installed"
            self.devices[port] = device
            return False
        
        try:
            # Attempt to connect
            interface = SerialInterface(devPath=port, connectNow=True)
            device.interface = interface
            device.connected = True
            device.last_error = None
            
            self.logger.info(f"Connected to device: {label}")
            
        except Exception as e:
            device.connected = False
            device.last_error = str(e)
            self.logger.error(f"Failed to connect to {label}: {e}")
        
        # Store device
        self.devices[port] = device
        
        return device.connected
    
    def DisconnectAll(self) -> None:
        """
        Disconnect all serial devices.
        
        This function cleanly shuts down all connections.
        """
        self.logger.info("Disconnecting all serial devices...")
        
        for port, device in self.devices.items():
            if device.interface:
                try:
                    device.interface.close()
                    self.logger.debug(f"Disconnected from {port}")
                except Exception as e:
                    self.logger.error(f"Error closing {port}: {e}")
        
        self.devices.clear()
        self.logger.info("All devices disconnected")
    
    def SetPacketCallback(self, callback: Callable[[dict], None]) -> None:
        """
        Set the callback function for incoming packets.
        
        Args:
            callback: Function to call with incoming packets
            
        The callback will receive a dictionary with packet details:
            - 'from': Source node ID
            - 'to': Destination node ID  
            - 'text': Message text (if text packet)
            - 'type': Packet type
            - etc.
        """
        self.packet_callback = callback
    
    def _OnMeshtasticPacket(self, packet: dict, interface) -> None:
        """
        Internal callback for Meshtastic packet events.
        
        This function is called by the meshtastic library when
        a packet is received. It then forwards to the registered
        packet callback.
        
        Args:
            packet: The received packet dictionary
            interface: The interface that received the packet
        """
        # Filter out our own packets
        if packet.get('from') == self.config.GetNodeId():
            return
        
        # Forward to registered callback
        if self.packet_callback:
            try:
                self.packet_callback(packet, interface)
            except Exception as e:
                self.logger.error(f"Error in packet callback: {e}")
    
    def SendTextToMesh(self, text: str, channel_index: int = 0) -> bool:
        """
        Send a text message to the entire mesh.
        
        Args:
            text: Message text to send
            channel_index: Which channel to send on (default: 0)
            
        Returns:
            True if at least one device sent successfully
        """
        success = False
        
        for port, device in self.devices.items():
            if not device.connected or not device.interface:
                continue
            
            try:
                device.interface.sendText(text, channelIndex=channel_index)
                success = True
                self.logger.debug(f"Sent broadcast on {port}")
            except Exception as e:
                self.logger.error(f"Failed to send broadcast on {port}: {e}")
        
        return success
    
    def SendTextToNode(self, node_id: str, text: str) -> bool:
        """
        Send a text message to a specific node.
        
        Args:
            node_id: Destination node ID
            text: Message text to send
            
        Returns:
            True if at least one device sent successfully
        """
        success = False
        
        for port, device in self.devices.items():
            if not device.connected or not device.interface:
                continue
            
            try:
                device.interface.sendText(text, destinationId=node_id)
                success = True
                self.logger.debug(f"Sent to {node_id} on {port}")
            except Exception as e:
                self.logger.error(f"Failed to send to {node_id} on {port}: {e}")
        
        return success
    
    def GetConnectedDeviceCount(self) -> int:
        """
        Get the number of currently connected devices.
        
        Returns:
            Count of connected devices
        """
        return sum(1 for d in self.devices.values() if d.connected)
    
    def GetDeviceStatus(self) -> List[Dict[str, Any]]:
        """
        Get status information for all configured devices.
        
        Returns:
            List of device status dictionaries
        """
        status = []
        
        for port, device in self.devices.items():
            status.append({
                'port': port,
                'label': device.config.label or port,
                'connected': device.connected,
                'last_error': device.last_error,
                'channel_index': device.config.channel_index,
            })
        
        return status
    
    def ReconnectDevice(self, port: str) -> bool:
        """
        Attempt to reconnect a specific device.
        
        Args:
            port: The serial port path
            
        Returns:
            True if reconnected successfully
        """
        if port not in self.devices:
            self.logger.warning(f"Device not found: {port}")
            return False
        
        device_config = self.devices[port].config
        
        # Close existing connection
        if self.devices[port].interface:
            try:
                self.devices[port].interface.close()
            except Exception:
                pass
        
        # Try to reconnect
        return self.ConnectDevice(device_config)
    
    def ReconnectAll(self) -> None:
        """
        Attempt to reconnect all devices.
        
        This is useful after a network disruption or device reset.
        """
        self.logger.info("Attempting to reconnect all devices...")
        
        for port in list(self.devices.keys()):
            self.ReconnectDevice(port)
        
        connected = self.GetConnectedDeviceCount()
        self.logger.info(f"Reconnect complete: {connected}/{len(self.devices)} devices connected")
    
    def GetInterfaces(self) -> Dict[str, Any]:
        """
        Get all connected interfaces.
        
        Returns:
            Dict mapping port to interface object
        """
        return {
            port: device.interface 
            for port, device in self.devices.items() 
            if device.connected and device.interface
        }
    
    def IsMeshtasticAvailable(self) -> bool:
        """
        Check if the meshtastic library is available.
        
        Returns:
            True if meshtastic is installed, False otherwise
        """
        return MESHTASTIC_AVAILABLE
