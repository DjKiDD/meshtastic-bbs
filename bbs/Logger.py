"""
Logger Module

This module provides logging functionality for the BBS server.

Purpose:
    - Configure logging from settings
    - Create loggers for different components
    - Handle both file and console output
    - Provide consistent log formatting

Key Classes:
    - Logger: Wrapper around Python logging with BBS-specific configuration

Usage:
    logger = Logger.SetupLogging(config)
    logger.Info("Server started")
"""

import logging
import sys
from typing import Optional
from pathlib import Path


class Logger:
    """
    Logging configuration and management for the BBS server.
    
    This class provides static methods to set up and configure logging
    for the entire application.
    """
    
    # Root logger name for the BBS application
    ROOT_LOGGER_NAME = "meshtastic-bbs"
    
    @staticmethod
    def SetupLogging(
        level: str,
        log_file: Optional[str] = None,
        log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ) -> logging.Logger:
        """
        Set up logging for the application.
        
        This function configures the root logger with the specified
        settings including log level, output destinations, and format.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (None for stdout only)
            log_format: Format string for log messages
            
        Returns:
            Configured logger instance
            
        Note:
            This function configures the root logger, so all child loggers
            will inherit this configuration.
        """
        # Convert string level to logging constant
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        
        # Create root logger
        root_logger = logging.getLogger(Logger.ROOT_LOGGER_NAME)
        root_logger.setLevel(numeric_level)
        
        # Remove any existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(log_format)
        
        # Add console handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Add file handler if log file is specified
        if log_file:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # Return the root logger
        return root_logger
    
    @staticmethod
    def GetLogger(name: str) -> logging.Logger:
        """
        Get a logger instance for a specific component.
        
        This function creates or retrieves a logger with the specified
        name under the root BBS logger namespace.
        
        Args:
            name: Name of the component (e.g., "Database", "SerialManager")
            
        Returns:
            Logger instance for the component
            
        Example:
            logger = Logger.GetLogger("Database")
            logger.Info("Connected to database")
        """
        # Create logger under root namespace
        full_name = f"{Logger.ROOT_LOGGER_NAME}.{name}"
        return logging.getLogger(full_name)
    
    @staticmethod
    def GetRootLogger() -> logging.Logger:
        """
        Get the root logger for the BBS application.
        
        Returns:
            The root logger instance
        """
        return logging.getLogger(Logger.ROOT_LOGGER_NAME)
    
    @staticmethod
    def SetLevel(level: str) -> None:
        """
        Change the log level for all handlers.
        
        Args:
            level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        root_logger = logging.getLogger(Logger.ROOT_LOGGER_NAME)
        root_logger.setLevel(numeric_level)
        
        # Update all handlers
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)
    
    @staticmethod
    def AddFileHandler(log_file: str, level: str = "INFO") -> None:
        """
        Add a file handler to the root logger.
        
        Args:
            log_file: Path to log file
            level: Log level for this handler
            
        Note:
            The directory containing the log file will be created if it doesn't exist.
        """
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create handler
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        
        # Add to root logger
        root_logger = logging.getLogger(Logger.ROOT_LOGGER_NAME)
        root_logger.addHandler(file_handler)


# Convenience function for quick logging setup
def SetupLogging(level: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Convenience function to quickly set up logging.
    
    This is a simple wrapper around Logger.SetupLogging().
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional path to log file
        
    Returns:
        Configured logger instance
    """
    return Logger.SetupLogging(level, log_file)


def GetLogger(name: str) -> logging.Logger:
    """
    Convenience function to get a component logger.
    
    This is a simple wrapper around Logger.GetLogger().
    
    Args:
        name: Name of the component
        
    Returns:
        Logger instance
    """
    return Logger.GetLogger(name)
