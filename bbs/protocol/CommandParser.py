"""
Command Parser Module

This module handles parsing incoming text commands from the mesh.

Purpose:
    - Parse text input into structured command objects
    - Validate command format
    - Handle command arguments
    - Support various command formats

Command Format:
    Commands are space-separated, with the command name first:
        COMMAND arg1 arg2 arg3 ...
    
    Example:
        MSG !abcd1234 Hello there
        BBS general This is a post
        READ

Key Classes:
    - ParsedCommand: Structured representation of a parsed command
    - CommandParser: Parses raw text into ParsedCommand objects

Usage:
    parser = CommandParser()
    result = parser.ParseCommand("MSG !abcd1234 Hello")
    
    if result.IsValid:
        command = result.Command
        args = result.Arguments
"""

import re
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class ParseResult(Enum):
    """Result of trying to parse a command."""
    SUCCESS = "success"
    EMPTY_INPUT = "empty_input"
    UNKNOWN_COMMAND = "unknown_command"
    INVALID_FORMAT = "invalid_format"
    MISSING_ARGUMENTS = "missing_arguments"


@dataclass
class ParsedCommand:
    """
    Represents a parsed command from user input.
    
    Attributes:
        command: The command name (uppercase)
        arguments: List of arguments after the command
        raw_input: The original raw input string
        is_valid: Whether parsing was successful
        error_message: Error message if parsing failed
    """
    command: str
    arguments: List[str]
    raw_input: str
    is_valid: bool = True
    error_message: Optional[str] = None


class CommandParser:
    """
    Parses text commands from Meshtastic packets.
    
    This class handles:
    - Splitting input into command and arguments
    - Validating command format
    - Cleaning and normalizing input
    
    The parser is fairly lenient and accepts various formats:
        COMMAND arg1 arg2
        COMMAND arg1 arg2 "multi word arg"
        command (lowercase also works)
    """
    
    # Maximum length of input we'll process
    MAX_INPUT_LENGTH = 500
    
    # Minimum command length
    MIN_COMMAND_LENGTH = 1
    
    def __init__(self):
        """Initialize the command parser."""
        pass
    
    def ParseCommand(self, input_text: str) -> ParsedCommand:
        """
        Parse raw input text into a command.
        
        This function:
        - Strips whitespace from ends
        - Splits into command and arguments
        - Uppercases the command
        - Handles quoted arguments
        
        Args:
            input_text: Raw text from the packet
            
        Returns:
            ParsedCommand object with parsing results
            
        Note:
            Even if parsing fails, a ParsedCommand is returned
            with is_valid=False and an error_message.
        """
        # Handle empty input
        if not input_text or not input_text.strip():
            return ParsedCommand(
                command="",
                arguments=[],
                raw_input=input_text or "",
                is_valid=False,
                error_message="Empty input"
            )
        
        # Trim input
        input_text = input_text.strip()
        
        # Check length
        if len(input_text) > self.MAX_INPUT_LENGTH:
            return ParsedCommand(
                command="",
                arguments=[],
                raw_input=input_text,
                is_valid=False,
                error_message=f"Input too long (max {self.MAX_INPUT_LENGTH})"
            )
        
        # Split into parts - handle quoted strings
        parts = self._SplitWithQuotes(input_text)
        
        if not parts:
            return ParsedCommand(
                command="",
                arguments=[],
                raw_input=input_text,
                is_valid=False,
                error_message="No command found"
            )
        
        # Extract command (first part)
        command = parts[0].upper()
        
        # Extract arguments (rest of parts)
        arguments = parts[1:] if len(parts) > 1 else []
        
        return ParsedCommand(
            command=command,
            arguments=arguments,
            raw_input=input_text,
            is_valid=True
        )
    
    def _SplitWithQuotes(self, text: str) -> List[str]:
        """
        Split text into parts, respecting quoted strings.
        
        This handles arguments like:
            MSG !node Hello world    -> ["MSG", "!node", "Hello", "world"]
            MSG !node "Hello world" -> ["MSG", "!node", "Hello world"]
        
        Args:
            text: Text to split
            
        Returns:
            List of parts
        """
        parts = []
        current = ""
        in_quotes = False
        
        for char in text:
            if char == '"':
                # Toggle quote mode
                in_quotes = not in_quotes
            elif char == ' ' and not in_quotes:
                # Space outside quotes - split here
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
        
        # Add last part
        if current:
            parts.append(current)
        
        return parts
    
    def ValidateCommand(
        self, 
        parsed: ParsedCommand, 
        valid_commands: List[str],
        min_args: int = 0
    ) -> ParsedCommand:
        """
        Validate a parsed command.
        
        This function checks:
        - Command is in the list of valid commands
        - Minimum number of arguments are present
        
        Args:
            parsed: The parsed command to validate
            valid_commands: List of valid command names
            min_args: Minimum number of arguments required
            
        Returns:
            The same ParsedCommand (modified in place)
        """
        if not parsed.is_valid:
            return parsed
        
        # Check command is valid
        if parsed.command not in valid_commands:
            parsed.is_valid = False
            parsed.error_message = f"Unknown command: {parsed.command}"
            return parsed
        
        # Check minimum arguments
        if len(parsed.arguments) < min_args:
            parsed.is_valid = False
            parsed.error_message = f"Missing arguments (need {min_args}, got {len(parsed.arguments)})"
            return parsed
        
        return parsed
    
    def GetCommandOnly(self, input_text: str) -> str:
        """
        Extract just the command part from input.
        
        This is a quick way to get just the command without
        full parsing, useful for help commands.
        
        Args:
            input_text: Raw input text
            
        Returns:
            Uppercase command name, or empty string
        """
        if not input_text:
            return ""
        
        parts = input_text.strip().split()
        if parts:
            return parts[0].upper()
        
        return ""
    
    def ExtractNodeId(self, text: str) -> Optional[str]:
        """
        Extract a Meshtastic node ID from text.
        
        Node IDs typically start with ! followed by hex:
            !abcd1234
        
        Args:
            text: Text to search
            
        Returns:
            Node ID if found, None otherwise
        """
        if not text:
            return None
        
        # Pattern for Meshtastic node ID
        # Starts with ! followed by 8+ hex characters
        pattern = r'![0-9a-fA-F]{8,}'
        
        match = re.search(pattern, text)
        if match:
            return match.group(0).upper()
        
        return None
    
    def FormatHelp(self, commands: List[str]) -> str:
        """
        Format a list of available commands for display.
        
        Args:
            commands: List of valid command names
            
        Returns:
            Formatted help string
        """
        lines = [
            "Available commands:",
            "",
        ]
        
        for cmd in sorted(commands):
            lines.append(f"  {cmd}")
        
        lines.append("")
        lines.append("Type HELP <command> for more info")
        
        return "\n".join(lines)
