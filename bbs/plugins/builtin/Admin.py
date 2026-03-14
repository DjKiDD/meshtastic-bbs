"""
Admin Plugin

This plugin handles admin commands for managing BBS areas and posts.

Commands:
    ADMIN <password> CREATE <area>
        Create a new BBS area
        
    ADMIN <password> DELETE <area>
        Delete a BBS area (asks confirmation if posts exist)
        
    ADMIN <password> DELPOST <post_id>
        Delete a specific post
        
    ADMIN <password> LIST
        List areas with their IDs (for deletion)
        
    ADMIN <password> POSTS <area>
        List posts in area with IDs
        
    ADMIN <password> CONFIRM DELETE <area>
        Confirm deletion of area with posts
        
    ADMIN <password> WHOAMI
        Show your node ID (for adding to allowlist)

Usage:
    ADMIN secret123 CREATE sales
    ADMIN secret123 DELETE sales
    ADMIN secret123 DELPOST 5
    ADMIN secret123 LIST
    ADMIN secret123 POSTS general
"""

import time
from bbs.plugins.BasePlugin import BasePlugin, PluginContext
from bbs.Database import BbsPost
from bbs.protocol.CommandRouter import HandlerContext


# Pending confirmations storage
pending_confirms = {}  # {confirm_key: area_name}


def HandleAdminCommand(context: HandlerContext) -> str:
    """
    Handle the ADMIN command for BBS management.
    
    Usage: ADMIN <password> <command> [args]
    
    Args:
        context: Handler context with arguments and services
        
    Returns:
        Response message
    """
    args = context.arguments
    
    if not args:
        return "Usage: ADMIN <pwd> CREATE|DELETE|DELPOST|LIST|POSTS"
    
    # Check if node is allowlisted (can skip password)
    from bbs.Configuration import Configuration
    config = context.configuration
    
    # Get password from args
    # Format: ADMIN <password> <cmd> <args>
    # Or if allowlisted: ADMIN <cmd> <args>
    
    password = ""
    cmd_args = []
    
    if len(args) < 2:
        return "Usage: ADMIN <pwd> CREATE|DELETE|DELPOST|LIST|POSTS"
    
    # Check if first arg is password or command
    # If node is allowlisted, password can be skipped
    if config.IsNodeAllowedForAdmin(context.from_node):
        # Node is allowlisted, treat first arg as command
        password = None  # No password needed
        cmd_args = args
    else:
        # Need password
        password = args[0]
        cmd_args = args[1:]
    
    # Verify password if required
    if password is not None:
        if password != config.GetAdminPassword():
            return "Error: Invalid password"
        if not config.GetAdminPassword():
            return "Error: Admin password not configured"
    
    if not cmd_args:
        return "Usage: ADMIN <pwd> CREATE|DELETE|DELPOST|LIST|POSTS"
    
    command = cmd_args[0].upper()
    cmd_args = cmd_args[1:]
    
    # BBS commands
    if command == "CREATE":
        return HandleAdminCreate(context, cmd_args)
    elif command == "DELETE":
        return HandleAdminDelete(context, cmd_args)
    elif command == "DELPOST":
        return HandleAdminDelpost(context, cmd_args)
    elif command == "LIST":
        return HandleAdminList(context, cmd_args)
    elif command == "POSTS":
        return HandleAdminPosts(context, cmd_args)
    elif command == "CONFIRM":
        return HandleAdminConfirm(context, cmd_args)
    elif command == "WHOAMI":
        return f"Your node ID: {context.from_node}"
    # Hangman commands
    elif command == "ADDWORD":
        if not cmd_args:
            return "Usage: ADMIN ADDWORD <word>"
        word = cmd_args[0].upper()
        if len(word) < 3:
            return "Word must be 3+ letters"
        try:
            now = int(time.time())
            context.database.connection.execute(
                "INSERT INTO hangman_words (word, added_at) VALUES (?, ?)",
                (word, now)
            )
            context.database.connection.commit()
            return f"OK: Added {word}"
        except Exception as e:
            return f"Error: {e}"
    elif command == "DELWORD":
        if not cmd_args:
            return "Usage: ADMIN DELWORD <word>"
        word = cmd_args[0].upper()
        try:
            context.database.connection.execute(
                "DELETE FROM hangman_words WHERE word = ?", (word,)
            )
            context.database.connection.commit()
            return f"OK: Deleted {word}"
        except Exception as e:
            return f"Error: {e}"
    elif command == "WORDS":
        try:
            cursor = context.database.connection.execute(
                "SELECT COUNT(*) as cnt FROM hangman_words"
            )
            row = cursor.fetchone()
            return f"Hangman words: {row['cnt']}"
        except:
            return "Error: Cannot count words"
    else:
        return f"Unknown admin command: {command}"


def HandleAdminCreate(context: HandlerContext, args) -> str:
    """Create a new BBS area."""
    if not args:
        return "Usage: ADMIN CREATE <area>"
    
    area_name = args[0].lower()
    
    try:
        area = context.database.CreateArea(area_name, f"Area: {area_name}")
        return f"OK: Created '{area_name}'"
    except Exception as e:
        return f"Error: {e}"


def HandleAdminDelete(context: HandlerContext, args) -> str:
    """Delete a BBS area."""
    if not args:
        return "Usage: ADMIN DELETE <area>"
    
    area_name = args[0].lower()
    area = context.database.GetAreaByName(area_name)
    
    if area is None:
        return f"Error: Area '{area_name}' not found"
    
    # Check for posts
    post_count = context.database.GetPostCountForArea(area_name)
    
    if post_count > 0:
        # Need confirmation
        confirm_key = f"{context.from_node}:{area_name}"
        pending_confirms[confirm_key] = area_name
        return f"'{area_name}' has {post_count} posts. Confirm: ADMIN CONFIRM DELETE {area_name}"
    
    # Delete directly
    try:
        # Delete all posts first
        posts = context.database.GetPostsForArea(area_name)
        for post in posts:
            context.database.DeletePost(post.id)
        # Delete area
        context.database.connection.execute("DELETE FROM bbs_areas WHERE id = ?", (area.id,))
        context.database.connection.commit()
        return f"OK: Deleted area '{area_name}'"
    except Exception as e:
        return f"Error: {e}"


def HandleAdminConfirm(context: HandlerContext, args) -> str:
    """Confirm deletion of area with posts."""
    if len(args) < 2 or args[0].upper() != "DELETE":
        return "Usage: ADMIN CONFIRM DELETE <area>"
    
    area_name = args[1].lower()
    confirm_key = f"{context.from_node}:{area_name}"
    
    if confirm_key not in pending_confirms:
        return "No pending confirmation. Use ADMIN DELETE <area> first."
    
    area = context.database.GetAreaByName(area_name)
    if area is None:
        del pending_confirms[confirm_key]
        return f"Error: Area '{area_name}' not found"
    
    try:
        # Delete all posts
        posts = context.database.GetPostsForArea(area_name)
        for post in posts:
            context.database.DeletePost(post.id)
        # Delete area
        context.database.connection.execute("DELETE FROM bbs_areas WHERE id = ?", (area.id,))
        context.database.connection.commit()
        del pending_confirms[confirm_key]
        return f"OK: Deleted area '{area_name}' and {len(posts)} posts"
    except Exception as e:
        return f"Error: {e}"


def HandleAdminDelpost(context: HandlerContext, args) -> str:
    """Delete a specific post."""
    if not args:
        return "Usage: ADMIN DELPOST <post_id>"
    
    try:
        post_id = int(args[0])
    except ValueError:
        return "Error: Invalid post ID"
    
    post = context.database.GetPostById(post_id)
    if post is None:
        return f"Error: Post {post_id} not found"
    
    try:
        context.database.DeletePost(post_id)
        return f"OK: Deleted post {post_id}"
    except Exception as e:
        return f"Error: {e}"


def HandleAdminList(context: HandlerContext, args) -> str:
    """List areas with IDs."""
    areas = context.database.GetAllAreas()
    
    if not areas:
        return "No areas exist"
    
    # Format: Areas: gen(5) fs(2) | IDs: gen=1 fs=2
    area_counts = [f"{a.name}({context.database.GetPostCountForArea(a.name)})" for a in areas]
    area_ids = [f"{a.name}={a.id}" for a in areas]
    
    return "Areas: " + " ".join(area_counts) + " | IDs: " + " ".join(area_ids)


def HandleAdminPosts(context: HandlerContext, args) -> str:
    """List posts in area with IDs."""
    if not args:
        return "Usage: ADMIN POSTS <area>"
    
    area_name = args[0].lower()
    area = context.database.GetAreaByName(area_name)
    
    if area is None:
        return f"Error: Area '{area_name}' not found"
    
    posts = context.database.GetPostsForArea(area_name)
    
    if not posts:
        return f"No posts in '{area_name}'"
    
    # List posts with IDs
    from datetime import datetime
    lines = [f"{area_name}:{len(posts)}"]
    for post in posts[:5]:
        ts = datetime.fromtimestamp(post.created_at)
        ts_str = ts.strftime("%m/%d %H:%M")
        preview = post.body[:40].replace("\n", " ")
        lines.append(f"{post.id} {ts_str} {post.from_node}: {preview}")
    
    if len(posts) > 5:
        lines.append(f"+{len(posts)-5} more")
    
    return " | ".join(lines)


# Hangman admin handlers (defined inline to avoid forward reference issues)

def _HandleHangmanAddWord(context: HandlerContext, args) -> str:
    """Add a word to hangman wordlist."""
    if not args:
        return "Usage: ADMIN ADDWORD <word>"
    word = args[0].upper()
    if len(word) < 3:
        return "Word must be 3+ letters"
    try:
        now = int(time.time())
        context.database.connection.execute(
            "INSERT INTO hangman_words (word, added_at) VALUES (?, ?)",
            (word, now)
        )
        context.database.connection.commit()
        return f"OK: Added {word}"
    except Exception as e:
        return f"Error: {e}"


def _HandleHangmanDelWord(context: HandlerContext, args) -> str:
    """Remove a word from hangman wordlist."""
    if not args:
        return "Usage: ADMIN DELWORD <word>"
    word = args[0].upper()
    try:
        context.database.connection.execute(
            "DELETE FROM hangman_words WHERE word = ?",
            (word,)
        )
        context.database.connection.commit()
        return f"OK: Deleted {word}"
    except Exception as e:
        return f"Error: {e}"


def _HandleHangmanWords(context: HandlerContext, args) -> str:
    """List word count."""
    try:
        cursor = context.database.connection.execute(
            "SELECT COUNT(*) as cnt FROM hangman_words"
        )
        row = cursor.fetchone()
        return f"Hangman words: {row['cnt']}"
    except Exception as e:
        return f"Error: {e}"


class AdminPlugin(BasePlugin):
    """
    Plugin for admin commands.
    """
    
    Name = "admin"
    Version = "1.0.0"
    Description = "Admin commands for BBS management"
    
    CommandHandlers = {
        "ADMIN": HandleAdminCommand,
    }
    
    def OnLoad(self, context: PluginContext) -> None:
        super().OnLoad(context)
        self.logger.info("Admin plugin loaded")
    
    def GetHelpText(self) -> str:
        return "ADMIN <pwd> CREATE|DELETE|DELPOST|LIST|POSTS"
