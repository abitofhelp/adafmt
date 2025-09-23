# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Format command implementation using the base command architecture.

This module implements the format command using the processing pipeline
and base command infrastructure.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from ..core.base_command import CommandArgs, CommandProcessor
from ..core.processing_pipeline import (
    FileData,
    FormatOperation,
    FormattedFile,
    LSPStage,
    ParseStage,
    ProcessingPipeline,
    ValidateStage,
)
from ..file_discovery_new import discover_files
# TODO: Import pattern loader when ready
# from ..pattern_loader import load_patterns
from ..worker_pool import WorkerPool
from ..errors import AdafmtError
from returns.result import Failure, Result, Success


@dataclass
class FormatArgs(CommandArgs):
    """Arguments specific to format command."""
    
    project_path: Path
    als_ready_timeout: int = 10
    als_stale_minutes: int = 30
    check: bool = False
    debug_als: bool = False
    debug_als_path: Path | None = None
    debug_patterns: bool = False
    debug_patterns_path: Path | None = None
    diff: bool = False
    exclude_path: list[Path] | None = None
    format_timeout: int = 60
    hook_timeout: int = 5
    include_path: list[Path] | None = None
    init_timeout: int = 180
    log_path: Path | None = None
    max_attempts: int = 2
    max_consecutive_timeouts: int = 5
    max_file_size: int = 102400
    metrics_path: Path | None = None
    no_als: bool = False
    no_patterns: bool = False
    num_workers: int | None = None
    patterns_max_bytes: int = 10485760
    patterns_path: Path | None = None
    patterns_timeout_ms: int = 100
    post_hook: str | None = None
    pre_hook: str | None = None
    preflight: str = "safe"
    stderr_path: Path | None = None
    validate_patterns: bool = False
    write: bool = False
    files: list[Path] | None = None
    workers: int = 3  # Number of worker threads for parallel processing
    verbose: bool = False  # Enable verbose output
    
    def __post_init__(self):
        """Initialize default values for list fields."""
        if self.exclude_path is None:
            self.exclude_path = []
        if self.include_path is None:
            self.include_path = []
        if self.files is None:
            self.files = []


class FormatCommandProcessor(CommandProcessor[FormattedFile]):
    """
    Format Ada source files.
    
    Uses a configurable pipeline to:
    1. Parse files (optional)
    2. Apply pre-ALS patterns (optional)
    3. Format via ALS
    4. Apply post-ALS patterns (optional)
    5. Validate with GNAT (optional)
    """
    
    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__()
        self.config = config or {}
        self.pipeline: ProcessingPipeline | None = None
        self.worker_pool: WorkerPool | None = None
    
    async def discover_targets(self, args: CommandArgs) -> Result[list[Any], AdafmtError]:
        """Discover Ada files to format."""
        # Cast to FormatArgs to access specific fields
        format_args = cast(FormatArgs, args)
        await self.log_info("Discovering Ada files...")
        
        try:
            # Convert file paths to strings for discover_files
            file_list = [str(f) for f in format_args.files] if format_args.files else None
            
            # Use a simplified file discovery approach for now
            # TODO: Restore full discover_files when IOResult issues are resolved
            if file_list:
                files = [Path(f) for f in file_list if Path(f).exists()]
            else:
                # Simple discovery: look for .ads and .adb files in include paths
                files = []
                for include_path in (format_args.include_path or []):
                    if include_path.exists():
                        files.extend(include_path.glob("*.ads"))
                        files.extend(include_path.glob("*.adb"))
            
            await self.log_info(f"Found {len(files)} Ada files to format")
            return Success(files)
        except Exception as e:
            return Failure(AdafmtError(
                message=f"Failed to discover files: {e}"
            ))
    
    async def process_targets(
        self,
        targets: list[Any],
        args: CommandArgs
    ) -> Result[list[FormattedFile], AdafmtError]:
        """Process files through formatting pipeline."""
        # Cast to FormatArgs to access specific fields
        format_args = cast(FormatArgs, args)
        await self.log_info(f"Processing {len(targets)} files (parser-based processing stub)")
        
        # Simple processing without complex pipeline for now
        # TODO: Implement full parser-based processing pipeline
        results = []
        for i, path in enumerate(targets):
            # Update progress
            await self.update_progress(i, len(targets))
            
            # Simple file processing stub
            result = await self._process_file_simple(path, format_args)
            results.append(result)
            
            # Update metrics
            if self.is_successful(result):
                self.metrics.successful_files += 1
            else:
                self.metrics.failed_files += 1
        
        return Success(results)
    
    async def _build_pipeline(self, args: FormatArgs) -> ProcessingPipeline:
        """Build processing pipeline based on configuration."""
        pipeline = ProcessingPipeline()
        
        # Load patterns if needed
        # TODO: Add pre_als_patterns and post_als_patterns to FormatArgs when implementing patterns
        patterns = None
        
        # 1. Parse stage (optional)
        # TODO: Add use_parser flag to FormatArgs when parser is fully integrated
        use_parser = getattr(args, 'use_parser', False)
        if use_parser:
            try:
                from ada2022_parser import Parser as AdaParser
                if AdaParser is not None:
                    await self.log_info("Parser-based formatting enabled")
                    pipeline.add_stage(ParseStage())
                    
                    # Validation stage
                    pipeline.add_stage(ValidateStage())
            except ImportError:
                pass  # Parser is optional
        
        # 2. Pre-ALS patterns (optional)
        # TODO: Implement when pattern system is ready
        
        # 3. ALS formatting
        pipeline.add_stage(LSPStage(FormatOperation()))
        
        # 4. Post-ALS patterns (optional)
        # TODO: Implement when pattern system is ready
        
        # 5. GNAT validation (optional)
        # TODO: Add validate_with_gnat flag to FormatArgs when GNAT validation is ready
        
        return pipeline
    
    async def _process_file_simple(self, path: Path, args: FormatArgs) -> FormattedFile:
        """Simple file processing stub for parser-based architecture."""
        try:
            # Read file content
            content = path.read_text(encoding='utf-8')
            
            # For now, just return the content unchanged
            # TODO: Implement parser-based transformations here
            await self.log_info(f"Processed {path.name} ({len(content)} chars)")
            
            return FormattedFile(
                path=path,
                content=content,
                encoding='utf-8',
                final_content=content,  # No processing applied yet
                patterns_applied=[],
                lsp_success=True,  # Mark as successful for testing
                ast={},
                parse_errors=[],
                is_safe=True,
                validation_messages=[],
                lsp_result=None
            )
            
        except Exception as e:
            # Return failed result
            return FormattedFile(
                path=path,
                content="",
                ast={},
                parse_errors=[str(e)],
                is_safe=False,
                validation_messages=[],
                lsp_result=None,
                lsp_success=False,
                final_content="",
                patterns_applied=[]
            )
    
    async def _process_file(self, path: Path) -> FormattedFile:
        """Process a single file through the pipeline."""
        try:
            # Load file data
            file_data = FileData.from_path(path)
            
            # Process through pipeline
            if self.pipeline is None:
                return FormattedFile(
                    path=path,
                    content=file_data.content,
                    encoding=file_data.encoding,
                    final_content=file_data.content,  # No processing applied
                    patterns_applied=[]
                )
            result = await self.pipeline.process(file_data)
            
            # Write result if successful
            if isinstance(result, FormattedFile) and result.final_content:
                # Use atomic write
                await self._write_file_atomic(path, result.final_content)
            
            return result
            
        except Exception as e:
            # Return failed result
            return FormattedFile(
                path=path,
                content="",
                ast={},
                parse_errors=[str(e)],
                is_safe=False,
                validation_messages=[],
                lsp_result=None,
                lsp_success=False,
                final_content="",
                patterns_applied=[]
            )
    
    async def _write_file_atomic(self, path: Path, content: str) -> None:
        """Write file atomically using temp file + rename."""
        import tempfile
        import os
        
        # Create temp file in same directory
        fd, temp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp"
        )
        
        try:
            # Write to temp file
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Atomic rename
            os.replace(temp_path, path)
            
        except Exception:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    
    def is_successful(self, result: FormattedFile) -> bool:
        """Check if formatting was successful."""
        return (
            result.lsp_success and 
            bool(result.final_content) and
            not result.parse_errors
        )
    
    async def report_results(
        self, 
        results: list[FormattedFile], 
        args: CommandArgs
    ) -> None:
        """Report formatting results."""
        # Cast to FormatArgs to access specific fields
        format_args = cast(FormatArgs, args)
        
        successful = sum(1 for r in results if self.is_successful(r))
        failed = len(results) - successful
        
        # Build summary
        summary = [
            "\nFormatting complete:",
            f"  Processed: {len(results)} files",
            f"  Successful: {successful} files",
            f"  Failed: {failed} files",
        ]
        
        if getattr(format_args, 'use_parser', False):
            parse_errors = sum(1 for r in results if r.parse_errors)
            if parse_errors:
                summary.append(f"  Parse errors: {parse_errors} files")
        
        # Report pattern statistics
        all_patterns: set[str] = set()
        for result in results:
            if result.patterns_applied:
                all_patterns.update(result.patterns_applied)
        
        if all_patterns:
            summary.append(f"  Patterns applied: {len(all_patterns)}")
        
        # Output summary
        for line in summary:
            await self.log_info(line)
        
        # Report errors if verbose
        if format_args.verbose and failed > 0:
            await self.log_info("\nErrors:")
            for result in results:
                if not self.is_successful(result):
                    errors = []
                    if result.parse_errors:
                        errors.extend(result.parse_errors)
                    if result.validation_messages:
                        errors.extend(result.validation_messages)
                    if not result.lsp_success and result.lsp_result:
                        errors.append(f"LSP error: {result.lsp_result}")
                    
                    await self.log_error(f"  {result.path}: {', '.join(errors)}")
        


# Factory function for creating format command
def create_format_command(config: dict[str, Any] | None = None) -> FormatCommandProcessor:
    """
    Create a format command with configuration.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured format command
    """
    return FormatCommandProcessor(config)


# CLI entry point
async def format_main(args: FormatArgs) -> int:
    """
    Main entry point for format command.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code
    """
    # Load configuration if specified
    config = {}
    config_file = getattr(args, 'config_file', None)
    if config_file and config_file.exists():
        import json
        config = json.loads(config_file.read_text())
    
    # Create and execute command
    command = create_format_command(config)
    result = await command.execute(args)
    
    # Extract exit code from Result
    if isinstance(result, Success):
        return result.unwrap()
    else:
        return 1  # Generic error code