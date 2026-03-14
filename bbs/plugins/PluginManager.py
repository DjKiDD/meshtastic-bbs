"""
Plugin Manager Module

This module handles plugin discovery, loading, and lifecycle management.

Purpose:
    - Discover plugins from multiple sources
    - Load and initialize plugins
    - Manage plugin lifecycle (load/unload)
    - Provide plugin lookup functionality

Key Classes:
    - PluginManager: Manages all plugins

Plugin Sources:
    1. Built-in plugins (included with BBS)
    2. External plugins (installed via entry points)
    3. Local plugins (in plugins/ directory)

Usage:
    manager = PluginManager(context)
    manager.LoadEnabledPlugins(["personal_messaging", "bulletin_board"])
    plugin = manager.GetPlugin("personal_messaging")
"""

import logging
import importlib
from typing import Dict, List, Optional, Type

from bbs.plugins.BasePlugin import BasePlugin, PluginContext
from bbs.Logger import GetLogger


class PluginManager:
    """
    Manages the plugin lifecycle for the BBS server.
    
    This class is responsible for:
    - Discovering available plugins
    - Loading enabled plugins
    - Managing plugin state
    - Providing plugin lookup
    
    Attributes:
        context: PluginContext shared with all plugins
        plugins: Dict of loaded plugins by name
    """
    
    def __init__(self, context: PluginContext):
        """
        Initialize the plugin manager.
        
        Args:
            context: PluginContext to pass to plugins
        """
        self.context = context
        self.logger = GetLogger("PluginManager")
        self.plugins: Dict[str, BasePlugin] = {}
    
    def LoadEnabledPlugins(self, enabled_list: List[str]) -> None:
        """
        Load all plugins listed as enabled in configuration.
        
        This function:
        - First loads built-in plugins
        - Then loads external plugins from entry points
        - Filters to only enabled plugins
        
        Args:
            enabled_list: List of plugin names to load
        """
        # Get all available plugins
        all_plugins = self._DiscoverAllPlugins()
        
        # Load enabled plugins
        for plugin_name in enabled_list:
            if plugin_name in all_plugins:
                self._LoadPlugin(all_plugins[plugin_name])
            else:
                self.logger.warning(f"Plugin '{plugin_name}' not found")
    
    def _DiscoverAllPlugins(self) -> Dict[str, Type[BasePlugin]]:
        """
        Discover all available plugins from all sources.
        
        Returns:
            Dict mapping plugin names to their classes
            
        Note:
            This combines built-in and external plugins.
        """
        all_plugins: Dict[str, Type[BasePlugin]] = {}
        
        # Discover built-in plugins
        builtin_plugins = self._DiscoverBuiltInPlugins()
        all_plugins.update(builtin_plugins)
        
        # Discover external plugins via entry points
        external_plugins = self._DiscoverExternalPlugins()
        all_plugins.update(external_plugins)
        
        return all_plugins
    
    def _DiscoverBuiltInPlugins(self) -> Dict[str, Type[BasePlugin]]:
        """
        Discover built-in plugins.
        
        Returns:
            Dict mapping plugin names to their classes
        """
        plugins: Dict[str, Type[BasePlugin]] = {}
        
        # Import and register built-in plugins
        try:
            from bbs.plugins.builtin.PersonalMessaging import PersonalMessagingPlugin
            plugins[PersonalMessagingPlugin.Name] = PersonalMessagingPlugin
        except ImportError as e:
            self.logger.warning(f"Failed to import PersonalMessaging plugin: {e}")
        
        try:
            from bbs.plugins.builtin.BulletinBoard import BulletinBoardPlugin
            plugins[BulletinBoardPlugin.Name] = BulletinBoardPlugin
        except ImportError as e:
            self.logger.warning(f"Failed to import BulletinBoard plugin: {e}")
        
        self.logger.debug(f"Discovered built-in plugins: {list(plugins.keys())}")
        
        return plugins
    
    def _DiscoverExternalPlugins(self) -> Dict[str, Type[BasePlugin]]:
        """
        Discover external plugins via entry points.
        
        Returns:
            Dict mapping plugin names to their classes
            
        Note:
            External plugins can be installed via pip and register
            themselves using entry points in their setup.py/pyproject.toml.
        """
        plugins: Dict[str, Type[BasePlugin]] = {}
        
        # Try to load plugins via entry points
        try:
            # Python 3.10+ syntax
            if hasattr(importlib.metadata, 'entry_points'):
                eps = importlib.metadata.entry_points()
                if hasattr(eps, 'select'):
                    plugin_eps = eps.select(group='meshtastic-bbs.plugins')
                else:
                    plugin_eps = eps.get('meshtastic-bbs.plugins', [])
            else:
                # Python 3.9 and earlier
                import importlib_metadata
                plugin_eps = importlib_metadata.entry_points().get('meshtastic-bbs.plugins', [])
            
            for ep in plugin_eps:
                try:
                    plugin_class = ep.load()
                    plugins[ep.name] = plugin_class
                    self.logger.debug(f"Discovered external plugin: {ep.name}")
                except Exception as e:
                    self.logger.warning(f"Failed to load plugin '{ep.name}': {e}")
                    
        except Exception as e:
            self.logger.debug(f"No external plugins found or entry points not available: {e}")
        
        return plugins
    
    def _LoadPlugin(self, plugin_class: Type[BasePlugin]) -> bool:
        """
        Load a single plugin class.
        
        Args:
            plugin_class: The plugin class to instantiate and load
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Instantiate the plugin
            plugin = plugin_class()
            
            # Call OnLoad with context
            plugin.OnLoad(self.context)
            
            # Store in plugins dict
            self.plugins[plugin.GetName()] = plugin
            
            self.logger.info(f"Loaded plugin: {plugin.GetName()} v{plugin.GetVersion()}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_class.Name}: {e}")
            return False
    
    def GetPlugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """
        Get a loaded plugin by name.
        
        Args:
            plugin_name: Name of the plugin to retrieve
            
        Returns:
            Plugin instance if loaded, None otherwise
        """
        return self.plugins.get(plugin_name)
    
    def GetAllPlugins(self) -> Dict[str, BasePlugin]:
        """
        Get all loaded plugins.
        
        Returns:
            Dict mapping plugin names to plugin instances
        """
        return self.plugins
    
    def GetLoadedPluginNames(self) -> List[str]:
        """
        Get list of names of all loaded plugins.
        
        Returns:
            List of plugin names
        """
        return list(self.plugins.keys())
    
    def GetCommandHandlers(self) -> Dict[str, callable]:
        """
        Get all command handlers from all loaded plugins.
        
        Returns:
            Dict mapping command names to handler methods
        """
        handlers: Dict[str, callable] = {}
        
        for plugin_name, plugin in self.plugins.items():
            plugin_handlers = plugin.GetCommandHandlers()
            handlers.update(plugin_handlers)
        
        return handlers
    
    def UnloadAll(self) -> None:
        """
        Unload all plugins.
        
        This calls OnUnload for each plugin and clears the plugins dict.
        """
        for plugin_name, plugin in self.plugins.items():
            try:
                plugin.OnUnload()
            except Exception as e:
                self.logger.error(f"Error unloading plugin '{plugin_name}': {e}")
        
        self.plugins.clear()
        self.logger.info("All plugins unloaded")
    
    def ReloadPlugin(self, plugin_name: str) -> bool:
        """
        Reload a specific plugin.
        
        Args:
            plugin_name: Name of the plugin to reload
            
        Returns:
            True if reloaded successfully, False otherwise
        """
        # Unload existing plugin if any
        if plugin_name in self.plugins:
            self.plugins[plugin_name].OnUnload()
            del self.plugins[plugin_name]
        
        # Find the plugin class
        all_plugins = self._DiscoverAllPlugins()
        
        if plugin_name not in all_plugins:
            self.logger.error(f"Cannot reload: plugin '{plugin_name}' not found")
            return False
        
        # Load the plugin
        return self._LoadPlugin(all_plugins[plugin_name])
    
    def RunMigrations(self) -> None:
        """
        Run migrations for all loaded plugins.
        
        This is called during database initialization to allow
        plugins to set up their database tables/columns.
        """
        for plugin_name, plugin in self.plugins.items():
            try:
                plugin.Migrate(self.context.Database)
                self.logger.debug(f"Ran migrations for plugin: {plugin_name}")
            except Exception as e:
                self.logger.error(f"Migration failed for plugin '{plugin_name}': {e}")
    
    def GetAllHelpText(self) -> str:
        """
        Get combined help text from all plugins.
        
        Returns:
            Formatted help string
        """
        lines = [
            "================================",
            "Meshtastic BBS - Available Commands",
            "================================",
            "",
        ]
        
        for plugin_name, plugin in self.plugins.items():
            help_text = plugin.GetHelpText()
            if help_text:
                lines.append(help_text)
                lines.append("")
        
        return "\n".join(lines)
