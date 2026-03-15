"""
Zork - Text Adventure Game Plugin

A faithful recreation of Zork I for Meshtastic BBS.
Implements the classic Infocom text adventure with full world,
items, puzzles, and scoring system.
"""

import random
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from bbs.plugins.BasePlugin import BasePlugin, PluginContext
from bbs.protocol.CommandRouter import HandlerContext

import logging


# =============================================================================
# ROOM DEFINITIONS
# =============================================================================

ROOMS = {
    # === HOUSE EXTERIOR ===
    "west_of_house": {
        "name": "West of House",
        "description": "You are standing in an open field west of a white house, with a boarded front door. There is a forest to the west.",
        "exits": {"north": "north_of_house", "south": "south_of_house", "west": "forest_1"},
        "items": [],
        "dark": False,
    },
    "north_of_house": {
        "name": "North of House", 
        "description": "You are standing at the north end of the house. The front door is boarded. There are windows on the north face.",
        "exits": {"south": "west_of_house", "west": "forest_2", "east": "east_of_house"},
        "items": [],
        "dark": False,
    },
    "south_of_house": {
        "name": "South of House",
        "description": "You are standing at the south end of the house. The front door is boarded.",
        "exits": {"north": "west_of_house", "west": "forest_3", "south": "clearing"},
        "items": [],
        "dark": False,
    },
    "east_of_house": {
        "name": "East of House",
        "description": "You are standing behind the white house. A kitchen window is open.",
        "exits": {"west": "north_of_house", "south": "behind_house", "east": "clearing"},
        "items": [],
        "dark": False,
    },
    "behind_house": {
        "name": "Behind House",
        "description": "You are behind the white house. To the east is a small clearing.",
        "exits": {"north": "east_of_house", "east": "clearing"},
        "items": [],
        "dark": False,
    },
    "stone_barrow": {
        "name": "Stone Barrow",
        "description": "You are standing in front of a massive stone barrow. A heavy stone door is set into the ground.",
        "exits": {"southwest": "west_of_house"},
        "items": [],
        "dark": False,
        "locked": True,
        "key": "brass_key",
    },
    
    # === FOREST ===
    "forest_1": {
        "name": "Forest",
        "description": "You are in a dense forest. Paths lead east and south.",
        "exits": {"east": "west_of_house", "south": "forest_2"},
        "items": [],
        "dark": False,
    },
    "forest_2": {
        "name": "Forest",
        "description": "You are in a forest. Paths lead north, south, and east.",
        "exits": {"north": "forest_1", "south": "forest_3", "east": "north_of_house"},
        "items": [],
        "dark": False,
    },
    "forest_3": {
        "name": "Forest",
        "description": "You are in a forest. Paths lead north and east.",
        "exits": {"north": "forest_2", "east": "south_of_house"},
        "items": [],
        "dark": False,
    },
    "clearing": {
        "name": "Clearing",
        "description": "You are in a small clearing. A path leads north to the house, and a trail leads southeast.",
        "exits": {"north": "behind_house", "southwest": "south_of_house", "northwest": "east_of_house"},
        "items": [],
        "dark": False,
    },
    "grating_clearing": {
        "name": "Grating Clearing",
        "description": "You are in a small clearing. A rusty metal grating is set into the ground, leading down.",
        "exits": {"south": "clearing"},
        "items": [],
        "dark": False,
    },
    "path": {
        "name": "Forest Path",
        "description": "A forest path. There is a large tree here that can be climbed.",
        "exits": {"south": "grating_clearing", "up": "up_a_tree"},
        "items": [],
        "dark": False,
    },
    "up_a_tree": {
        "name": "Up a Tree",
        "description": "You are high in a tree. A bird's nest is visible in the branches.",
        "exits": {"down": "path"},
        "items": ["jeweled_egg"],
        "dark": False,
    },
    
    # === HOUSE INTERIOR ===
    "kitchen": {
        "name": "Kitchen",
        "description": "You are in a small kitchen. A table holds some food. A bottle of water is here.",
        "exits": {"west": "living_room", "up": "attic"},
        "items": ["bottle", "food"],
        "dark": False,
    },
    "living_room": {
        "name": "Living Room",
        "description": "You are in a living room. A trophy case stands against one wall. A heavy rug covers the floor. An old sword hangs on the wall. A brass lamp sits on a table.",
        "exits": {"east": "kitchen", "down": "cellar"},
        "items": ["sword", "brass_lamp", "trophy_case"],
        "dark": False,
    },
    "attic": {
        "name": "Attic",
        "description": "You are in a dark attic. A rope hangs from the ceiling.",
        "exits": {"down": "kitchen"},
        "items": ["rope", "knife"],
        "dark": True,
    },
    
    # === UNDERGROUND ===
    "cellar": {
        "name": "Cellar",
        "description": "You are in a dusty cellar. The exit leads up.",
        "exits": {"up": "living_room", "east": "troll_room"},
        "items": [],
        "dark": True,
        "need_lamp": True,
    },
    "troll_room": {
        "name": "Troll Room",
        "description": "You are in a large room. Passages lead east and west. A massive troll blocks the eastern passage.",
        "exits": {"west": "cellar", "east": "east_west_passage", "south": "maze_1"},
        "items": [],
        "dark": False,
        "troll": True,
    },
    "east_west_passage": {
        "name": "East-West Passage",
        "description": "You are in a narrow passage running east and west.",
        "exits": {"west": "troll_room", "east": "round_room"},
        "items": [],
        "dark": False,
    },
    "round_room": {
        "name": "Round Room",
        "description": "You are in a circular room. Exits lead in many directions. The room is remarkably声.",
        "exits": {"west": "east_west_passage", "north": "loud_room", "south": "mirror_room_1", "east": "gallery"},
        "items": [],
        "dark": False,
    },
    "gallery": {
        "name": "Gallery",
        "description": "You are in an art gallery. Most of the paintings have been stolen.",
        "exits": {"west": "round_room", "north": "studio"},
        "items": ["painting"],
        "dark": False,
    },
    "studio": {
        "name": "Studio",
        "description": "You are in an artist's studio. An empty canvas sits on an easel.",
        "exits": {"south": "gallery"},
        "items": [],
        "dark": False,
    },
    "loud_room": {
        "name": "Loud Room",
        "description": "You are in a room with strange acoustic properties. Sounds echo loudly here.",
        "exits": {"south": "round_room"},
        "items": ["platinum_bar"],
        "dark": False,
    },
    "mirror_room_1": {
        "name": "Mirror Room",
        "description": "You are in a maze of mirrored passages. The reflections make navigation difficult.",
        "exits": {"north": "round_room", "south": "mirror_room_2"},
        "items": [],
        "dark": False,
    },
    "mirror_room_2": {
        "name": "Mirror Room",
        "description": "You are in a maze of mirrored passages.",
        "exits": {"north": "mirror_room_1", "east": "maze_2"},
        "items": [],
        "dark": False,
    },
    
    # === MAZE ===
    "maze_1": {
        "name": "Maze",
        "description": "You are in a twisty maze of passages. The exits lead in many directions.",
        "exits": {"north": "troll_room", "south": "maze_2", "east": "maze_3"},
        "items": [],
        "dark": False,
    },
    "maze_2": {
        "name": "Maze",
        "description": "You are in a twisty maze of passages.",
        "exits": {"north": "maze_1", "west": "mirror_room_2", "south": "maze_4"},
        "items": [],
        "dark": False,
    },
    "maze_3": {
        "name": "Maze",
        "description": "You are in a twisty maze of passages.",
        "exits": {"west": "maze_1", "east": "maze_4"},
        "items": [],
        "dark": False,
    },
    "maze_4": {
        "name": "Maze",
        "description": "You are in a dead end of the maze.",
        "exits": {"north": "maze_2", "west": "maze_3"},
        "items": [],
        "dark": False,
    },
    "maze_5": {
        "name": "Maze",
        "description": "You are in a twisty maze. A skeleton lies in the corner.",
        "exits": {"west": "maze_1", "north": "maze_11"},
        "items": ["bag_of_coins"],
        "dark": False,
    },
    "maze_11": {
        "name": "Maze",
        "description": "You are in a twisty maze.",
        "exits": {"south": "maze_5", "up": "grating_room"},
        "items": [],
        "dark": False,
    },
    "grating_room": {
        "name": "Grating Room",
        "description": "You are in a small room beneath a metal grating. The grate leads up to the surface.",
        "exits": {"down": "maze_11"},
        "items": [],
        "dark": True,
    },
    
    # === CYCLOPS AREA ===
    "maze_15": {
        "name": "Maze",
        "description": "You are in a twisty maze.",
        "exits": {"north": "maze_1", "east": "cyclops_room"},
        "items": [],
        "dark": False,
    },
    "cyclops_room": {
        "name": "Cyclops Room",
        "description": "You are in a large room. A massive cyclops sleeps in the corner. An eastern passage is blocked by a stone wall.",
        "exits": {"west": "maze_15", "east": "treasure_room"},
        "items": [],
        "dark": False,
        "cyclops": True,
    },
    "treasure_room": {
        "name": "Treasure Room",
        "description": "You are in a room filled with treasures!",
        "exits": {"west": "cyclops_room"},
        "items": ["silver_chalice"],
        "dark": False,
    },
    
    # === RESERVOIR AREA ===
    "reservoir_south": {
        "name": "Reservoir South",
        "description": "You are standing on the shore of a large reservoir. The water stretches to the north.",
        "exits": {"north": "reservoir_north", "south": "dam"},
        "items": [],
        "dark": False,
    },
    "reservoir_north": {
        "name": "Reservoir North",
        "description": "You are on the north shore of the reservoir.",
        "exits": {"south": "reservoir_south"},
        "items": [],
        "dark": False,
    },
    "dam": {
        "name": "Dam",
        "description": "You are at a flood control dam. A control panel has a large wheel.",
        "exits": {"north": "reservoir_south", "south": "dam"},
        "items": ["wrench"],
        "dark": False,
    },
    "atlantis": {
        "name": "Atlantis",
        "description": "You are in an underwater room. The water glows with an eerie light.",
        "exits": {"north": "reservoir_north"},
        "items": ["crystal_trident"],
        "dark": True,
    },
    
    # === TEMPLE AREA ===
    "south_temple": {
        "name": "South Temple",
        "description": "You are in the south end of an ancient temple. An altar stands against the north wall. Candles flicker nearby.",
        "exits": {"north": "north_temple"},
        "items": ["black_book", "candle"],
        "dark": False,
    },
    "north_temple": {
        "name": "North Temple",
        "description": "You are in the north end of the temple. A brass bell hangs from the ceiling.",
        "exits": {"south": "south_temple"},
        "items": ["brass_bell"],
        "dark": False,
    },
    "land_of_living_dead": {
        "name": "Land of the Living Dead",
        "description": "You are in a terrifying realm of ghosts and spirits. They float all around you!",
        "exits": {"south": "north_temple"},
        "items": ["crystal_skull"],
        "dark": True,
    },
    
    # === HADES ===
    "entrance_to_hades": {
        "name": "Entrance to Hades",
        "description": "You stand before the entrance to the Land of the Dead. A fearsome guardian blocks the way.",
        "exits": {"west": "round_room", "east": "land_of_living_dead"},
        "items": [],
        "dark": False,
    },
}


# =============================================================================
# ITEM DEFINITIONS
# =============================================================================

ITEMS = {
    # Treasures
    "jeweled_egg": {
        "name": "Jeweled Egg",
        "description": "A beautiful jewel-encrusted egg. It seems to contain something inside.",
        "take_points": 5,
        "treasure": True,
    },
    "painting": {
        "name": "Beautiful Painting",
        "description": "A valuable painting from the gallery.",
        "take_points": 4,
        "treasure": True,
    },
    "platinum_bar": {
        "name": "Platinum Bar",
        "description": "A heavy bar of pure platinum.",
        "take_points": 10,
        "treasure": True,
    },
    "silver_chalice": {
        "name": "Silver Chalice",
        "description": "An ornate silver chalice.",
        "take_points": 10,
        "treasure": True,
    },
    "crystal_trident": {
        "name": "Crystal Trident",
        "description": "A trident made of crystal.",
        "take_points": 4,
        "treasure": True,
    },
    "crystal_skull": {
        "name": "Crystal Skull",
        "description": "A glowing crystal skull.",
        "take_points": 10,
        "treasure": True,
    },
    "bag_of_coins": {
        "name": "Bag of Coins",
        "description": "A heavy bag of gold coins.",
        "take_points": 10,
        "treasure": True,
    },
    
    # Tools and Items
    "brass_lamp": {
        "name": "Brass Lamp",
        "description": "A brass lamp that provides light.",
        "take_points": 0,
        "treasure": False,
    },
    "brass_key": {
        "name": "Brass Key",
        "description": "A small brass key.",
        "take_points": 0,
        "treasure": False,
    },
    "silver_key": {
        "name": "Silver Key",
        "description": "A silver key.",
        "take_points": 0,
        "treasure": False,
    },
    "sword": {
        "name": "Sword",
        "description": "A rusty old sword.",
        "take_points": 0,
        "treasure": False,
    },
    "rope": {
        "name": "Rope",
        "description": "A length of rope.",
        "take_points": 0,
        "treasure": False,
    },
    "knife": {
        "name": "Knife",
        "description": "A sharp knife.",
        "take_points": 0,
        "treasure": False,
    },
    "wrench": {
        "name": "Wrench",
        "description": "A large wrench.",
        "take_points": 0,
        "treasure": False,
    },
    "screwdriver": {
        "name": "Screwdriver",
        "description": "A screwdriver.",
        "take_points": 0,
        "treasure": False,
    },
    "bottle": {
        "name": "Bottle",
        "description": "A clear glass bottle.",
        "take_points": 0,
        "treasure": False,
    },
    "food": {
        "name": "Food",
        "description": "Some food.",
        "take_points": 0,
        "treasure": False,
    },
    "trophy_case": {
        "name": "Trophy Case",
        "description": "A trophy case for displaying treasures.",
        "take_points": 0,
        "treasure": False,
        "fixed": True,
    },
    "black_book": {
        "name": "Black Book",
        "description": "A mysterious black book.",
        "take_points": 0,
        "treasure": False,
    },
    "candle": {
        "name": "Candle",
        "description": "A wax candle.",
        "take_points": 0,
        "treasure": False,
    },
    "brass_bell": {
        "name": "Brass Bell",
        "description": "A brass bell.",
        "take_points": 0,
        "treasure": False,
    },
}


# =============================================================================
# GAME STATE
# =============================================================================

class ZorkGameState:
    """Manages the game state for a single player."""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.location = "west_of_house"
        self.inventory: List[str] = []
        self.score = 0
        self.turns = 0
        self.game_over = False
        self.victory = False
        
        # Puzzle flags
        self.flags = {
            "troll_defeated": False,
            "window_open": False,
            "door_unlocked": False,
            "cyclops_asleep": False,
            "lamp_on": False,
        }
    
    def GetDescription(self) -> str:
        """Get the current room description."""
        room = ROOMS.get(self.location)
        if not room:
            return "You are lost!"
        
        desc = f"[{room['name']}]\n{room['description']}"
        
        # Show items in room
        if room.get('items'):
            item_names = [ITEMS[i]['name'] for i in room['items'] if i in ITEMS]
            if item_names:
                desc += f"\nYou see: {', '.join(item_names)}"
        
        # Show exits
        exits = list(room.get('exits', {}).keys())
        if exits:
            desc += f"\nExits: {', '.join(exits)}"
        
        return desc
    
    def Move(self, direction: str) -> str:
        """Try to move in a direction."""
        room = ROOMS.get(self.location)
        if not room:
            return "You are lost!"
        
        # Handle short directions
        direction_map = {
            'n': 'north', 's': 'south', 'e': 'east', 'w': 'west',
            'u': 'up', 'd': 'down', 'north': 'north', 'south': 'south',
            'east': 'east', 'west': 'west', 'up': 'up', 'down': 'down'
        }
        direction = direction_map.get(direction.lower(), direction.lower())
        
        if direction not in room.get('exits', {}):
            return "You can't go that way."
        
        # Check if exit is blocked
        new_location = room['exits'][direction]
        
        # Check troll
        if self.location == "troll_room" and direction == "east" and not self.flags["troll_defeated"]:
            return "The troll blocks your path! You must deal with him first."
        
        # Check darkness
        target_room = ROOMS.get(new_location)
        if target_room and target_room.get('dark') and not self.flags.get('lamp_on'):
            if 'brass_lamp' not in self.inventory:
                return "It's too dark to go that way."
        
        self.location = new_location
        self.turns += 1
        return self.GetDescription()
    
    def Take(self, item_name: str) -> str:
        """Try to take an item."""
        # Find item in current room
        room = ROOMS.get(self.location)
        if not room:
            return "You can't do that here."
        
        # Match item name
        item_id = None
        for i in room.get('items', []):
            if ITEMS[i]['name'].lower() == item_name.lower():
                item_id = i
                break
        
        if not item_id:
            return "You don't see that here."
        
        # Check if item is fixed
        if ITEMS[item_id].get('fixed'):
            return "You can't take that."
        
        # Remove from room, add to inventory
        room['items'].remove(item_id)
        self.inventory.append(item_id)
        
        # Award points for treasure
        if ITEMS[item_id].get('treasure'):
            points = ITEMS[item_id].get('take_points', 0)
            self.score += points
            return f" taken. ({points} points)"
        
        return " taken."
    
    def Drop(self, item_name: str) -> str:
        """Try to drop an item."""
        # Match item in inventory
        item_id = None
        for i in self.inventory:
            if ITEMS[i]['name'].lower() == item_name.lower():
                item_id = i
                break
        
        if not item_id:
            return "You're not carrying that."
        
        # Remove from inventory, add to room
        self.inventory.remove(item_id)
        room = ROOMS.get(self.location)
        if room:
            room['items'].append(item_id)
        
        return " dropped."
    
    def Examine(self, item_name: str) -> str:
        """Examine an item."""
        # Check inventory first
        for i in self.inventory:
            if ITEMS[i]['name'].lower() == item_name.lower():
                return ITEMS[i]['description']
        
        # Check room
        room = ROOMS.get(self.location)
        if room:
            for i in room.get('items', []):
                if ITEMS[i]['name'].lower() == item_name.lower():
                    return ITEMS[i]['description']
        
        return "You don't see that."
    
    def Inventory(self) -> str:
        """Show inventory."""
        if not self.inventory:
            return "You are empty-handed."
        
        names = [ITEMS[i]['name'] for i in self.inventory]
        return "You are carrying:\n" + "\n".join(f"  {n}" for n in names)
    
    def Attack(self, target: str) -> str:
        """Attack something."""
        if target == "troll" and self.location == "troll_room":
            if 'sword' in self.inventory:
                self.flags["troll_defeated"] = True
                self.score += 5
                self.inventory.remove('sword')
                return "You swing the sword! The troll falls! (5 points)"
            else:
                return "You have no weapon!"
        
        if target == "cyclops" and self.location == "cyclops_room":
            return "Attacking the cyclops would be suicidal!"
        
        return "There's nothing to attack here."
    
    def Open(self, target: str) -> str:
        """Open something."""
        if target == "door" and self.location == "stone_barrow":
            if self.flags.get("door_unlocked"):
                return "The door is already open."
            if 'brass_key' in self.inventory:
                self.flags["door_unlocked"] = True
                return "You unlock the stone door. It reveals a dark passage!"
            return "You need a key."
        
        if target == "window" and self.location == "east_of_house":
            self.flags["window_open"] = not self.flags["window_open"]
            return "You open the window." if self.flags["window_open"] else "You close the window."
        
        return "You can't open that."
    
    def Use(self, item: str) -> str:
        """Use an item."""
        if item == "lamp" or item == "brass lamp":
            if 'brass_lamp' in self.inventory:
                self.flags["lamp_on"] = not self.flags["lamp_on"]
                return "The lamp is now on." if self.flags["lamp_on"] else "The lamp is now off."
            return "You don't have the lamp."
        
        if item == "wrench" and self.location == "dam":
            self.flags["dam_drained"] = True
            return "You turn the wheel. The water level begins to drop!"
        
        return "You can't use that here."


# Active games per node
active_games: Dict[str, ZorkGameState] = {}


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def HandleZorkCommand(context: HandlerContext) -> str:
    """Main handler for Zork commands."""
    args = context.arguments
    
    # Initialize game if needed
    if context.from_node not in active_games:
        active_games[context.from_node] = ZorkGameState(context.from_node)
    
    game = active_games[context.from_node]
    
    if game.game_over:
        return f"Game over! Score: {game.score}. Type ZORK to start new game."
    
    if not args or args[0].upper() in ("ZORK", "START", "NEW"):
        return game.GetDescription()
    
    cmd = args[0].upper()
    rest = " ".join(args[1:]) if len(args) > 1 else ""
    
    # Movement commands
    if cmd in ("N", "NORTH", "S", "SOUTH", "E", "EAST", "W", "WEST", "U", "UP", "D", "DOWN", "GO", "WALK"):
        direction = cmd if cmd in ("N", "S", "E", "W", "U", "D") else rest
        if direction:
            return game.Move(direction)
        return "Go where?"
    
    # Look
    if cmd in ("LOOK", "L", "EXAMINE", "X"):
        if rest:
            return game.Examine(rest)
        return game.GetDescription()
    
    # Take
    if cmd in ("TAKE", "GET", "GRAB"):
        if not rest:
            return "Take what?"
        result = game.Take(rest)
        return f"{ITEMS.get(game.inventory[-1], {}).get('name', 'Item')}{result}" if result.endswith(" taken.") else result
    
    # Drop
    if cmd == "DROP":
        if not rest:
            return "Drop what?"
        return f"{rest}{game.Drop(rest)}"
    
    # Inventory
    if cmd in ("INVENTORY", "I", "INV"):
        return game.Inventory()
    
    # Attack
    if cmd in ("ATTACK", "KILL", "FIGHT"):
        return game.Attack(rest)
    
    # Open
    if cmd == "OPEN":
        if not rest:
            return "Open what?"
        return game.Open(rest)
    
    # Use
    if cmd == "USE":
        if not rest:
            return "Use what?"
        return game.Use(rest)
    
    # Score
    if cmd == "SCORE":
        return f"Score: {game.score}/350\nTurns: {game.turns}"
    
    # Quit
    if cmd in ("QUIT", "ABANDON"):
        del active_games[context.from_node]
        return "Game abandoned. Type ZORK to start a new game."
    
    # Help
    if cmd == "HELP":
        return """Zork Commands:
GO [direction] - Move (N/S/E/W/U/D)
LOOK - Describe room
TAKE <item> - Pick up item
DROP <item> - Drop item
EXAMINE <item> - Inspect item
INVENTORY - Check items
OPEN <thing> - Open door/window
USE <item> - Use item
ATTACK <target> - Fight
SCORE - View score
QUIT - Abandon game"""
    
    return f"I don't understand '{cmd}'. Type HELP for commands."


# =============================================================================
# PLUGIN DEFINITION
# =============================================================================

class ZorkPlugin(BasePlugin):
    """
    Zork - Text Adventure Game Plugin
    
    A faithful recreation of the classic Infocom game Zork I,
    adapted for Meshtastic BBS with truncated messages.
    """
    
    Name = "zork"
    Version = "1.0.0"
    Description = "Zork I text adventure game"
    
    CommandHandlers = {
        "ZORK": HandleZorkCommand,
    }
    
    def OnLoad(self, context: PluginContext) -> None:
        """Initialize the plugin."""
        super().OnLoad(context)
        self.logger.info("Zork plugin loaded - type ZORK to play!")
    
    def GetHelpText(self) -> str:
        """Get help text for Zork commands."""
        return """=== Zork ===
ZORK - Start game
N/S/E/W/U/D - Move
LOOK - Look around
TAKE/DROP - Items
INVENTORY - Check items
SCORE - View score
HELP - Commands
QUIT - Abandon game"""


# Alias handler for shorter command
def HandleZCommand(context: HandlerContext) -> str:
    """Alias for ZORK command."""
    return HandleZorkCommand(context)


# Export both handlers
CommandHandlers = {
    "ZORK": HandleZorkCommand,
}
