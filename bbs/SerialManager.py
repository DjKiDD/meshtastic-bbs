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
import threading
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
        node_id: The node ID of this radio (from the radio itself)
    """
    config: SerialDeviceConfig
    interface: Optional[Any] = None
    connected: bool = False
    last_error: Optional[str] = None
    node_id: Optional[str] = None


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
        
        # ACK tracking: {packet_id: {"node_id": str, "event": threading.Event, "acked": bool}}
        self._pending_acks: Dict[int, Dict] = {}
        self._ack_lock = threading.Lock()
        
        # Subscribe to meshtastic packet events - ACKs come through regular receive
        if MESHTASTIC_AVAILABLE:
            pub.subscribe(self._OnMeshtasticPacket, "meshtastic.receive")
    
    def ConnectAll(self) -> None:
        """
        Connect to all configured serial devices.
        
        This function:
        - If no devices configured, auto-detect Meshtastic devices
        - Iterates over all configured serial devices
        - Attempts to connect to each one
        - Stores the interface for later use
        
        Note:
            If a device fails to connect, it will be retried automatically
            on the next packet receive attempt.
        """
        devices = self.config.GetSerialDevices()
        
        # If no devices configured, auto-detect
        if not devices:
            self.logger.info("No serial devices configured, auto-detecting...")
            self._AutoDetectDevices()
            return
        
        self.logger.info(f"Connecting to {len(devices)} serial device(s)...")
        
        for device_config in devices:
            self.ConnectDevice(device_config)
    
    def _AutoDetectDevices(self) -> None:
        """
        Auto-detect Meshtastic devices on the system.
        
        Uses meshtastic's built-in device discovery to find
        all connected Meshtastic devices.
        """
        if not MESHTASTIC_AVAILABLE:
            self.logger.error("Meshtastic library not available")
            return
        
        # First, try to list all serial ports to see what's available
        try:
            import serial.tools.list_ports
            all_ports = list(serial.tools.list_ports.comports())
            self.logger.info(f"Found {len(all_ports)} serial port(s): {[p.device for p in all_ports]}")
        except Exception as e:
            self.logger.warning(f"Could not enumerate serial ports: {e}")
        
        # Try using meshtastic's findPorts
        try:
            import meshtastic.util
            ports = meshtastic.util.findPorts(True)
        except Exception as e:
            self.logger.error(f"Failed to detect devices with findPorts: {e}")
            ports = []
        
        if not ports:
            # Try without eliminate_duplicates
            try:
                ports = meshtastic.util.findPorts(False)
            except:
                ports = []
        
        if not ports:
            self.logger.warning("No Meshtastic devices found")
            return
        
        self.logger.info(f"Found {len(ports)} Meshtastic device(s): {ports}")
        
        for port in ports:
            device_config = SerialDeviceConfig(
                port=port,
                label=port.split('/')[-1]  # Use device name as label
            )
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
            
            # Get node ID from the radio itself
            # Try getMyNodeInfo() which explicitly fetches node info
            try:
                if hasattr(interface, 'getMyNodeInfo'):
                    my_info = interface.getMyNodeInfo()
                    if my_info and 'myNodeNum' in my_info:
                        node_num = my_info['myNodeNum']
                        if node_num:
                            node_id = f"!{node_num:08x}"
                            device.node_id = node_id
                            self.logger.info(f"Device {label} node ID: {device.node_id}")
                # Also try localNode as backup
                if not device.node_id and hasattr(interface, 'localNode') and interface.localNode:
                    node_num = interface.localNode.nodeNum
                    if node_num:
                        node_id = f"!{node_num:08x}"
                        device.node_id = node_id
                        self.logger.info(f"Device {label} node ID: {device.node_id}")
                # Also try myInfo as another backup
                if not device.node_id and hasattr(interface, 'myInfo') and interface.myInfo and interface.myInfo.myNodeNum:
                    node_num = interface.myInfo.myNodeNum
                    node_id = f"!{node_num:08x}"
                    device.node_id = node_id
                    self.logger.info(f"Device {label} node ID: {device.node_id}")
            except Exception as e:
                self.logger.warning(f"Could not get node ID from {label}: {e}")
            
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
        
        # Re-subscribe with the callback if meshtastic is available
        if MESHTASTIC_AVAILABLE:
            try:
                pub.subscribe(self._OnMeshtasticPacket, "meshtastic.receive")
            except Exception as e:
                self.logger.warning(f"Could not subscribe to meshtastic.receive: {e}")
    
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
        # Check if this is an ACK/NAK via routing packet
        # ACKs come through regular meshtastic.receive with decoded.routing field
        packet_id = packet.get('id')
        
        if packet_id and 'decoded' in packet:
            decoded = packet.get('decoded', {})
            routing = decoded.get('routing', {})
            
            if routing:
                error_reason = routing.get('errorReason', 'NONE')
                self.logger.info(f"Routing packet received - id: {packet_id}, errorReason: '{error_reason}', pending: {list(self._pending_acks.keys())}")
                
                if packet_id in self._pending_acks:
                    if error_reason == 'NONE':
                        # ACK received
                        with self._ack_lock:
                            self._pending_acks[packet_id]['acked'] = True
                            self._pending_acks[packet_id]['event'].set()
                        self.logger.info(f"ACK matched for packet {packet_id}")
                    else:
                        # NAK received
                        with self._ack_lock:
                            self._pending_acks[packet_id]['event'].set()
                        self.logger.warning(f"NAK matched for packet {packet_id}: {error_reason}")
        
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
    
    def SendTextToNodeOnInterface(self, node_id: str, text: str, interface) -> bool:
        """
        Send a text message to a specific node on a specific interface.
        Simple retry-based delivery - no ACK tracking.
        
        Args:
            node_id: Destination node ID (can be !hexstring or plain hex)
            text: Message text to send
            interface: The interface to send on
            
        Returns:
            True if message was sent
        """
        max_retries = 3
        retry_delay = 0.2
        
        # Convert node_id to node number if needed
        dest_id = self._convertNodeId(node_id)
        
        # Find the device that has this interface
        for port, device in self.devices.items():
            if device.interface is interface:
                for attempt in range(max_retries):
                    try:
                        self.logger.info(f"Sending to {node_id} ({dest_id}) on {port} (attempt {attempt + 1}/{max_retries})")
                        # Send without wantAck - messages get through, just retry on failure
                        device.interface.sendText(text, destinationId=dest_id, wantAck=False)
                        self.logger.info(f"Sent to {node_id}")
                        return True
                    except Exception as e:
                        self.logger.warning(f"Send attempt {attempt + 1} failed: {e}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                
                self.logger.error(f"Failed to send to {node_id} after {max_retries} attempts")
                return False
        
        # Interface not found, try all devices
        self.logger.warning(f"Interface not found, trying all devices")
        return self.SendTextToNode(node_id, text)
    
    def _convertNodeId(self, node_id: str) -> str:
        """
        Convert node ID to format suitable for sendText.
        
        Args:
            node_id: Node ID in format !hexstring or plain hex
            
        Returns:
            Node ID suitable for meshtastic
        """
        # If starts with !, remove it
        if node_id.startswith('!'):
            return node_id[1:]
        return node_id
    
    def SendTextToNode(self, node_id: str, text: str) -> bool:
        """
        Send a text message to a specific node.
        
        Args:
            node_id: Destination node ID
            text: Message text to send
            
        Returns:
            True if message was sent
        """
        # Convert node_id to node number if needed
        dest_id = self._convertNodeId(node_id)
        
        for port, device in self.devices.items():
            if not device.connected or not device.interface:
                continue
            
            try:
                self.logger.info(f"Sending to {node_id} ({dest_id}) on {port}")
                device.interface.sendText(text, destinationId=dest_id, wantAck=False)
                self.logger.info(f"Sent to {node_id}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to send to {node_id}: {e}")
        
        return False
    
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
    
    def GetNodeIdForInterface(self, interface) -> Optional[str]:
        """
        Get the node ID for the device that received a packet.
        
        Args:
            interface: The interface that received the packet
            
        Returns:
            Node ID string, or None if not found
        """
        for port, device in self.devices.items():
            if device.interface is interface:
                return device.node_id
        return None
    
    def GetAllNodeIds(self) -> List[str]:
        """
        Get all node IDs for connected devices.
        
        Returns:
            List of node ID strings
        """
        return [d.node_id for d in self.devices.values() if d.node_id]
