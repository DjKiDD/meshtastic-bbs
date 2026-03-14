"""
Configuration Module

This module handles loading and parsing the YAML configuration file
that controls all aspects of the BBS server operation.

Purpose:
    - Load configuration from YAML file
    - Provide typed access to configuration values
    - Validate required configuration fields
    - Supply default values where appropriate

Key Classes:
    - Configuration: Main configuration object containing all settings
    - SerialDeviceConfig: Represents a single serial device entry
    - PluginConfig: Represents plugin-specific configuration

Usage:
    config = Configuration.LoadConfiguration("config.yaml")
    node_id = config.GetNodeId()
    serial_devices = config.GetSerialDevices()
"""

import yaml
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class SerialDeviceConfig:
    """
    Represents configuration for a single serial device.
    
    Attributes:
        port: The serial port path (e.g., /dev/ttyUSB0)
        label: A human-readable label for this device
        channel_index: Which channel to listen on (default: 0)
    """
    port: str
    label: Optional[str] = None
    channel_index: int = 0


@dataclass
class BbsConfig:
    """
    Configuration for the BBS node itself.
    
    Attributes:
        node_id: This BBS's unique node ID in Meshtastic format
        name: Human-readable name for the BBS
        description: Description shown in HELP command
    """
    node_id: str
    name: str = "MeshBBS"
    description: str = "Meshtastic Bulletin Board System"


@dataclass
class DatabaseConfig:
    """
    Configuration for the database connection.
    
    Attributes:
        path: Path to the SQLite database file
    """
    path: str = "/var/lib/meshtastic-bbs/bbs.db"


@dataclass
class LoggingConfig:
    """
    Configuration for logging output.
    
    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        file: Path to log file (None = stdout only)
        format: Log message format string
    """
    level: str = "INFO"
    file: Optional[str] = None
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class PluginSettings:
    """
    Configuration for plugins.
    
    Attributes:
        enabled: List of plugin names to load
        settings: Dictionary of plugin-specific settings
    """
    enabled: List[str] = field(default_factory=list)
    settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class Configuration:
    """
    Main configuration container that holds all BBS server settings.
    
    This class is populated from a YAML configuration file and provides
    typed access to all configuration values.
    
    Attributes:
        bbs: BBS node configuration
        serial: Serial device configuration
        database: Database configuration
        logging: Logging configuration
        plugins: Plugin configuration
    """
    bbs: BbsConfig = field(default_factory=lambda: BbsConfig(node_id=""))
    serial_devices: List[SerialDeviceConfig] = field(default_factory=list)
    database: DatabaseConfig = field(default_factory=lambda: DatabaseConfig())
    logging: LoggingConfig = field(default_factory=lambda: LoggingConfig())
    plugins: PluginSettings = field(default_factory=lambda: PluginSettings())

    @staticmethod
    def LoadConfiguration(config_path: str) -> 'Configuration':
        """
        Load configuration from a YAML file.
        
        This function reads the specified YAML file and parses it into
        a Configuration object with proper type validation.
        
        Args:
            config_path: Path to the YAML configuration file
            
        Returns:
            Configuration object with all settings loaded
            
        Raises:
            FileNotFoundError: If the config file doesn't exist
            yaml.YAMLError: If the YAML is malformed
            ValueError: If required fields are missing
        """
        # Check if file exists
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Read and parse YAML file
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        if raw_config is None:
            raise ValueError("Configuration file is empty")
        
        # Parse into Configuration object
        config = Configuration()
        
        # Parse BBS section (required)
        if 'bbs' in raw_config:
            bbs_data = raw_config['bbs']
            config.bbs = BbsConfig(
                node_id=bbs_data.get('node_id', '!bbs0001'),
                name=bbs_data.get('name', 'MeshBBS'),
                description=bbs_data.get('description', 'Meshtastic Bulletin Board System')
            )
        
        # Parse serial devices section
        if 'serial' in raw_config and 'devices' in raw_config['serial']:
            config.serial_devices = []
            for device in raw_config['serial']['devices']:
                config.serial_devices.append(SerialDeviceConfig(
                    port=device.get('port', ''),
                    label=device.get('label'),
                    channel_index=device.get('channel_index', 0)
                ))
        
        # Parse database section
        if 'database' in raw_config:
            db_data = raw_config['database']
            config.database = DatabaseConfig(
                path=db_data.get('path', '/var/lib/meshtastic-bbs/bbs.db')
            )
        
        # Parse logging section
        if 'logging' in raw_config:
            log_data = raw_config['logging']
            config.logging = LoggingConfig(
                level=log_data.get('level', 'INFO'),
                file=log_data.get('file'),
                format=log_data.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
        
        # Parse plugins section
        if 'plugins' in raw_config:
            plugin_data = raw_config['plugins']
            config.plugins = PluginSettings(
                enabled=plugin_data.get('enabled', []),
                settings=plugin_data.get('settings', {})
            )
        
        return config

    def GetNodeId(self) -> str:
        """
        Get the BBS node ID.
        
        Returns:
            The configured node ID string
        """
        return self.bbs.node_id

    def GetBbsName(self) -> str:
        """
        Get the BBS human-readable name.
        
        Returns:
            The configured BBS name
        """
        return self.bbs.name

    def GetBbsDescription(self) -> str:
        """
        Get the BBS description.
        
        Returns:
            The configured BBS description
        """
        return self.bbs.description

    def GetSerialDevices(self) -> List[SerialDeviceConfig]:
        """
        Get the list of configured serial devices.
        
        Returns:
            List of SerialDeviceConfig objects
        """
        return self.serial_devices

    def GetDatabasePath(self) -> str:
        """
        Get the database file path.
        
        Returns:
            Path to the SQLite database file
        """
        return self.database.path

    def GetLogLevel(self) -> str:
        """
        Get the logging level.
        
        Returns:
            Log level string (DEBUG, INFO, WARNING, ERROR)
        """
        return self.logging.level

    def GetLogFile(self) -> Optional[str]:
        """
        Get the log file path.
        
        Returns:
            Log file path or None if logging to stdout only
        """
        return self.logging.file

    def GetLogFormat(self) -> str:
        """
        Get the log format string.
        
        Returns:
            Log format string
        """
        return self.logging.format

    def GetEnabledPlugins(self) -> List[str]:
        """
        Get the list of enabled plugin names.
        
        Returns:
            List of plugin name strings
        """
        return self.plugins.enabled

    def GetPluginSettings(self, plugin_name: str) -> Dict[str, Any]:
        """
        Get configuration settings for a specific plugin.
        
        Args:
            plugin_name: Name of the plugin to get settings for
            
        Returns:
            Dictionary of plugin-specific settings, empty dict if none
        """
        return self.plugins.settings.get(plugin_name, {})

    def GetSerialDeviceCount(self) -> int:
        """
        Get the number of configured serial devices.
        
        Returns:
            Count of serial devices
        """
        return len(self.serial_devices)
