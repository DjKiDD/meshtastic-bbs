# Plugin Development Guide

This guide explains how to create new plugins for the Meshtastic BBS server.

## Overview

Plugins are the primary way to extend BBS functionality. Each plugin:
- Defines one or more commands
- Handles business logic for those commands
- Has access to the database and other services

## Creating a Plugin

### 1. Create the Plugin File

Create a new Python file in `bbs/plugins/builtin/` (for built-in plugins):

```python
# bbs/plugins/builtin/MyPlugin.py

from bbs.plugins.BasePlugin import BasePlugin, PluginContext
from bbs.protocol.CommandRouter import HandlerContext


class MyPlugin(BasePlugin):
    """
    My custom plugin that does something useful.
    """
    
    # Plugin metadata - REQUIRED
    Name = "my_plugin"
    Version = "1.0.0"
    Description = "Does something useful"
    
    # Command handlers - maps command names to methods
    CommandHandlers = {
        "MYCMD": HandleMyCommand,
        "ANOTHER": HandleAnotherCommand,
    }
    
    def OnLoad(self, context: PluginContext) -> None:
        """
        Called when plugin is loaded.
        
        Use this to initialize state and access config.
        """
        super().OnLoad(context)
        
        # Get plugin-specific config
        plugin_config = context.GetPluginConfiguration(self.Name)
        self.some_setting = plugin_config.get("some_setting", "default")
        
        self.logger.info(f"MyPlugin loaded with setting: {self.some_setting}")
    
    def GetHelpText(self) -> str:
        """
        Return help text for your commands.
        """
        return """
=== My Plugin ===

MYCMD <arg>
  Does something with the argument

ANOTHER
  Does another thing
"""


def HandleMyCommand(context: HandlerContext) -> str:
    """
    Handle the MYCMD command.
    
    Args:
        context: Handler context with arguments and services
        
    Returns:
        Response string to send back to user
    """
    # Access arguments
    if not context.arguments:
        return "Usage: MYCMD <argument>"
    
    argument = context.arguments[0]
    
    # Access database
    some_data = context.database.GetSomething()
    
    # Access config
    bbs_name = context.GetBbsName()
    
    # Send response
    return f"Processed: {argument} from {context.from_node}"


def HandleAnotherCommand(context: HandlerContext) -> str:
    """
    Handle the ANOTHER command.
    """
    return "Another command executed!"
```

### 2. Register the Plugin

The plugin will be auto-discovered when placed in `bbs/plugins/builtin/`.

To enable it, add to your `config.yaml`:

```yaml
plugins:
  enabled:
    - personal_messaging
    - bulletin_board
    - my_plugin  # Add your plugin here
```

### 3. Add Entry Point (for external plugins)

If creating an external plugin package, add to `pyproject.toml`:

```toml
[project.entry-points."meshtastic-bbs.plugins"]
my_plugin = "mypackage.mymodule:MyPlugin"
```

## Plugin Context

The `HandlerContext` object provides access to:

| Property | Type | Description |
|----------|------|-------------|
| `from_node` | str | Node ID of sender |
| `arguments` | List[str] | Command arguments |
| `database` | Database | Database instance |
| `configuration` | Configuration | Config instance |
| `serial_manager` | SerialManager | Serial manager |
| `plugin_manager` | PluginManager | Plugin manager |
| `logger` | Logger | Logger instance |

### Context Methods

```python
# Send a response back to the sender
context.SendResponse("Hello!")

# Get BBS info
bbs_name = context.GetBbsName()
bbs_node = context.GetBbsNodeId()
```

## Database Access

Plugins can access the database through `context.database`:

```python
# Register a node
context.database.RegisterNode(node_id, "Node Name")

# Get messages
messages = context.database.GetMessagesForNode(node_id)

# Save a message
message = Message(from_node="!1234", to_node="!5678", body="Hello")
context.database.SaveMessage(message)

# Get BBS areas
areas = context.database.GetAllAreas()

# Create BBS post
post = BbsPost(area_id=1, from_node="!1234", body="Post content")
context.database.SavePost(post)
```

## Adding Database Tables

If your plugin needs its own database tables, use the `Migrate` method:

```python
class MyPlugin(BasePlugin):
    Name = "my_plugin"
    # ...
    
    def Migrate(self, database: Database) -> None:
        """
        Create database tables for this plugin.
        """
        database.connection.execute("""
            CREATE TABLE IF NOT EXISTS my_plugin_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                data TEXT,
                created_at INTEGER
            )
        """)
        database.connection.commit()
```

## Best Practices

1. **Always validate input**: Check argument count and format
2. **Return helpful errors**: Tell users what went wrong
3. **Log important events**: Use `self.logger.info()` and `self.logger.error()`
4. **Keep commands simple**: Do one thing per command
5. **Document your commands**: Implement `GetHelpText()`
6. **Handle exceptions**: Don't let errors crash the server

## Example: Complete Plugin

Here's a complete example of a simple plugin:

```python
# bbs/plugins/builtin/Example.py

from bbs.plugins.BasePlugin import BasePlugin, PluginContext
from bbs.protocol.CommandRouter import HandlerContext
import time


class ExamplePlugin(BasePlugin):
    """Example plugin demonstrating plugin development."""
    
    Name = "example"
    Version = "1.0.0"
    Description = "Example plugin for developers"
    
    CommandHandlers = {
        "HELLO": HandleHello,
        "TIME": HandleTime,
        "COUNT": HandleCount,
    }
    
    def OnLoad(self, context: PluginContext) -> None:
        super().OnLoad(context)
        self.request_count = 0
    
    def GetHelpText(self) -> str:
        return """=== Example Plugin ===

HELLO [name]
  Say hello, optionally to a name
  
TIME
  Show current server time
  
COUNT
  Show request count
"""


def HandleHello(context: HandlerContext) -> str:
    """Handle the HELLO command."""
    if context.arguments:
        name = context.arguments[0]
        return f"Hello, {name}!"
    return f"Hello from {context.GetBbsName()}!"


def HandleTime(context: HandlerContext) -> str:
    """Handle the TIME command."""
    import datetime
    now = datetime.datetime.now()
    return f"Server time: {now.strftime('%Y-%m-%d %H:%M:%S')}"


def HandleCount(context: HandlerContext) -> str:
    """Handle the COUNT command."""
    plugin = context.plugin_manager.GetPlugin("example")
    if plugin:
        plugin.request_count += 1
        return f"Requests handled: {plugin.request_count}"
    return "Error: Plugin not found"
```

## Testing Plugins

You can test your plugin by:

1. Starting the BBS server with your plugin enabled
2. Sending commands via Meshtastic
3. Checking the logs for errors

```bash
# Run with debug logging
# Edit config.yaml and set logging.level to DEBUG

python -m bbs.Application
```

## Next Steps

- Look at existing plugins in `bbs/plugins/builtin/` for examples
- Check the Database.py for available database methods
- Read the CommandRouter.py to understand command flow
