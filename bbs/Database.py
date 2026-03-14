"""
Database Module

This module provides SQLite database functionality for the BBS server.

Purpose:
    - Manage SQLite database connection
    - Handle database schema creation and migrations
    - Provide CRUD operations for all data types
    - Track schema version for migration support

Key Classes:
    - Database: Main database interface
    - Node: Represents a node in the mesh network
    - Message: Represents a personal message
    - BbsArea: Represents a BBS bulletin board area
    - BbsPost: Represents a post in a BBS area

Data Models:
    - Nodes: Known mesh nodes
    - Messages: Personal messages between nodes
    - BbsAreas: Bulletin board areas (forums)
    - BbsPosts: Posts within bulletin board areas

Usage:
    db = Database("/var/lib/meshtastic-bbs/bbs.db", logger)
    db.Initialize()
    db.RegisterNode("!abcd1234", "MyNode")
    db.SaveMessage(message)
    messages = db.GetMessagesForNode("!abcd1234")
"""

import sqlite3
import json
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
from enum import Enum

from bbs.Logger import GetLogger


class SchemaVersion(Enum):
    """Database schema version for tracking migrations."""
    INITIAL = 1
    CURRENT = 1


@dataclass
class Node:
    """
    Represents a node in the Meshtastic mesh network.
    
    Attributes:
        id: Unique node identifier (e.g., "!abcd1234")
        name: Optional human-readable name
        last_seen: Unix timestamp of last activity
        metadata: Additional metadata as JSON
    """
    id: str
    name: Optional[str] = None
    last_seen: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Message:
    """
    Represents a personal message between two nodes.
    
    Attributes:
        id: Unique message identifier (auto-generated)
        from_node: Node ID of sender
        to_node: Node ID of recipient
        subject: Optional subject line
        body: Message content
        created_at: Unix timestamp of creation
        read: Whether the message has been read
    """
    id: Optional[int] = None
    from_node: str = ""
    to_node: str = ""
    subject: Optional[str] = None
    body: str = ""
    created_at: Optional[int] = None
    read: bool = False


@dataclass
class BbsArea:
    """
    Represents a BBS bulletin board area (forum/topic).
    
    Attributes:
        id: Unique area identifier (auto-generated)
        name: Area name (e.g., "general", "for-sale")
        description: Human-readable description
        created_at: Unix timestamp of creation
    """
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_at: Optional[int] = None


@dataclass
class BbsPost:
    """
    Represents a post in a BBS area.
    
    Attributes:
        id: Unique post identifier (auto-generated)
        area_id: ID of the BBS area this post belongs to
        from_node: Node ID of the poster
        subject: Optional subject line
        body: Post content
        created_at: Unix timestamp of creation
    """
    id: Optional[int] = None
    area_id: int = 0
    from_node: str = ""
    subject: Optional[str] = None
    body: str = ""
    created_at: Optional[int] = None


class Database:
    """
    SQLite database interface for the BBS server.
    
    This class manages all database operations including:
    - Schema initialization and migrations
    - Node registration and lookup
    - Personal message storage and retrieval
    - BBS area and post management
    
    Attributes:
        database_path: Path to the SQLite database file
    """
    
    def __init__(self, database_path: str, logger=None):
        """
        Initialize the database interface.
        
        Args:
            database_path: Path to SQLite database file
            logger: Optional logger instance
        """
        self.database_path = database_path
        self.logger = logger or GetLogger("Database")
        self.connection: Optional[sqlite3.Connection] = None
    
    def Initialize(self) -> None:
        """
        Initialize the database connection and create schema.
        
        This function:
        - Creates the database directory if needed
        - Establishes database connection
        - Creates tables if they don't exist
        - Runs any pending migrations
        
        Raises:
            sqlite3.Error: If database operations fail
        """
        # Ensure database directory exists
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        
        # Enable foreign keys
        self.connection.execute("PRAGMA foreign_keys = ON")
        
        # Create schema
        self._CreateSchema()
        
        # Run migrations
        self._Migrate()
        
        self.logger.info(f"Database initialized at {self.database_path}")
    
    def Close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("Database connection closed")
    
    def _CreateSchema(self) -> None:
        """Create all database tables."""
        # Schema version tracking
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)
        
        # Nodes table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                name TEXT,
                last_seen INTEGER,
                metadata TEXT
            )
        """)
        
        # Personal messages table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_node TEXT NOT NULL,
                to_node TEXT NOT NULL,
                subject TEXT,
                body TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                read INTEGER DEFAULT 0,
                FOREIGN KEY (from_node) REFERENCES nodes(id),
                FOREIGN KEY (to_node) REFERENCES nodes(id)
            )
        """)
        
        # BBS Areas table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS bbs_areas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at INTEGER NOT NULL
            )
        """)
        
        # BBS Posts table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS bbs_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area_id INTEGER NOT NULL,
                from_node TEXT NOT NULL,
                subject TEXT,
                body TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (area_id) REFERENCES bbs_areas(id),
                FOREIGN KEY (from_node) REFERENCES nodes(id)
            )
        """)
        
        # Create indexes for common queries
        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_to_node ON messages(to_node)
        """)
        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_from_node ON messages(from_node)
        """)
        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_bbs_posts_area_id ON bbs_posts(area_id)
        """)
        
        self.connection.commit()
    
    def _Migrate(self) -> None:
        """Run database migrations."""
        # Get current schema version
        cursor = self.connection.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        )
        row = cursor.fetchone()
        
        if row is None:
            # No schema version, set initial version
            self.connection.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SchemaVersion.INITIAL.value,)
            )
            self.connection.commit()
            self.logger.info(f"Database schema initialized at version {SchemaVersion.INITIAL.value}")
        
        current_version = row['version'] if row else 0
        
        # Run any needed migrations
        # For now, we only have version 1, so no migrations needed
        if current_version < SchemaVersion.CURRENT.value:
            self.logger.warning(f"Database schema version {current_version} is older than expected")
    
    # ==================== Node Operations ====================
    
    def RegisterNode(self, node_id: str, name: str = None) -> None:
        """
        Register or update a node in the database.
        
        Args:
            node_id: Unique node identifier
            name: Optional human-readable name
        """
        now = int(time.time())
        
        self.connection.execute("""
            INSERT INTO nodes (id, name, last_seen)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = COALESCE(?, name),
                last_seen = ?
        """, (node_id, name, now, name, now))
        
        self.connection.commit()
    
    def GetNode(self, node_id: str) -> Optional[Node]:
        """
        Get a node by ID.
        
        Args:
            node_id: Node identifier to look up
            
        Returns:
            Node object if found, None otherwise
        """
        cursor = self.connection.execute(
            "SELECT * FROM nodes WHERE id = ?",
            (node_id,)
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        metadata = None
        if row['metadata']:
            metadata = json.loads(row['metadata'])
        
        return Node(
            id=row['id'],
            name=row['name'],
            last_seen=row['last_seen'],
            metadata=metadata
        )
    
    def GetAllNodes(self) -> List[Node]:
        """
        Get all known nodes.
        
        Returns:
            List of all Node objects
        """
        cursor = self.connection.execute("SELECT * FROM nodes ORDER BY last_seen DESC")
        rows = cursor.fetchall()
        
        nodes = []
        for row in rows:
            metadata = None
            if row['metadata']:
                metadata = json.loads(row['metadata'])
            
            nodes.append(Node(
                id=row['id'],
                name=row['name'],
                last_seen=row['last_seen'],
                metadata=metadata
            ))
        
        return nodes
    
    def UpdateNodeLastSeen(self, node_id: str) -> None:
        """
        Update the last_seen timestamp for a node.
        
        Args:
            node_id: Node identifier to update
        """
        now = int(time.time())
        self.connection.execute(
            "UPDATE nodes SET last_seen = ? WHERE id = ?",
            (now, node_id)
        )
        self.connection.commit()
    
    # ==================== Message Operations ====================
    
    def SaveMessage(self, message: Message) -> int:
        """
        Save a personal message to the database.
        
        Args:
            message: Message object to save
            
        Returns:
            The ID of the newly created message
        """
        created_at = message.created_at or int(time.time())
        
        cursor = self.connection.execute("""
            INSERT INTO messages (from_node, to_node, subject, body, created_at, read)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            message.from_node,
            message.to_node,
            message.subject,
            message.body,
            created_at,
            1 if message.read else 0
        ))
        
        self.connection.commit()
        
        # Register both nodes if they don't exist
        self.RegisterNode(message.from_node)
        self.RegisterNode(message.to_node)
        
        return cursor.lastrowid
    
    def GetMessagesForNode(self, node_id: str, unread_only: bool = False) -> List[Message]:
        """
        Get all messages for a specific node.
        
        Args:
            node_id: The node to get messages for
            unread_only: If True, only return unread messages
            
        Returns:
            List of Message objects
        """
        if unread_only:
            query = "SELECT * FROM messages WHERE to_node = ? AND read = 0 ORDER BY created_at DESC"
        else:
            query = "SELECT * FROM messages WHERE to_node = ? ORDER BY created_at DESC"
        
        cursor = self.connection.execute(query, (node_id,))
        rows = cursor.fetchall()
        
        messages = []
        for row in rows:
            messages.append(Message(
                id=row['id'],
                from_node=row['from_node'],
                to_node=row['to_node'],
                subject=row['subject'],
                body=row['body'],
                created_at=row['created_at'],
                read=bool(row['read'])
            ))
        
        return messages
    
    def GetMessageById(self, message_id: int) -> Optional[Message]:
        """
        Get a specific message by ID.
        
        Args:
            message_id: The message ID to retrieve
            
        Returns:
            Message object if found, None otherwise
        """
        cursor = self.connection.execute(
            "SELECT * FROM messages WHERE id = ?",
            (message_id,)
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return Message(
            id=row['id'],
            from_node=row['from_node'],
            to_node=row['to_node'],
            subject=row['subject'],
            body=row['body'],
            created_at=row['created_at'],
            read=bool(row['read'])
        )
    
    def MarkMessageAsRead(self, message_id: int) -> None:
        """
        Mark a message as read.
        
        Args:
            message_id: The message ID to mark as read
        """
        self.connection.execute(
            "UPDATE messages SET read = 1 WHERE id = ?",
            (message_id,)
        )
        self.connection.commit()
    
    def DeleteMessage(self, message_id: int) -> None:
        """
        Delete a message from the database.
        
        Args:
            message_id: The message ID to delete
        """
        self.connection.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        self.connection.commit()
    
    def GetUnreadMessageCount(self, node_id: str) -> int:
        """
        Get the count of unread messages for a node.
        
        Args:
            node_id: The node to count messages for
            
        Returns:
            Number of unread messages
        """
        cursor = self.connection.execute(
            "SELECT COUNT(*) as count FROM messages WHERE to_node = ? AND read = 0",
            (node_id,)
        )
        row = cursor.fetchone()
        return row['count'] if row else 0
    
    # ==================== BBS Area Operations ====================
    
    def GetAllAreas(self) -> List[BbsArea]:
        """
        Get all BBS areas.
        
        Returns:
            List of BbsArea objects ordered by name
        """
        cursor = self.connection.execute(
            "SELECT * FROM bbs_areas ORDER BY name"
        )
        rows = cursor.fetchall()
        
        areas = []
        for row in rows:
            areas.append(BbsArea(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                created_at=row['created_at']
            ))
        
        return areas
    
    def GetAreaByName(self, name: str) -> Optional[BbsArea]:
        """
        Get a BBS area by name.
        
        Args:
            name: The area name to look up
            
        Returns:
            BbsArea object if found, None otherwise
        """
        cursor = self.connection.execute(
            "SELECT * FROM bbs_areas WHERE name = ?",
            (name.lower(),)
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return BbsArea(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            created_at=row['created_at']
        )
    
    def CreateArea(self, name: str, description: str = "") -> BbsArea:
        """
        Create a new BBS area.
        
        Args:
            name: The area name (will be stored lowercase)
            description: Human-readable description
            
        Returns:
            The newly created BbsArea object
            
        Raises:
            sqlite3.IntegrityError: If area with name already exists
        """
        now = int(time.time())
        
        cursor = self.connection.execute("""
            INSERT INTO bbs_areas (name, description, created_at)
            VALUES (?, ?, ?)
        """, (name.lower(), description, now))
        
        self.connection.commit()
        
        return BbsArea(
            id=cursor.lastrowid,
            name=name.lower(),
            description=description,
            created_at=now
        )
    
    # ==================== BBS Post Operations ====================
    
    def SavePost(self, post: BbsPost) -> int:
        """
        Save a BBS post to the database.
        
        Args:
            post: BbsPost object to save
            
        Returns:
            The ID of the newly created post
        """
        created_at = post.created_at or int(time.time())
        
        cursor = self.connection.execute("""
            INSERT INTO bbs_posts (area_id, from_node, subject, body, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            post.area_id,
            post.from_node,
            post.subject,
            post.body,
            created_at
        ))
        
        self.connection.commit()
        
        # Register the node if needed
        self.RegisterNode(post.from_node)
        
        return cursor.lastrowid
    
    def GetPostsForArea(self, area_name: str) -> List[BbsPost]:
        """
        Get all posts in a BBS area.
        
        Args:
            area_name: The area name to get posts from
            
        Returns:
            List of BbsPost objects ordered by creation time (newest first)
        """
        cursor = self.connection.execute("""
            SELECT bp.* FROM bbs_posts bp
            JOIN bbs_areas ba ON bp.area_id = ba.id
            WHERE ba.name = ?
            ORDER BY bp.created_at DESC
        """, (area_name.lower(),))
        
        rows = cursor.fetchall()
        
        posts = []
        for row in rows:
            posts.append(BbsPost(
                id=row['id'],
                area_id=row['area_id'],
                from_node=row['from_node'],
                subject=row['subject'],
                body=row['body'],
                created_at=row['created_at']
            ))
        
        return posts
    
    def GetPostById(self, post_id: int) -> Optional[BbsPost]:
        """
        Get a specific post by ID.
        
        Args:
            post_id: The post ID to retrieve
            
        Returns:
            BbsPost object if found, None otherwise
        """
        cursor = self.connection.execute(
            "SELECT * FROM bbs_posts WHERE id = ?",
            (post_id,)
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return BbsPost(
            id=row['id'],
            area_id=row['area_id'],
            from_node=row['from_node'],
            subject=row['subject'],
            body=row['body'],
            created_at=row['created_at']
        )
    
    def DeletePost(self, post_id: int) -> None:
        """
        Delete a post from the database.
        
        Args:
            post_id: The post ID to delete
        """
        self.connection.execute("DELETE FROM bbs_posts WHERE id = ?", (post_id,))
        self.connection.commit()
    
    def GetPostCountForArea(self, area_name: str) -> int:
        """
        Get the count of posts in an area.
        
        Args:
            area_name: The area name
            
        Returns:
            Number of posts in the area
        """
        cursor = self.connection.execute("""
            SELECT COUNT(*) as count FROM bbs_posts bp
            JOIN bbs_areas ba ON bp.area_id = ba.id
            WHERE ba.name = ?
        """, (area_name.lower(),))
        
        row = cursor.fetchone()
        return row['count'] if row else 0
