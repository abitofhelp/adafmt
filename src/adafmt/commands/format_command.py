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
from typing import Any

from ..core.base_command import CommandArgs, CommandProcessor
from ..core.processing_pipeline import (
    FileData,
    FormatOperation,
    FormattedFile,
    GNATValidationStage,
    LSPStage,
    ParseStage,
    PatternStage,
    ProcessingPipeline,
    ValidateStage,
)
from ..file_discovery import discover_ada_files
from ..pattern_loader import load_patterns
from ..worker_pool import WorkerPool


@dataclass
class FormatArgs(CommandArgs):
    """Arguments specific to format command."""
    
    files: list[Path]
    recursive: bool = False
    ignore: list[str] | None = None
    config_file: Path | None = None
    use_parser: bool = True
    pre_als_patterns: bool = True
    post_als_patterns: bool = True
    validate_with_gnat: bool = False
    pattern_file: Path | None = None


class FormatCommand(CommandProcessor[FormattedFile]):
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
    
    async def discover_targets(self, args: FormatArgs) -> list[Path]:
        """Discover Ada files to format."""
        await self.log_info("Discovering Ada files...")
        
        files = await discover_ada_files(
            paths=args.files,
            recursive=args.recursive,
            ignore_patterns=args.ignore or []
        )
        
        await self.log_info(f"Found {len(files)} Ada files to format")
        return files
    
    async def process_targets(
        self,
        targets: list[Path],
        args: FormatArgs
    ) -> list[FormattedFile]:
        """Process files through formatting pipeline."""
        # Build the processing pipeline
        self.pipeline = await self._build_pipeline(args)
        
        # Inject ALS client if available
        if self.als_client:
            self.pipeline.set_als_client(self.als_client)
        
        # Create worker pool for parallel processing
        self.worker_pool = WorkerPool(
            num_workers=args.workers,
            metrics=self.metrics
        )
        
        await self.log_info(f"Processing {len(targets)} files with {args.workers} workers")
        
        # Process files
        results = []
        async with self.worker_pool:
            for i, path in enumerate(targets):
                # Update progress
                await self.update_progress(i, len(targets))
                
                # Process file
                result = await self._process_file(path)
                results.append(result)
                
                # Update metrics
                if self.is_successful(result):
                    self.metrics.successful_files += 1
                else:
                    self.metrics.failed_files += 1
        
        return results
    
    async def _build_pipeline(self, args: FormatArgs) -> ProcessingPipeline:
        """Build processing pipeline based on configuration."""
        pipeline = ProcessingPipeline()
        
        # Load patterns if needed
        patterns = None
        if args.pre_als_patterns or args.post_als_patterns:
            pattern_file = args.pattern_file or Path("adafmt_patterns.json")
            if pattern_file.exists():
                patterns = await load_patterns(pattern_file)
        
        # 1. Parse stage (optional)
        if args.use_parser:
            await self.log_info("Parser-based formatting enabled")
            pipeline.add_stage(ParseStage())
            
            # Validation stage
            pipeline.add_stage(ValidateStage())
        
        # 2. Pre-ALS patterns (optional)
        if args.pre_als_patterns and patterns:
            pre_patterns = [p for p in patterns if p.get("phase") == "pre-als"]
            if pre_patterns:
                await self.log_info(f"Applying {len(pre_patterns)} pre-ALS patterns")
                pipeline.add_stage(PatternStage(pre_patterns, "pre-als"))
        
        # 3. ALS formatting
        pipeline.add_stage(LSPStage(FormatOperation()))
        
        # 4. Post-ALS patterns (optional)
        if args.post_als_patterns and patterns:
            post_patterns = [p for p in patterns if p.get("phase", "post-als") == "post-als"]
            if post_patterns:
                await self.log_info(f"Applying {len(post_patterns)} post-ALS patterns")
                pipeline.add_stage(PatternStage(post_patterns, "post-als"))
        
        # 5. GNAT validation (optional)
        if args.validate_with_gnat:
            await self.log_info("GNAT validation enabled")
            pipeline.add_stage(GNATValidationStage())
        
        return pipeline
    
    async def _process_file(self, path: Path) -> FormattedFile:
        """Process a single file through the pipeline."""
        try:
            # Load file data
            file_data = FileData.from_path(path)
            
            # Process through pipeline
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
        args: FormatArgs
    ) -> None:
        """Report formatting results."""
        successful = sum(1 for r in results if self.is_successful(r))
        failed = len(results) - successful
        
        # Build summary
        summary = [
            f"\nFormatting complete:",
            f"  Processed: {len(results)} files",
            f"  Successful: {successful} files",
            f"  Failed: {failed} files",
        ]
        
        if args.use_parser:
            parse_errors = sum(1 for r in results if r.parse_errors)
            if parse_errors:
                summary.append(f"  Parse errors: {parse_errors} files")
        
        # Report pattern statistics
        all_patterns = set()
        for result in results:
            all_patterns.update(result.patterns_applied)
        
        if all_patterns:
            summary.append(f"  Patterns applied: {len(all_patterns)}")
        
        # Output summary
        for line in summary:
            await self.log_info(line)
        
        # Report errors if verbose
        if args.verbose and failed > 0:
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
def create_format_command(config: dict[str, Any] | None = None) -> FormatCommand:
    """
    Create a format command with configuration.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured format command
    """
    return FormatCommand(config)


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
    if args.config_file and args.config_file.exists():
        import json
        config = json.loads(args.config_file.read_text())
    
    # Create and execute command
    command = create_format_command(config)
    return await command.execute(args)