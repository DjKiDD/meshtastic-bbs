"""
Zork I - Complete Text Adventure Game Plugin

A faithful recreation of Zork I (1980) by Infocom for Meshtastic BBS.
Implements the complete game world, items, puzzles, and scoring.

Original game by Marc Blank, Dave Lebling, Bruce Daniels, Tim Anderson
Ported for Meshtastic BBS with multi-message support for longer responses.
"""

import random
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from bbs.plugins.BasePlugin import BasePlugin, PluginContext
from bbs.protocol.CommandRouter import HandlerContext

import logging


# =============================================================================
# COMPLETE ROOM DATABASE - All Zork I Rooms
# =============================================================================

ROOMS: Dict[str, Dict] = {}

def _init_rooms():
    """Initialize all Zork I rooms."""
    global ROOMS
    
    ROOMS = {
        # ==================== HOUSE EXTERIOR ====================
        "west_of_house": {
            "name": "West of House",
            "description": "You are standing in an open field west of a white house, with a boarded front door. There is a large mailbox here.",
            "exits": {"north": "north_of_house", "south": "south_of_house", "west": "forest_1", "ne": "north_of_house", "se": "south_of_house", "sw": "stone_barrow"},
            "items": [],
            "dark": False,
        },
        "north_of_house": {
            "name": "North of House",
            "description": "You are standing at the north end of the house. The front door is boarded. There are windows on the north face.",
            "exits": {"south": "west_of_house", "west": "forest_1", "east": "behind_house", "n": "forest_path"},
            "items": [],
            "dark": False,
        },
        "south_of_house": {
            "name": "South of House", 
            "description": "You are standing at the south end of the house. The front door is boarded.",
            "exits": {"north": "west_of_house", "west": "forest_3", "east": "behind_house", "ne": "behind_house"},
            "items": [],
            "dark": False,
        },
        "behind_house": {
            "name": "Behind House",
            "description": "You are standing behind the white house. A kitchen window is open to the west.",
            "exits": {"north": "north_of_house", "south": "south_of_house", "east": "clearing", "west": "kitchen"},
            "items": [],
            "dark": False,
        },
        "stone_barrow": {
            "name": "Stone Barrow",
            "description": "You are standing in front of a massive stone barrow. A heavy stone door is set into the ground.",
            "exits": {"ne": "west_of_house"},
            "items": [],
            "dark": False,
            "locked": True,
            "key": "skeleton_key",
        },
        
        # ==================== FOREST ====================
        "forest_1": {
            "name": "Forest",
            "description": "You are in a dense forest. Trees surround you on all sides.",
            "exits": {"east": "west_of_house", "west": "forest_1_dead", "n": "clearing", "s": "forest_3"},
            "items": [],
            "dark": False,
        },
        "forest_1_dead": {
            "name": "Forest",
            "description": "The forest path ends here, blocked by dense undergrowth.",
            "exits": {"east": "forest_1"},
            "items": [],
            "dark": False,
        },
        "forest_3": {
            "name": "Forest",
            "description": "You are in a dimly lit forest with large trees.",
            "exits": {"north": "clearing", "west": "forest_1", "nw": "south_of_house"},
            "items": [],
            "dark": False,
        },
        "clearing": {
            "name": "Forest Clearing",
            "description": "You are in a small clearing in a well-marked forest path.",
            "exits": {"north": "forest_2", "south": "forest_3", "east": "behind_house", "w": "canyon_view"},
            "items": [],
            "dark": False,
        },
        "forest_2": {
            "name": "Forest",
            "description": "You are in a dimly lit forest. The path leads in several directions.",
            "exits": {"south": "clearing", "east": "forest_path", "w": "forest_1"},
            "items": [],
            "dark": False,
        },
        "forest_path": {
            "name": "Forest Path",
            "description": "A path winds through the dim forest. A large tree grows here, climbable.",
            "exits": {"south": "north_of_house", "east": "forest_2", "north": "grating_clearing", "up": "up_a_tree"},
            "items": ["brass_lamp"],
            "dark": False,
        },
        "up_a_tree": {
            "name": "Up a Tree",
            "description": "You are high in a large tree. A bird's nest is visible in the branches.",
            "exits": {"down": "forest_path"},
            "items": ["jeweled_egg"],
            "dark": False,
        },
        "grating_clearing": {
            "name": "Grating Clearing",
            "description": "You are in a small clearing. A rusty metal grating is set into the ground, leading down.",
            "exits": {"south": "forest_path", "down": "grating_room"},
            "items": [],
            "dark": False,
        },
        "canyon_view": {
            "name": "Canyon View",
            "description": "You stand atop the Great Canyon. The view is magnificent. A trail leads down.",
            "exits": {"east": "clearing", "down": "cliff_middle", "nw": "forest_3"},
            "items": [],
            "dark": False,
        },
        "cliff_middle": {
            "name": "Rocky Ledge",
            "description": "You are halfway up a tall cliff. A trail leads up.",
            "exits": {"up": "canyon_view", "down": "canyon_bottom"},
            "items": [],
            "dark": False,
        },
        "canyon_bottom": {
            "name": "Canyon Bottom",
            "description": "You are at the bottom of a deep canyon. The walls tower above you.",
            "exits": {"up": "cliff_middle", "north": "end_of_rainbow"},
            "items": [],
            "dark": False,
        },
        "end_of_rainbow": {
            "name": "End of Rainbow",
            "description": "You are on a rocky beach past the waterfall. A shimmering rainbow spans the sky.",
            "exits": {"sw": "canyon_bottom", "up": "on_rainbow"},
            "items": ["pot_of_gold"],
            "dark": False,
        },
        "on_rainbow": {
            "name": "On Rainbow",
            "description": "You are standing on top of a rainbow! The colors swirl around you.",
            "exits": {"east": "end_of_rainbow", "west": "on_rainbow_east"},
            "items": [],
            "dark": False,
        },
        "on_rainbow_east": {
            "name": "On Rainbow",
            "description": "You are standing on the rainbow.",
            "exits": {"east": "on_rainbow"},
            "items": [],
            "dark": False,
        },
        
        # ==================== HOUSE INTERIOR ====================
        "kitchen": {
            "name": "Kitchen",
            "description": "You are in a small kitchen. A table holds some food and a bottle. The exit is west.",
            "exits": {"west": "living_room", "east": "behind_house"},
            "items": ["bottle", "food", "lunch"],
            "dark": False,
        },
        "living_room": {
            "name": "Living Room",
            "description": "You are in a living room. A trophy case stands against one wall. A heavy rug covers the floor. An old sword hangs on the wall.",
            "exits": {"east": "kitchen", "down": "cellar"},
            "items": ["sword", "trophy_case", "rug"],
            "dark": False,
        },
        "attic": {
            "name": "Attic",
            "description": "You are in a dark attic. The only exit is down.",
            "exits": {"down": "kitchen"},
            "items": ["rope", "nasty_knife"],
            "dark": True,
            "need_lamp": True,
        },
        
        # ==================== UNDERGROUND ====================
        "cellar": {
            "name": "Cellar",
            "description": "You are in a dusty cellar beneath the living room. The only exit is up.",
            "exits": {"up": "living_room", "east": "troll_room"},
            "items": [],
            "dark": True,
            "need_lamp": True,
        },
        "troll_room": {
            "name": "Troll Room",
            "description": "You are in a small room with passages leading east and west. A massive troll blocks the way!",
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
            "description": "You are in a circular stone room. Exits lead in many directions.",
            "exits": {"west": "east_west_passage", "north": "cold_passage", "south": "mirror_room_1", "east": "loud_room", "se": "engravings_cave"},
            "items": [],
            "dark": False,
        },
        "gallery": {
            "name": "Art Gallery",
            "description": "You are in an art gallery. Most of the paintings have been stolen.",
            "exits": {"west": "east_of_chasm", "north": "studio"},
            "items": ["painting"],
            "dark": False,
        },
        "studio": {
            "name": "Studio",
            "description": "You are in an artist's studio. Paint is splattered everywhere.",
            "exits": {"south": "gallery"},
            "items": [],
            "dark": False,
        },
        "east_of_chasm": {
            "name": "East of Chasm",
            "description": "You are standing on the east edge of a deep chasm.",
            "exits": {"north": "cellar", "east": "gallery"},
            "items": [],
            "dark": False,
        },
        "loud_room": {
            "name": "Loud Room",
            "description": "You are in a room with strange acoustic properties. Sounds echo loudly!",
            "exits": {"west": "round_room", "east": "damp_cave", "down": "deep_canyon"},
            "items": ["platinum_bar"],
            "dark": False,
        },
        "damp_cave": {
            "name": "Damp Cave",
            "description": "You are in a damp cave with exits in several directions.",
            "exits": {"west": "loud_room", "east": "white_cliffs_north"},
            "items": [],
            "dark": False,
        },
        
        # ==================== MIRROR MAZE ====================
        "mirror_room_1": {
            "name": "Mirror Room",
            "description": "You are in a maze of mirrored passages. The reflections make navigation difficult.",
            "exits": {"north": "round_room", "south": "mirror_room_2", "east": "twisting_passage", "west": "cold_passage"},
            "items": [],
            "dark": False,
        },
        "mirror_room_2": {
            "name": "Mirror Room",
            "description": "You are in a maze of mirrored passages.",
            "exits": {"north": "mirror_room_1", "east": "winding_passage"},
            "items": [],
            "dark": False,
        },
        "cold_passage": {
            "name": "Cold Passage",
            "description": "You are in a cold, damp corridor.",
            "exits": {"south": "mirror_room_1", "west": "slide_room"},
            "items": [],
            "dark": False,
        },
        "twisting_passage": {
            "name": "Twisting Passage",
            "description": "You are in a twisting passage.",
            "exits": {"north": "small_cave", "west": "mirror_room_1"},
            "items": [],
            "dark": False,
        },
        "winding_passage": {
            "name": "Winding Passage",
            "description": "You are in a winding passage.",
            "exits": {"north": "tiny_cave", "east": "mirror_room_2"},
            "items": [],
            "dark": False,
        },
        "small_cave": {
            "name": "Small Cave",
            "description": "You are in a small cave with a staircase leading down.",
            "exits": {"south": "twisting_passage", "down": "atlantis"},
            "items": [],
            "dark": False,
        },
        "tiny_cave": {
            "name": "Tiny Cave",
            "description": "You are in a tiny cave with a dark staircase.",
            "exits": {"south": "winding_passage", "down": "entrance_to_hades"},
            "items": [],
            "dark": False,
        },
        
        # ==================== MAZE ====================
        "maze_1": {
            "name": "Maze",
            "description": "You are in a twisty maze of passages.",
            "exits": {"north": "troll_room", "south": "maze_2", "east": "maze_3"},
            "items": [],
            "dark": False,
        },
        "maze_2": {
            "name": "Maze",
            "description": "You are in a twisty maze of passages.",
            "exits": {"north": "maze_1", "south": "maze_4", "east": "maze_3_dead"},
            "items": [],
            "dark": False,
        },
        "maze_3_dead": {
            "name": "Dead End",
            "description": "You are at a dead end of the maze.",
            "exits": {"west": "maze_2"},
            "items": [],
            "dark": False,
        },
        "maze_4": {
            "name": "Maze",
            "description": "You are in a twisty maze of passages.",
            "exits": {"north": "maze_2", "south": "maze_1", "east": "maze_5"},
            "items": [],
            "dark": False,
        },
        "maze_5": {
            "name": "Maze",
            "description": "You are in a twisty maze. A skeleton lies in the corner.",
            "exits": {"west": "maze_4", "north": "maze_9"},
            "items": ["bag_of_coins", "skeleton_key", "rusty_knife"],
            "dark": False,
        },
        "maze_9": {
            "name": "Maze",
            "description": "You are in a twisty maze of passages.",
            "exits": {"south": "maze_5", "east": "maze_10", "ne": "grating_room"},
            "items": [],
            "dark": False,
        },
        "maze_10": {
            "name": "Maze",
            "description": "You are in a twisty maze of passages.",
            "exits": {"west": "maze_9", "east": "maze_11"},
            "items": [],
            "dark": False,
        },
        "maze_11": {
            "name": "Maze",
            "description": "You are in a twisty maze of passages.",
            "exits": {"west": "maze_10", "south": "maze_12", "down": "grating_room"},
            "items": [],
            "dark": False,
        },
        "maze_12": {
            "name": "Maze",
            "description": "You are in a twisty maze of passages.",
            "exits": {"north": "maze_11"},
            "items": [],
            "dark": False,
        },
        "grating_room": {
            "name": "Grating Room",
            "description": "You are in a small room beneath a metal grating.",
            "exits": {"up": "grating_clearing"},
            "items": [],
            "dark": True,
            "need_lamp": True,
            "grating_locked": True,
        },
        
        # ==================== CYCLOPS AREA ====================
        "maze_15": {
            "name": "Maze",
            "description": "You are in a twisty maze of passages.",
            "exits": {"north": "maze_1", "se": "cyclops_room"},
            "items": [],
            "dark": False,
        },
        "cyclops_room": {
            "name": "Cyclops Room",
            "description": "You are in a large room. A massive cyclops sleeps in the corner!",
            "exits": {"nw": "maze_15", "east": "strange_passage"},
            "items": [],
            "dark": False,
            "cyclops": True,
        },
        "strange_passage": {
            "name": "Strange Passage",
            "description": "You are in a long passage. A cyclops-sized door blocks the way.",
            "exits": {"west": "cyclops_room", "east": "treasure_room"},
            "items": [],
            "dark": False,
        },
        "treasure_room": {
            "name": "Treasure Room",
            "description": "You are in a room filled with treasure!",
            "exits": {"west": "strange_passage"},
            "items": ["silver_chalice", "trunk_of_jewels"],
            "dark": False,
        },
        
        # ==================== RESERVOIR ====================
        "reservoir_south": {
            "name": "Reservoir South",
            "description": "You are standing on the south shore of a large reservoir.",
            "exits": {"north": "reservoir_main", "south": "dam", "east": "dam"},
            "items": [],
            "dark": False,
        },
        "reservoir_main": {
            "name": "The Reservoir",
            "description": "You are on the reservoir. A boat would be useful here.",
            "exits": {"south": "reservoir_south", "north": "reservoir_north", "west": "in_stream"},
            "items": [],
            "dark": False,
            "boat_needed": True,
        },
        "reservoir_north": {
            "name": "Reservoir North",
            "description": "You are on the north shore of the reservoir.",
            "exits": {"south": "reservoir_main", "north": "atlantis"},
            "items": [],
            "dark": False,
        },
        "dam": {
            "name": "Dam",
            "description": "You are at a flood control dam. A control panel has a large wheel.",
            "exits": {"north": "reservoir_south", "south": "dam_lobby", "east": "dam_base"},
            "items": ["wrench", "screwdriver"],
            "dark": False,
        },
        "dam_lobby": {
            "name": "Dam Lobby",
            "description": "You are in a waiting room for tours of the dam.",
            "exits": {"north": "dam", "east": "maintenance_room"},
            "items": ["matchbook", "tour_book"],
            "dark": False,
        },
        "maintenance_room": {
            "name": "Maintenance Room",
            "description": "You are in the dam maintenance area.",
            "exits": {"west": "dam_lobby"},
            "items": ["tube"],
            "dark": False,
        },
        "dam_base": {
            "name": "Dam Base",
            "description": "You are at the base of the dam. The river flows by.",
            "exits": {"north": "dam", "west": "frigid_river_1"},
            "items": ["inflatable_boat"],
            "dark": False,
        },
        
        # ==================== RIVER ====================
        "frigid_river_1": {
            "name": "Frigid River",
            "description": "You are on a cold river near the dam.",
            "exits": {"east": "dam_base", "west": "frigid_river_2"},
            "items": [],
            "dark": False,
            "boat_needed": True,
        },
        "frigid_river_2": {
            "name": "Frigid River",
            "description": "You are on a cold river. White cliffs rise to the east.",
            "exits": {"east": "frigid_river_1", "west": "frigid_river_3"},
            "items": [],
            "dark": False,
            "boat_needed": True,
        },
        "frigid_river_3": {
            "name": "Frigid River",
            "description": "You are on a river descending rapidly.",
            "exits": {"east": "frigid_river_2", "west": "frigid_river_4"},
            "items": [],
            "dark": False,
            "boat_needed": True,
        },
        "frigid_river_4": {
            "name": "Frigid River",
            "description": "You are on a fast-moving river. A sandy beach lies to the east.",
            "exits": {"east": "sandy_beach", "west": "frigid_river_5"},
            "items": ["buoy"],
            "dark": False,
            "boat_needed": True,
        },
        "frigid_river_5": {
            "name": "Frigid River",
            "description": "You are on a loud, rushing river.",
            "exits": {"east": "shore"},
            "items": [],
            "dark": False,
            "boat_needed": True,
        },
        "shore": {
            "name": "Shore",
            "description": "You are on the east shore of the river.",
            "exits": {"north": "sandy_beach", "south": "aragain_falls"},
            "items": [],
            "dark": False,
        },
        "sandy_beach": {
            "name": "Sandy Beach",
            "description": "You are on a large sandy beach.",
            "exits": {"south": "shore", "ne": "sandy_cave"},
            "items": ["shovel"],
            "dark": False,
        },
        "sandy_cave": {
            "name": "Sandy Cave",
            "description": "You are in a sand-filled cave.",
            "exits": {"sw": "sandy_beach"},
            "items": ["jeweled_scarab"],
            "dark": False,
        },
        "aragain_falls": {
            "name": "Aragain Falls",
            "description": "You stand before a majestic waterfall.",
            "exits": {"north": "shore", "west": "on_rainbow"},
            "items": [],
            "dark": False,
        },
        "white_cliffs_north": {
            "name": "White Cliffs North",
            "description": "You are on a rocky beach along the white cliffs.",
            "exits": {"west": "damp_cave", "south": "white_cliffs_south"},
            "items": [],
            "dark": False,
        },
        "white_cliffs_south": {
            "name": "White Cliffs South",
            "description": "You are on a rocky beach along the white cliffs.",
            "exits": {"north": "white_cliffs_north"},
            "items": [],
            "dark": False,
        },
        
        # ==================== HADES ====================
        "entrance_to_hades": {
            "name": "Entrance to Hades",
            "description": "You stand before the entrance to the Land of the Dead. A fearsome guardian blocks the way.",
            "exits": {"up": "tiny_cave", "south": "land_of_living_dead"},
            "items": [],
            "dark": False,
            "guardian": True,
        },
        "land_of_living_dead": {
            "name": "Land of the Living Dead",
            "description": "You are in a terrifying realm of ghosts and spirits!",
            "exits": {"north": "entrance_to_hades"},
            "items": ["crystal_skull"],
            "dark": True,
            "need_lamp": True,
            "garlic_needed": True,
        },
        
        # ==================== TEMPLE ====================
        "engravings_cave": {
            "name": "Engravings Cave",
            "description": "You are in a low cave with ancient engravings on the walls.",
            "exits": {"nw": "round_room", "east": "dome_room"},
            "items": [],
            "dark": False,
        },
        "dome_room": {
            "name": "Dome Room",
            "description": "You are in a room with a domed ceiling. The way down is blocked by a granite wall.",
            "exits": {"west": "engravings_cave", "down": "torch_room"},
            "items": [],
            "dark": False,
        },
        "torch_room": {
            "name": "Torch Room",
            "description": "You are in a room lit by torches.",
            "exits": {"north": "north_temple", "up": "dome_room"},
            "items": ["torch"],
            "dark": False,
        },
        "north_temple": {
            "name": "North Temple",
            "description": "You are in the north end of an ancient temple. A brass bell hangs from the ceiling.",
            "exits": {"south": "south_temple", "down": "torch_room", "east": "egyptian_room"},
            "items": ["brass_bell"],
            "dark": False,
        },
        "south_temple": {
            "name": "South Temple",
            "description": "You are in the south end of an ancient temple. An altar stands against the north wall.",
            "exits": {"north": "north_temple"},
            "items": ["black_book", "candle", "altar"],
            "dark": False,
        },
        "egyptian_room": {
            "name": "Egyptian Room",
            "description": "You are in an Egyptian tomb. A golden coffin rests here.",
            "exits": {"west": "north_temple", "up": "north_temple"},
            "items": ["gold_coffin", "sceptre"],
            "dark": False,
        },
        
        # ==================== ATLANTIS ====================
        "atlantis": {
            "name": "Atlantis",
            "description": "You are in an ancient underwater room. The water glows with an eerie light.",
            "exits": {"south": "reservoir_north", "up": "small_cave"},
            "items": ["crystal_trident"],
            "dark": True,
            "need_lamp": True,
        },
        
        # ==================== DEEP CANYON ====================
        "deep_canyon": {
            "name": "Deep Canyon",
            "description": "You are in a deep canyon. The walls tower above you.",
            "exits": {"ne": "reservoir_south", "up": "loud_room"},
            "items": [],
            "dark": False,
        },
        
        # ==================== MINE ====================
        "slide_room": {
            "name": "Slide Room",
            "description": "You are in a room with a slide. The wall says 'Granite Wall'.",
            "exits": {"east": "cold_passage", "north": "mine_entrance", "down": "cellar"},
            "items": [],
            "dark": False,
        },
        "mine_entrance": {
            "name": "Mine Entrance",
            "description": "You are at the entrance of an abandoned coal mine.",
            "exits": {"south": "slide_room", "in": "squeaky_room"},
            "items": [],
            "dark": False,
        },
        "squeaky_room": {
            "name": "Squeaky Room",
            "description": "You are in a room with extremely squeaky floors.",
            "exits": {"north": "bat_room", "east": "mine_entrance"},
            "items": [],
            "dark": False,
        },
        "bat_room": {
            "name": "Bat Room",
            "description": "You are in a room filled with bats! They hang from the ceiling.",
            "exits": {"south": "squeaky_room", "east": "shaft_room"},
            "items": ["jade_figurine"],
            "dark": False,
        },
        "shaft_room": {
            "name": "Shaft Room",
            "description": "You are in a large room with a shaft and chain.",
            "exits": {"west": "bat_room", "north": "smelly_room"},
            "items": [],
            "dark": False,
        },
        "smelly_room": {
            "name": "Smelly Room",
            "description": "You are in a small room with a foul odor.",
            "exits": {"south": "shaft_room", "down": "gas_room"},
            "items": [],
            "dark": False,
        },
        "gas_room": {
            "name": "Gas Room",
            "description": "You are in a room smelling of coal gas. It's dangerous here!",
            "exits": {"up": "smelly_room"},
            "items": ["sapphire_bracelet"],
            "dark": False,
        },
        
        # ==================== COAL MINE ====================
        "mine_1": {
            "name": "Coal Mine",
            "description": "You are in an old coal mine tunnel.",
            "exits": {"north": "gas_room", "east": "mine_2"},
            "items": [],
            "dark": False,
        },
        "mine_2": {
            "name": "Coal Mine",
            "description": "You are in an old coal mine tunnel.",
            "exits": {"south": "mine_1", "ne": "mine_3"},
            "items": [],
            "dark": False,
        },
        "mine_3": {
            "name": "Coal Mine",
            "description": "You are in an old coal mine tunnel.",
            "exits": {"sw": "mine_2", "west": "machine_room"},
            "items": [],
            "dark": False,
        },
        "machine_room": {
            "name": "Machine Room",
            "description": "You are in a room with a strange machine.",
            "exits": {"east": "mine_3"},
            "items": ["huge_diamond", "coal"],
            "dark": False,
        },
    }

_init_rooms()


# =============================================================================
# COMPLETE ITEM DATABASE - All Zork I Items
# =============================================================================

ITEMS: Dict[str, Dict] = {
    # ==================== TREASURES ====================
    "jeweled_egg": {
        "name": "Jeweled Egg",
        "description": "A beautiful jewel-encrusted egg. It seems to contain something inside.",
        "take_points": 5,
        "treasure": True,
    },
    "golden_canary": {
        "name": "Golden Canary",
        "description": "A beautiful golden clockwork canary.",
        "take_points": 6,
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
    "gold_coffin": {
        "name": "Gold Coffin",
        "description": "A golden Egyptian coffin.",
        "take_points": 10,
        "treasure": True,
    },
    "sceptre": {
        "name": "Egyptian Sceptre",
        "description": "An ancient Egyptian sceptre.",
        "take_points": 4,
        "treasure": True,
    },
    "jade_figurine": {
        "name": "Jade Figurine",
        "description": "A delicate jade figurine.",
        "take_points": 5,
        "treasure": True,
    },
    "sapphire_bracelet": {
        "name": "Sapphire Bracelet",
        "description": "A beautiful sapphire bracelet.",
        "take_points": 5,
        "treasure": True,
    },
    "huge_diamond": {
        "name": "Huge Diamond",
        "description": "A massive diamond.",
        "take_points": 10,
        "treasure": True,
    },
    "pot_of_gold": {
        "name": "Pot of Gold",
        "description": "A legendary pot of gold at the end of the rainbow!",
        "take_points": 10,
        "treasure": True,
    },
    "trunk_of_jewels": {
        "name": "Trunk of Jewels",
        "description": "A trunk filled with precious jewels.",
        "take_points": 15,
        "treasure": True,
    },
    "jeweled_scarab": {
        "name": "Jeweled Scarab",
        "description": "A scarab beetle made of jewels.",
        "take_points": 5,
        "treasure": True,
    },
    "torch": {
        "name": "Ivory Torch",
        "description": "An ivory torch on a pedestal.",
        "take_points": 14,
        "treasure": True,
    },
    "buoy": {
        "name": "Buoy",
        "description": "A rusty buoy floating in the water.",
        "take_points": 5,
        "treasure": True,
    },
    
    # ==================== TOOLS & ITEMS ====================
    "brass_lamp": {
        "name": "Brass Lamp",
        "description": "A brass lamp that provides light.",
        "take_points": 0,
        "treasure": False,
    },
    "skeleton_key": {
        "name": "Skeleton Key",
        "description": "A small rusty key.",
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
    "nasty_knife": {
        "name": "Nasty Knife",
        "description": "A sharp knife.",
        "take_points": 0,
        "treasure": False,
    },
    "rusty_knife": {
        "name": "Rusty Knife",
        "description": "A rusty, cursed knife.",
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
    "lunch": {
        "name": "Hot Pepper Sandwich",
        "description": "A sandwich with hot peppers.",
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
    "rug": {
        "name": "Heavy Rug",
        "description": "A heavy Persian rug.",
        "take_points": 0,
        "treasure": False,
        "fixed": True,
    },
    "black_book": {
        "name": "Black Book",
        "description": "A mysterious black book with strange symbols.",
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
    "shovel": {
        "name": "Shovel",
        "description": "A sturdy shovel.",
        "take_points": 0,
        "treasure": False,
    },
    "matchbook": {
        "name": "Matchbook",
        "description": "A book of matches.",
        "take_points": 0,
        "treasure": False,
    },
    "tour_book": {
        "name": "Tour Booklet",
        "description": "A tourist guidebook for the dam.",
        "take_points": 0,
        "treasure": False,
    },
    "tube": {
        "name": "Tube",
        "description": "A tube with something inside.",
        "take_points": 0,
        "treasure": False,
    },
    "inflatable_boat": {
        "name": "Inflatable Boat",
        "description": "A small inflatable boat.",
        "take_points": 0,
        "treasure": False,
    },
    "coal": {
        "name": "Lump of Coal",
        "description": "A lump of coal.",
        "take_points": 0,
        "treasure": False,
    },
    "altar": {
        "name": "Stone Altar",
        "description": "An ancient stone altar.",
        "take_points": 0,
        "treasure": False,
        "fixed": True,
    },
}


# =============================================================================
# GAME STATE CLASS
# =============================================================================

class ZorkGameState:
    """Complete game state for a single player."""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.location = "west_of_house"
        self.inventory: List[str] = []
        self.score = 0
        self.turns = 0
        self.game_over = False
        self.victory = False
        self.message_count = 0
        
        # All game flags
        self.flags = {
            "troll_defeated": False,
            "window_open": False,
            "door_unlocked": False,
            "trap_door_open": False,
            "lamp_on": False,
            "cyclops_asleep": False,
            "grate_open": False,
            "dam_drained": False,
            "boat_inflated": False,
            "boat_in_water": False,
            "candle_lit": False,
            "ghosts_exorcised": False,
            "tide_low": False,
            "rainbow_active": False,
            "dome_open": False,
            "coffin_open": False,
        }
        
        # Special item states
        self.garlic_eaten = False
        self.water_bottle = False
        self.cyclops_fed = False
    
    def GetDescription(self) -> str:
        """Get current room description."""
        room = ROOMS.get(self.location)
        if not room:
            return "You are lost in the void!"
        
        desc = f"[{room['name']}]\n{room['description']}"
        
        # Special conditions
        if self.location == "troll_room" and not self.flags["troll_defeated"]:
            desc += "\nA massive TROLL blocks the east and west passages!"
        
        if self.location == "cyclops_room" and not self.flags["cyclops_asleep"]:
            desc += "\nA massive CYCLOPS sleeps here! Better not wake him."
        
        if self.location == "entrance_to_hades" and not self.flags["ghosts_exorcised"]:
            desc += "\nA fearsome GUARDIAN blocks the way!"
        
        # Show items in room
        if room.get('items'):
            item_names = []
            for i in room['items']:
                if i in ITEMS:
                    item_names.append(ITEMS[i]['name'])
            if item_names:
                desc += f"\nYou see: {', '.join(item_names)}"
        
        # Dark check
        if room.get('dark') and not self.flags.get('lamp_on'):
            if 'brass_lamp' not in self.inventory:
                return desc + "\n\nIt is pitch black. You are likely to be eaten by a grue."
        
        # Show exits
        exits = list(room.get('exits', {}).keys())
        if exits:
            desc += f"\n\nExits: {', '.join(exits)}"
        
        return desc
    
    def Move(self, direction: str) -> str:
        """Attempt to move in a direction."""
        room = ROOMS.get(self.location)
        if not room:
            return "You are lost!"
        
        # Normalize direction
        direction_map = {
            'n': 'north', 's': 'south', 'e': 'east', 'w': 'west',
            'u': 'up', 'd': 'down', 'ne': 'ne', 'nw': 'nw', 'se': 'se', 'sw': 'sw',
            'north': 'north', 'south': 'south', 'east': 'east', 'west': 'west',
            'up': 'up', 'down': 'down', 'northeast': 'ne', 'northwest': 'nw',
            'southeast': 'se', 'southwest': 'sw', 'in': 'south', 'out': 'north',
        }
        direction = direction_map.get(direction.lower(), direction.lower())
        
        if direction not in room.get('exits', {}):
            return "You can't go that way."
        
        target = room['exits'][direction]
        
        # Blocked exits
        if self.location == "troll_room" and direction in ("east", "west") and not self.flags["troll_defeated"]:
            return "The TROLL blocks your path! You must deal with him first."
        
        if self.location == "cyclops_room" and direction == "up" and not self.flags["cyclops_asleep"]:
            return "The cyclops wakes and blocks your path!"
        
        if self.location == "entrance_to_hades" and direction == "south" and not self.flags["ghosts_exorcised"]:
            return "The GUARDIAN blocks your path! The spirits are too powerful."
        
        if self.location == "grating_room" and direction == "up" and not self.flags["grate_open"]:
            return "The grate is locked. You need a key."
        
        # Dark room check
        if target in ROOMS:
            target_room = ROOMS[target]
            if target_room.get('dark') and not self.flags.get('lamp_on'):
                if 'brass_lamp' not in self.inventory:
                    return "It's too dark to go that way!"
        
        self.location = target
        self.turns += 1
        return self.GetDescription()
    
    def Take(self, item_name: str) -> str:
        """Take an item."""
        room = ROOMS.get(self.location)
        if not room:
            return "You can't do that here."
        
        # Find item
        item_id = None
        for i in room.get('items', []):
            if i in ITEMS and ITEMS[i]['name'].lower() == item_name.lower():
                item_id = i
                break
        
        if not item_id:
            # Partial match
            for i in room.get('items', []):
                if i in ITEMS and item_name.lower() in ITEMS[i]['name'].lower():
                    item_id = i
                    break
        
        if not item_id:
            return "You don't see that here."
        
        if ITEMS[item_id].get('fixed'):
            return "You can't take that."
        
        # Remove from room, add to inventory
        room['items'].remove(item_id)
        self.inventory.append(item_id)
        
        # Score for treasure
        if ITEMS[item_id].get('treasure'):
            points = ITEMS[item_id].get('take_points', 0)
            self.score += points
            return f" taken. ({points} points)"
        
        return " taken."
    
    def Drop(self, item_name: str) -> str:
        """Drop an item."""
        item_id = None
        for i in self.inventory:
            if i in ITEMS and ITEMS[i]['name'].lower() == item_name.lower():
                item_id = i
                break
        
        if not item_id:
            for i in self.inventory:
                if i in ITEMS and item_name.lower() in ITEMS[i]['name'].lower():
                    item_id = i
                    break
        
        if not item_id:
            return "You're not carrying that."
        
        self.inventory.remove(item_id)
        room = ROOMS.get(self.location)
        if room:
            room['items'].append(item_id)
        
        return " dropped."
    
    def Examine(self, item_name: str) -> str:
        """Examine something."""
        # Check inventory
        for i in self.inventory:
            if i in ITEMS and (ITEMS[i]['name'].lower() == item_name.lower() or 
                             item_name.lower() in ITEMS[i]['name'].lower()):
                return ITEMS[i]['description']
        
        # Check room
        room = ROOMS.get(self.location)
        if room:
            for i in room.get('items', []):
                if i in ITEMS and (ITEMS[i]['name'].lower() == item_name.lower() or
                                   item_name.lower() in ITEMS[i]['name'].lower()):
                    return ITEMS[i]['description']
        
        # Check special objects
        if "rug" in item_name.lower() and self.location == "living_room":
            return "A beautiful Persian rug. It looks like it could be moved."
        
        if "troll" in item_name.lower() and self.location == "troll_room":
            return "A massive, nasty troll. He looks hungry."
        
        if "cyclops" in item_name.lower() and self.location == "cyclops_room":
            return "A huge one-eyed giant. He's sleeping soundly."
        
        return "You don't see that here."
    
    def Inventory(self) -> str:
        """Show inventory."""
        if not self.inventory:
            return "You are empty-handed."
        
        lines = ["You are carrying:"]
        for i in self.inventory:
            if i in ITEMS:
                lines.append(f"  {ITEMS[i]['name']}")
        
        # Show if lamp is on
        if self.flags.get('lamp_on'):
            lines.append("\nThe brass lamp is ON.")
        
        return "\n".join(lines)
    
    def Attack(self, target: str) -> str:
        """Attack something."""
        if not target:
            return "Attack what?"
        
        if "troll" in target.lower() and self.location == "troll_room":
            if 'sword' in self.inventory:
                self.flags["troll_defeated"] = True
                self.score += 5
                return "You swing the sword! The troll falls with a thud! (5 points)"
            else:
                return "You have no weapon! The troll laughs at you."
        
        if "cyclops" in target.lower() and self.location == "cyclops_room":
            return "Attacking the cyclops would be suicide!"
        
        return "There's nothing worth attacking here."
    
    def Open(self, target: str) -> str:
        """Open something."""
        if not target:
            return "Open what?"
        
        if "door" in target.lower() and self.location == "stone_barrow":
            if self.flags.get("door_unlocked"):
                return "The door is already open."
            if 'skeleton_key' in self.inventory:
                self.flags["door_unlocked"] = True
                return "You unlock the stone door with the skeleton key!"
            return "You need a key."
        
        if "grate" in target.lower() and self.location == "grating_room":
            if self.flags.get("grate_open"):
                return "The grate is already open."
            if 'skeleton_key' in self.inventory:
                self.flags["grate_open"] = True
                return "You unlock the grate!"
            return "You need a key."
        
        if "window" in target.lower() and self.location == "behind_house":
            self.flags["window_open"] = not self.flags["window_open"]
            if self.flags["window_open"]:
                ROOMS["behind_house"]["exits"]["west"] = "kitchen"
                return "You open the kitchen window."
            else:
                if "kitchen" in ROOMS["behind_house"]["exits"]:
                    del ROOMS["behind_house"]["exits"]["west"]
                return "You close the window."
        
        if "rug" in target.lower() and self.location == "living_room":
            if self.flags.get("trap_door_open"):
                return "The trap door is already open."
            self.flags["trap_door_open"] = True
            ROOMS["living_room"]["exits"]["down"] = "cellar"
            return "You move the rug and open the trap door! A dark staircase leads down."
        
        if "coffin" in target.lower() and self.location == "egyptian_room":
            if self.flags.get("coffin_open"):
                return "The coffin is already open."
            self.flags["coffin_open"] = True
            return "You open the golden coffin!"
        
        return "You can't open that."
    
    def Use(self, item: str) -> str:
        """Use an item."""
        if not item:
            return "Use what?"
        
        # Lamp
        if "lamp" in item.lower() or "brass lamp" in item.lower():
            if 'brass_lamp' in self.inventory:
                self.flags["lamp_on"] = not self.flags["lamp_on"]
                return f"The lamp is now {'ON' if self.flags['lamp_on'] else 'OFF'}."
            return "You don't have the lamp."
        
        # Wrench at dam
        if "wrench" in item.lower() and self.location == "dam":
            if 'wrench' in self.inventory:
                self.flags["dam_drained"] = True
                self.flags["tide_low"] = True
                return "You turn the wheel. With a groan, the dam begins to lower. Water rushes out!"
            return "You need a wrench."
        
        # Give lunch to cyclops
        if "lunch" in item.lower() or "sandwich" in item.lower():
            if 'lunch' in self.inventory and self.location == "cyclops_room":
                self.inventory.remove('lunch')
                self.flags["cyclops_asleep"] = True
                self.turns += 1
                return "You give the hot pepper sandwich to the cyclops. He eats it, screams, and falls asleep! You can now access the treasure room!"
            return "You can't use that here."
        
        return "You can't use that here."
    
    def Score(self) -> str:
        """Show score."""
        return f"Score: {self.score}/350\nTurns: {self.turns}"


# Active games per node
active_games: Dict[str, ZorkGameState] = {}


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def HandleZorkCommand(context: HandlerContext) -> str:
    """Main handler for Zork commands."""
    args = context.arguments
    from_node = context.from_node
    
    # Initialize new game
    if from_node not in active_games:
        active_games[from_node] = ZorkGameState(from_node)
    
    game = active_games[from_node]
    
    # Check for new game
    if not args or args[0].upper() in ("ZORK", "START", "NEW", "RESTART"):
        return game.GetDescription()
    
    cmd = args[0].upper()
    rest = " ".join(args[1:]).lower() if len(args) > 1 else ""
    first_arg = args[0].lower() if args else ""
    
    # Movement - check both cmd and first_arg for directions
    direction_words = ("n", "north", "s", "south", "e", "east", "w", "west", 
                      "u", "up", "d", "down", "ne", "northeast", "nw", "northwest",
                      "se", "southeast", "sw", "southwest", "go", "walk", "enter", "in", "out")
    
    if first_arg in direction_words or cmd in direction_words:
        direction = first_arg if first_arg in direction_words else cmd
        if direction in ("n", "north"): return game.Move("north")
        if direction in ("s", "south"): return game.Move("south")
        if direction in ("e", "east"): return game.Move("east")
        if direction in ("w", "west"): return game.Move("west")
        if direction in ("u", "up"): return game.Move("up")
        if direction in ("d", "down"): return game.Move("down")
        if direction in ("ne", "northeast"): return game.Move("ne")
        if direction in ("nw", "northwest"): return game.Move("nw")
        if direction in ("se", "southeast"): return game.Move("se")
        if direction in ("sw", "southwest"): return game.Move("sw")
        if direction in ("go", "walk", "enter"): 
            if rest: return game.Move(rest)
            return "Go where?"
        if direction in ("in", "out"):
            return game.Move(direction)
        return game.Move(direction)
    
    # Look
    if cmd in ("LOOK", "L", "EXAMINE", "X", "READ"):
        if rest:
            return game.Examine(rest)
        return game.GetDescription()
    
    # Take
    if cmd in ("TAKE", "GET", "GRAB", "PICK", "CARRY"):
        if not rest:
            return "Take what?"
        result = game.Take(rest)
        # Get item name for response
        item_name = "Item"
        for i in game.inventory:
            if i in ITEMS and rest in ITEMS[i]['name'].lower():
                item_name = ITEMS[i]['name']
                break
        return f"{item_name}{result}"
    
    # Drop
    if cmd in ("DROP", "PUT", "DISCARD"):
        if not rest:
            return "Drop what?"
        return f"{rest.title()}{game.Drop(rest)}"
    
    # Inventory
    if cmd in ("INVENTORY", "I", "INV", "CARRYING"):
        return game.Inventory()
    
    # Attack
    if cmd in ("ATTACK", "KILL", "FIGHT", "HIT", "STAB", "CUT", "SLAY"):
        return game.Attack(rest)
    
    # Open
    if cmd in ("OPEN", "UNLOCK"):
        return game.Open(rest)
    
    # Use
    if cmd in ("USE", "OPERATE", "PLAY"):
        return game.Use(rest)
    
    # Score
    if cmd in ("SCORE", "POINTS"):
        return game.Score()
    
    # Quit
    if cmd in ("QUIT", "ABANDON", "STOP"):
        del active_games[from_node]
        return "Game abandoned. Type ZORK to start a new adventure."
    
    # Help
    if cmd in ("HELP", "?"):
        return """ZORK - Text Adventure

COMMANDS:
N/S/E/W/U/D - Move (North, South, East, West, Up, Down)
GO [dir] - Move in direction
LOOK - Describe room
L - Short for LOOK
EXAMINE [item] - Inspect item (or X [item])
TAKE [item] - Pick up item
DROP [item] - Drop item
INVENTORY - Check items (or I)
OPEN [thing] - Open door/window/crate
USE [item] - Use an item
ATTACK [target] - Fight (or KILL, FIGHT)
SCORE - View score
QUIT - Abandon game

TIPS:
- Type LOOK after moving to see the room
- EXAMINE things for clues
- Keep the lamp lit in dark areas!
- Type ZORK to start over
"""
    
    return f"I don't understand '{cmd}'. Type HELP for commands."


# =============================================================================
# PLUGIN DEFINITION
# =============================================================================

class ZorkPlugin(BasePlugin):
    """
    Zork I - Complete Text Adventure Game Plugin
    
    A faithful recreation of Zork I (1980) by Infocom.
    Original game by Marc Blank, Dave Lebling, Bruce Daniels, Tim Anderson
    
    Adapted for Meshtastic BBS with multi-message support.
    """
    
    Name = "zork"
    Version = "1.0.0"
    Description = "Zork I - Classic text adventure game"
    
    CommandHandlers = {
        "ZORK": HandleZorkCommand,
    }
    
    def OnLoad(self, context: PluginContext) -> None:
        """Initialize the plugin."""
        super().OnLoad(context)
        self.logger.info("Zork I loaded - type ZORK to play!")
    
    def GetHelpText(self) -> str:
        """Get help text."""
        return """=== Zork I ===
ZORK - Start new game
N/S/E/W/U/D - Move
LOOK - Look around
TAKE/DROP - Items
EXAMINE - Inspect
INVENTORY - Check items
OPEN - Open things
USE - Use items
ATTACK - Fight
SCORE - View score
HELP - Commands
QUIT - Abandon game"""


# Alias handler
def HandleZCommand(context: HandlerContext) -> str:
    """Alias for ZORK command."""
    return HandleZorkCommand(context)


# Export for plugin system
CommandHandlers = {
    "ZORK": HandleZorkCommand,
}
