# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Base command processor implementing the template method pattern.

This module provides the abstract base class for all CLI commands,
defining the common execution flow and shared infrastructure.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

from ..als_client import ALSClient
from ..cleanup_handler import cleanup_on_signal
from ..logging_setup import redirect_stderr, setup_logging
from ..metrics import Metrics
from ..tui import TUI

T = TypeVar('T')  # Result type for command


class CommandArgs:
    """Base arguments shared by all commands."""
    
    verbose: bool
    quiet: bool
    als_command: list[str]
    color: bool
    workers: int
    

class CommandProcessor(ABC, Generic[T]):
    """
    Base processor for all CLI commands.
    
    Implements the template method pattern to define common execution flow:
    1. Setup environment (logging, signals, UI)
    2. Initialize ALS client
    3. Discover targets (files, symbols, etc.)
    4. Process targets (command-specific)
    5. Finalize (cleanup, reporting)
    """
    
    def __init__(self):
        self.metrics = Metrics()
        self.tui: TUI | None = None
        self.als_client: ALSClient | None = None
    
    async def execute(self, args: CommandArgs) -> int:
        """
        Template method defining the common execution flow.
        
        Args:
            args: Command-specific arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Setup phase
            await self.setup_environment(args)
            
            # Initialize ALS if needed
            if self.requires_als():
                self.als_client = await self.initialize_als(args)
            
            # Discovery phase
            targets = await self.discover_targets(args)
            if not targets:
                await self.log_info("No targets found to process")
                return 0
            
            # Processing phase (command-specific)
            results = await self.process_targets(targets, args)
            
            # Finalization phase
            return await self.finalize(results, args)
            
        except KeyboardInterrupt:
            await self.log_info("\nOperation cancelled by user")
            return 130
        except Exception as e:
            await self.handle_error(e, args)
            return 1
        finally:
            await self.cleanup()
    
    async def setup_environment(self, args: CommandArgs) -> None:
        """
        Common environment setup for all commands.
        
        Sets up logging, signal handlers, stderr redirection, and UI.
        """
        # Setup logging
        setup_logging(verbose=args.verbose)
        
        # Redirect stderr if quiet mode
        if args.quiet:
            redirect_stderr()
        
        # Setup signal handlers for graceful shutdown
        cleanup_on_signal()
        
        # Initialize UI if not quiet
        if not args.quiet and self.supports_ui():
            self.tui = TUI()
            await self.tui.start()
    
    async def initialize_als(self, args: CommandArgs) -> ALSClient:
        """
        Initialize the Ada Language Server client.
        
        Args:
            args: Command arguments containing ALS command
            
        Returns:
            Initialized ALS client
        """
        als_client = ALSClient(
            als_command=args.als_command,
            startup_timeout=30.0,
            request_timeout=60.0
        )
        
        await self.log_info("Starting Ada Language Server...")
        await als_client.start()
        
        # Wait for ALS to be ready
        await als_client.wait_until_ready()
        await self.log_info("Ada Language Server ready")
        
        return als_client
    
    @abstractmethod
    async def discover_targets(self, args: CommandArgs) -> list[Any]:
        """
        Discover targets to process (files, symbols, etc.).
        
        Args:
            args: Command arguments
            
        Returns:
            List of targets to process
        """
        pass
    
    @abstractmethod
    async def process_targets(
        self, 
        targets: list[Any], 
        args: CommandArgs
    ) -> list[T]:
        """
        Process discovered targets.
        
        This is the main command-specific logic.
        
        Args:
            targets: Targets to process
            args: Command arguments
            
        Returns:
            List of results
        """
        pass
    
    async def finalize(self, results: list[T], args: CommandArgs) -> int:
        """
        Finalize command execution with reporting.
        
        Args:
            results: Processing results
            args: Command arguments
            
        Returns:
            Exit code
        """
        # Calculate success/failure
        successful = sum(1 for r in results if self.is_successful(r))
        failed = len(results) - successful
        
        # Update metrics
        self.metrics.successful_files = successful
        self.metrics.failed_files = failed
        
        # Report results
        await self.report_results(results, args)
        
        return 0 if failed == 0 else 1
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.als_client:
            await self.als_client.shutdown()
        
        if self.tui:
            await self.tui.stop()
    
    async def handle_error(self, error: Exception, args: CommandArgs) -> None:
        """
        Handle command-level errors.
        
        Args:
            error: The exception that occurred
            args: Command arguments
        """
        await self.log_error(f"Command failed: {error}")
        if args.verbose:
            import traceback
            await self.log_error(traceback.format_exc())
    
    # Helper methods for subclasses
    
    async def log_info(self, message: str) -> None:
        """Log info message to UI or console."""
        if self.tui:
            await self.tui.update_status(message)
        else:
            print(message)
    
    async def log_error(self, message: str) -> None:
        """Log error message."""
        if self.tui:
            await self.tui.add_error(message)
        else:
            print(f"ERROR: {message}")
    
    async def update_progress(self, current: int, total: int) -> None:
        """Update progress in UI."""
        if self.tui:
            await self.tui.update_progress(current, total)
    
    # Abstract methods for subclasses to override
    
    @abstractmethod
    def is_successful(self, result: T) -> bool:
        """
        Determine if a result represents success.
        
        Args:
            result: Processing result
            
        Returns:
            True if successful
        """
        pass
    
    def requires_als(self) -> bool:
        """
        Whether this command requires ALS.
        
        Override to return False for commands that don't need ALS.
        """
        return True
    
    def supports_ui(self) -> bool:
        """
        Whether this command supports TUI.
        
        Override to return False for simple commands.
        """
        return True
    
    @abstractmethod
    async def report_results(self, results: list[T], args: CommandArgs) -> None:
        """
        Report command results.
        
        Args:
            results: Processing results
            args: Command arguments
        """
        pass