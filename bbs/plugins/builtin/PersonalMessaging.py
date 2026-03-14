"""
Personal Messaging Plugin

This plugin handles personal message commands between nodes.

Commands:
    MSG <recipient_node> <message>
        Send a personal message to another node
        
    READ [message_id]
        Read your messages. Without args, lists all messages.
        With message_id, shows that specific message.
        
    DELETE <message_id>
        Delete a message from your inbox

Usage:
    MSG !abcd1234 Hello there
    READ
    READ 5
    DELETE 5
"""

import time
from bbs.plugins.BasePlugin import BasePlugin, PluginContext
from bbs.Database import Message
from bbs.protocol.CommandRouter import HandlerContext


# Handler functions - defined before the class that references them

def HandleSendMessage(context: HandlerContext) -> str:
    """
    Handle the MSG command to send a personal message.
    
    Usage: MSG <recipient_node> <message>
    
    This function:
    - Validates the arguments
    - Creates a message record in the database
    - Sends a delivery notification to the recipient
    
    Args:
        context: Handler context with arguments and services
        
    Returns:
        Response message to send back to sender
    """
    # Check arguments
    if len(context.arguments) < 2:
        return "Usage: MSG <node_id> <message>"
    
    # Extract recipient and message
    recipient_node = context.arguments[0].upper()
    message_text = " ".join(context.arguments[1:])
    
    # Validate node ID format
    if not recipient_node.startswith("!"):
        return "Error: Invalid node ID format. Must start with !"
    
    # Check message length
    if len(message_text) > 500:
        return f"Error: Message too long (max 500 characters)"
    
    # Create message record
    message = Message(
        from_node=context.from_node,
        to_node=recipient_node,
        body=message_text,
        created_at=int(time.time()),
        read=False
    )
    
    # Save to database
    message_id = context.database.SaveMessage(message)
    
    # Build response to sender
    response_lines = [
        f"Message sent to {recipient_node}",
        f"Message ID: {message_id}",
        "",
        f"Message: {message_text[:100]}..." if len(message_text) > 100 else f"Message: {message_text}",
    ]
    
    return "\n".join(response_lines)


def HandleReadMessages(context: HandlerContext) -> str:
    """
    Handle the READ command to read messages.
    
    Usage: READ
           READ <message_id>
    
    Without arguments, lists all messages for the sender.
    With a message_id, shows that specific message.
    
    Args:
        context: Handler context with arguments and services
        
    Returns:
        Response with messages
    """
    from datetime import datetime
    
    # Check if reading specific message
    if context.arguments:
        try:
            message_id = int(context.arguments[0])
        except ValueError:
            return "Error: Invalid message ID. Must be a number."
        
        # Get the message
        message = context.database.GetMessageById(message_id)
        
        if message is None:
            return f"Error: Message {message_id} not found."
        
        # Check if sender is recipient or sender
        if message.to_node != context.from_node and message.from_node != context.from_node:
            return f"Error: You don't have access to message {message_id}."
        
        # Mark as read
        if message.to_node == context.from_node:
            context.database.MarkMessageAsRead(message_id)
        
        # Format message
        timestamp = datetime.fromtimestamp(message.created_at).strftime("%Y-%m-%d %H:%M")
        
        lines = [
            f"=== Message {message_id} ===",
            f"From: {message.from_node}",
            f"Date: {timestamp}",
            "",
            message.body,
        ]
        
        return "\n".join(lines)
    
    # List all messages
    messages = context.database.GetMessagesForNode(context.from_node)
    
    if not messages:
        return "You have no messages."
    
    # Get unread count
    unread_count = context.database.GetUnreadMessageCount(context.from_node)
    
    lines = [
        f"=== Your Messages ({len(messages)} total, {unread_count} unread) ===",
        "",
    ]
    
    # Show message summaries
    for msg in messages[:20]:  # Limit to 20
        timestamp = datetime.fromtimestamp(msg.created_at).strftime("%m/%d %H:%M")
        status = "NEW" if not msg.read else "   "
        lines.append(f"[{msg.id:3d}] {status} {timestamp} From: {msg.from_node}")
        
        # Show first part of message
        preview = msg.body[:40].replace("\n", " ")
        lines.append(f"       {preview}...")
        lines.append("")
    
    if len(messages) > 20:
        lines.append(f"... and {len(messages) - 20} more messages")
    
    lines.append("")
    lines.append("Type READ <message_id> to read a message")
    lines.append("Type DELETE <message_id> to delete a message")
    
    return "\n".join(lines)


def HandleDeleteMessage(context: HandlerContext) -> str:
    """
    Handle the DELETE command to delete a message.
    
    Usage: DELETE <message_id>
    
    Deletes a message from the sender's inbox.
    Only the recipient can delete a message.
    
    Args:
        context: Handler context with arguments and services
        
    Returns:
        Response message
    """
    # Check arguments
    if not context.arguments:
        return "Usage: DELETE <message_id>"
    
    try:
        message_id = int(context.arguments[0])
    except ValueError:
        return "Error: Invalid message ID. Must be a number."
    
    # Get the message
    message = context.database.GetMessageById(message_id)
    
    if message is None:
        return f"Error: Message {message_id} not found."
    
    # Only recipient can delete
    if message.to_node != context.from_node:
        return f"Error: You can only delete messages in your inbox."
    
    # Delete the message
    context.database.DeleteMessage(message_id)
    
    return f"Message {message_id} deleted."


class PersonalMessagingPlugin(BasePlugin):
    """
    Plugin for handling personal messages between nodes.
    
    This plugin allows nodes to send and receive personal messages
    through the BBS, even when they're not directly connected.
    
    Commands:
        MSG: Send a personal message
        READ: Read messages
        DELETE: Delete a message
    """
    
    # Plugin metadata
    Name = "personal_messaging"
    Version = "1.0.0"
    Description = "Send and receive personal messages"
    
    # Command handlers - maps command name to handler method
    CommandHandlers = {
        "MSG": HandleSendMessage,
        "READ": HandleReadMessages,
        "DELETE": HandleDeleteMessage,
    }
    
    def OnLoad(self, context: PluginContext) -> None:
        """
        Initialize the personal messaging plugin.
        
        Called when the plugin is loaded. Sets up the context
        and logs the plugin initialization.
        
        Args:
            context: Plugin context with database and config access
        """
        super().OnLoad(context)
        
        # Get plugin-specific config
        plugin_config = context.GetPluginConfiguration(self.Name)
        
        # Store max message length
        self.max_message_length = plugin_config.get("max_message_length", 500)
        self.max_subject_length = plugin_config.get("max_subject_length", 50)
        
        self.logger.info(
            f"Personal Messaging loaded - max message: {self.max_message_length}"
        )
    
    def GetHelpText(self) -> str:
        """
        Get help text for personal messaging commands.
        
        Returns:
            Formatted help string
        """
        lines = [
            "=== Personal Messaging ===",
            "",
            "MSG <node_id> <message>",
            "  Send a personal message to another node",
            "  Example: MSG !abcd1234 Hello friend!",
            "",
            "READ",
            "  List all your messages",
            "",
            "READ <message_id>",
            "  Read a specific message",
            "",
            "DELETE <message_id>",
            "  Delete a message from your inbox",
            "",
        ]
        
        return "\n".join(lines)
