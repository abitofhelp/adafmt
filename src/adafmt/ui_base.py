# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Base UI interface for command processors."""

from abc import ABC, abstractmethod


class BaseUI(ABC):
    """Abstract base class for UI implementations."""
    
    @abstractmethod
    async def start(self) -> None:
        """Start the UI."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the UI."""
        pass
    
    @abstractmethod
    async def update_status(self, message: str) -> None:
        """Update status message."""
        pass
    
    @abstractmethod
    async def update_progress(self, current: int, total: int) -> None:
        """Update progress indicator."""
        pass
    
    @abstractmethod
    async def add_error(self, error: str) -> None:
        """Add an error message."""
        pass
    
    @abstractmethod
    async def log_line(self, message: str) -> None:
        """Log a message line."""
        pass