# Meshtastic BBS Server

A lightweight BBS (Bulletin Board System) server for multiple Meshtastic nodes, designed to run on Raspberry Pi Zero W2.

## Features

- **Personal Messaging**: Send and receive personal messages between mesh nodes
- **Bulletin Board System**: Public message boards organized by areas
- **Extensible Plugin System**: Easy to add new commands and features
- **Multiple Serial Devices**: Connect to multiple Meshtastic devices
- **SQLite Database**: Lightweight storage for messages and posts
- **Human-Readable Code**: Easy to understand and modify

## Installation

```bash
# Clone or download this repository
cd meshtastic-bbs

# Install dependencies
pip install -r requirements.txt

# Copy example config
cp config.example.yaml config.yaml

# Edit configuration
nano config.yaml
```

## Configuration

Edit `config.yaml` to configure:

- BBS node ID and name
- Serial device ports
- Database location
- Logging settings
- Enabled plugins

## Running the BBS

```bash
# Run with default config
python -m bbs.Application

# Or specify a config file
python -m bbs.Application config.yaml
```

## Commands

### Personal Messaging

| Command | Description | Example |
|---------|-------------|---------|
| `MSG <node> <text>` | Send personal message | `MSG !abcd1234 Hello!` |
| `READ` | List your messages | `READ` |
| `READ <id>` | Read specific message | `READ 5` |
| `DELETE <id>` | Delete message | `DELETE 5` |

### Bulletin Board

| Command | Description | Example |
|---------|-------------|---------|
| `BBS <area> <text>` | Post to area | `BBS general Hello!` |
| `AREAS` | List all areas | `AREAS` |
| `READ <area>` | Read posts in area | `READ general` |

### General

| Command | Description |
|---------|-------------|
| `HELP` | Show help |
| `PING` | Check if BBS is online |

## Developing Plugins

See [PLUGIN_DEVELOPMENT.md](docs/PLUGIN_DEVELOPMENT.md) for detailed instructions.

## Project Structure

```
meshtastic-bbs/
├── bbs/
│   ├── Application.py       # Main entry point
│   ├── Configuration.py     # Config loading
│   ├── Database.py          # SQLite wrapper
│   ├── Logger.py            # Logging setup
│   ├── SerialManager.py     # Serial device management
│   ├── protocol/            # Command parsing and routing
│   └── plugins/             # Plugin system
│       ├── BasePlugin.py    # Base class for plugins
│       ├── PluginManager.py # Plugin loading
│       └── builtin/         # Built-in plugins
├── config.example.yaml      # Example config
├── requirements.txt         # Dependencies
└── pyproject.toml           # Package config
```

## License

MIT License
