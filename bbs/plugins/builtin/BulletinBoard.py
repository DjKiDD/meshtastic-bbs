"""
Bulletin Board Plugin

This plugin handles BBS (Bulletin Board System) commands.

Commands:
    BBS <area> <message>
        Post a message to a bulletin board area
        
    AREAS
        List all available BBS areas
        
    READ <area>
        Read posts in a bulletin board area

Usage:
    BBS general Hello everyone!
    AREAS
    READ general
"""

import time
from datetime import datetime
from bbs.plugins.BasePlugin import BasePlugin, PluginContext
from bbs.Database import BbsArea, BbsPost
from bbs.protocol.CommandRouter import HandlerContext


# Handler functions - defined before the class that references them

def HandlePostToBoard(context: HandlerContext) -> str:
    """
    Handle the BBS command to post to a bulletin board area.
    
    Usage: BBS <area> <message>
    
    This function:
    - Validates the arguments
    - Looks up or creates the area
    - Saves the post to the database
    - Returns confirmation
    
    Args:
        context: Handler context with arguments and services
        
    Returns:
        Response message to send back to sender
    """
    # Check arguments
    if len(context.arguments) < 2:
        return "Usage: BBS <area> <message>"
    
    # Extract area name and message
    area_name = context.arguments[0].lower()
    message_text = " ".join(context.arguments[1:])
    
    # Get or create the area
    area = context.database.GetAreaByName(area_name)
    
    if area is None:
        # Create new area
        area = context.database.CreateArea(
            name=area_name,
            description=f"Area: {area_name}"
        )
    
    # Validate message length (100 char limit)
    if len(message_text) > 100:
        return "Error: Msg too long (max 100 chars)"
    
    # Create post
    post = BbsPost(
        area_id=area.id,
        from_node=context.from_node,
        body=message_text,
        created_at=int(time.time())
    )
    
    # Save to database
    post_id = context.database.SavePost(post)
    
    # Brief confirmation
    return f"Posted to {area_name} (ID:{post_id})"
    
    return "\n".join(response_lines)


def HandleListAreas(context: HandlerContext) -> str:
    """
    Handle the AREAS command to list all BBS areas.
    
    Usage: AREAS
    
    Lists all available bulletin board areas with
    their descriptions and post counts.
    
    Args:
        context: Handler context with arguments and services
        
    Returns:
        Response with list of areas
    """
    # Get all areas
    areas = context.database.GetAllAreas()
    
    if not areas:
        return "No areas. Post: BBS <area> <msg>"
    
    # Brief listing - limit to 5 areas max
    area_info = [f"{a.name}({context.database.GetPostCountForArea(a.name)})" for a in areas[:5]]
    result = "Areas: " + " ".join(area_info)
    if len(areas) > 5:
        result += f" +{len(areas)-5} more"
    return result


def HandleReadBoard(context: HandlerContext) -> str:
    """
    Handle the READ command to read posts from an area.
    
    Usage: READ <area>
    
    This is different from the personal messaging READ command
    because it reads from BBS areas instead of personal inbox.
    
    Args:
        context: Handler context with arguments and services
        
    Returns:
        Response with posts from the area
    """
    # Check arguments - need area name
    if not context.arguments:
        return "Usage: READ <area> | Use AREAS to list"
    
    # Get area name
    area_name = context.arguments[0].lower()
    
    # Get area
    area = context.database.GetAreaByName(area_name)
    
    if area is None:
        return f"Area '{area_name}' not found. Use AREAS."
    
    # Get posts
    posts = context.database.GetPostsForArea(area_name)
    
    if not posts:
        return f"No posts in {area_name}. Be first: BBS {area_name} <msg>"
    
    # Brief listing - show last 1 post only to stay under 200 chars
    lines = [f"=== {area_name} ({len(posts)} posts) ==="]
    for post in posts[:1]:
        preview = post.body[:80].replace("\n", " ")
        lines.append(f"[{post.id}] {post.from_node}: {preview}")
    
    return "\n".join(lines)


class BulletinBoardPlugin(BasePlugin):
    """
    Plugin for handling bulletin board posts.
    
    This plugin allows nodes to post and read messages in
    public bulletin board areas (forums).
    
    Commands:
        BBS: Post to a bulletin board area
        AREAS: List available areas
        READ: Read posts in an area
    """
    
    # Plugin metadata
    Name = "bulletin_board"
    Version = "1.0.0"
    Description = "Bulletin board system for mesh network"
    
    # Command handlers - maps command name to handler method
    CommandHandlers = {
        "BBS": HandlePostToBoard,
        "AREAS": HandleListAreas,
        "READ": HandleReadBoard,
    }
    
    def OnLoad(self, context: PluginContext) -> None:
        """
        Initialize the bulletin board plugin.
        
        Called when the plugin is loaded. Sets up the context,
        creates default areas if configured, and logs initialization.
        
        Args:
            context: Plugin context with database and config access
        """
        super().OnLoad(context)
        
        # Get plugin-specific config
        plugin_config = context.GetPluginConfiguration(self.Name)
        
        # Get default area
        self.default_area = plugin_config.get("default_area", "general")
        
        # Create default areas from config
        areas_config = plugin_config.get("areas", [])
        for area_config in areas_config:
            # Try to create area (will fail if already exists, which is fine)
            try:
                context.database.CreateArea(
                    name=area_config.get("name", "general"),
                    description=area_config.get("description", "")
                )
                context.logger.debug(f"Created BBS area: {area_config.get('name')}")
            except Exception:
                # Area already exists
                pass
        
        self.logger.info(f"Bulletin Board loaded with default area: {self.default_area}")
    
    def Migrate(self, database) -> None:
        """
        Create default BBS areas on first run.
        
        Called during database migration to ensure default
        areas exist.
        
        Args:
            database: Database instance
        """
        # Create default areas if they don't exist
        default_areas = [
            {"name": "general", "description": "General discussion"},
            {"name": "for-sale", "description": "Items for sale or trade"},
            {"name": "help", "description": "Ask for help"},
            {"name": "announcements", "description": "Official announcements"},
        ]
        
        for area in default_areas:
            try:
                database.CreateArea(area["name"], area["description"])
            except Exception:
                # Already exists
                pass
    
    def GetHelpText(self) -> str:
        """
        Get help text for bulletin board commands.
        
        Returns:
            Condensed help string for low bandwidth
        """
        return "BBS <area> <txt> | AREAS | READ <area>"
