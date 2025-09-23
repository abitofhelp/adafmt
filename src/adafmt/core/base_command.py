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
from typing import Any, Generic, TypeVar

from returns.future import FutureResult, future_safe
from returns.io import IOResult
from returns.result import Failure, Result, Success

from ..als_client import ALSClient
from ..cleanup_handler import setup_cleanup_handlers
from ..errors import AdafmtError
from ..metrics import MetricsCollector
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ui_base import BaseUI

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
        self.metrics = MetricsCollector()
        self.tui: BaseUI | None = None if TYPE_CHECKING else None
        self.als_client: ALSClient | None = None
    
    async def execute(self, args: CommandArgs) -> Result[int, AdafmtError]:
        """
        Template method defining the common execution flow using functional error handling.
        
        Args:
            args: Command-specific arguments
            
        Returns:
            Result[int, AdafmtError]: Exit code on success or error
        """
        # Execute internal method which returns FutureResult[int, Exception]
        result = await self._execute_internal(args)
        
        # Check if it's a success - if so, return as-is since int maps correctly
        if isinstance(result, Success):
            return result  # Success[int] is valid as Result[int, AdafmtError]
        
        # Handle failures - need to convert Exception to AdafmtError
        exc = result.failure()
        
        if isinstance(exc, KeyboardInterrupt):
            # For keyboard interrupt, log and return special exit code
            await self.log_info("\nOperation cancelled by user")
            return Success(130)
        elif isinstance(exc, AdafmtError):
            # Already an AdafmtError, wrap in Failure
            return Failure(exc)
        else:
            # Convert other exceptions to AdafmtError
            return Failure(AdafmtError(
                message=f"Unexpected error: {exc}"
            ))
    
    @future_safe
    async def _execute_internal(self, args: CommandArgs) -> int:
        """
        Internal execute implementation with automatic exception handling.
        
        Args:
            args: Command-specific arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for failure)
            
        Note:
            @future_safe automatically converts exceptions to IOResult[int, Exception]
        """
        try:
            # Setup phase
            await self.setup_environment(args)
            
            # Initialize ALS if needed
            if self.requires_als():
                als_result = await self.initialize_als(args)
                if isinstance(als_result, Failure):
                    raise RuntimeError("Failed to initialize ALS")
                self.als_client = als_result.unwrap()
            
            # Discovery phase
            targets_result = await self.discover_targets(args)
            if isinstance(targets_result, Failure):
                raise RuntimeError("Failed to discover targets")
            
            targets = targets_result.unwrap()
            if not targets:
                await self.log_info("No targets found to process")
                return 0
            
            # Processing phase (command-specific)
            results = await self.process_targets(targets, args)
            if isinstance(results, Failure):
                raise RuntimeError("Failed to process targets")
            
            # Finalization phase
            return await self.finalize(results.unwrap(), args)
            
        finally:
            await self.cleanup()
    
    async def setup_environment(self, args: CommandArgs) -> None:
        """
        Common environment setup for all commands.
        
        Sets up logging, signal handlers, stderr redirection, and UI.
        """
        # TODO: Setup logging
        # setup_logging(verbose=args.verbose)
        
        # TODO: Redirect stderr if quiet mode
        # if args.quiet:
        #     redirect_stderr()
        
        # Setup signal handlers for graceful shutdown
        setup_cleanup_handlers()
        
        # TODO: Initialize UI if not quiet
        # if not args.quiet and self.supports_ui():
        #     self.tui = TUI()
        #     await self.tui.start()
    
    @future_safe
    async def _initialize_als_internal(self, args: CommandArgs) -> ALSClient:
        """
        Internal ALS initialization with automatic exception handling.
        
        Args:
            args: Command arguments
            
        Returns:
            ALSClient: Initialized ALS client
            
        Note:
            @future_safe automatically converts exceptions to IOResult[ALSClient, Exception]
        """
        # For now, create a dummy ALSClient since the actual implementation
        # depends on the project_path from FormatArgs/RenameArgs
        from pathlib import Path
        
        als_client = ALSClient(
            project_file=getattr(args, 'project_path', Path('.'))
        )
        
        await self.log_info("Starting Ada Language Server...")
        result = await als_client.start()
        
        if isinstance(result, Failure):
            raise RuntimeError(f"Failed to start ALS: {result.failure()}")
        
        await self.log_info("Ada Language Server ready")
        return als_client
    
    async def initialize_als(self, args: CommandArgs) -> Result[ALSClient, AdafmtError]:
        """
        Initialize the Ada Language Server client with error handling.
        
        Args:
            args: Command arguments
            
        Returns:
            Result[ALSClient, AdafmtError]: Initialized ALS client or error
        """
        # Execute internal method which returns FutureResult[ALSClient, Exception]
        result = await self._initialize_als_internal(args)
        
        # @future_safe returns IOResult, not Result
        # We need to handle IOResult -> Result conversion
        if isinstance(result, Success):
            return Success(result.unwrap())
        else:
            exc = result.failure()
            return Failure(AdafmtError(
                message=f"Failed to initialize ALS: {exc}"
            ))
    
    @abstractmethod
    async def discover_targets(self, args: CommandArgs) -> Result[list[Any], AdafmtError]:
        """
        Discover targets to process (files, symbols, etc.).
        
        Args:
            args: Command arguments
            
        Returns:
            Result[list[Any], AdafmtError]: List of targets to process or error
        """
        pass
    
    @abstractmethod
    async def process_targets(
        self, 
        targets: list[Any], 
        args: CommandArgs
    ) -> Result[list[T], AdafmtError]:
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
        
        # TODO: Stop TUI if running
        # if self.tui:
        #     await self.tui.stop()
    
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