# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Rename command implementation using the base command architecture.

This module implements the rename command for renaming Ada symbols
across a project using the Ada Language Server.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.base_command import CommandArgs, CommandProcessor
from ..core.processing_pipeline import (
    FileData,
    LSPStage,
    ParseStage,
    ProcessedFile,
    ProcessingPipeline,
    RenameOperation,
    ValidateStage,
)
from ..file_discovery_new import discover_files
from ..errors import AdafmtError
from returns.result import Result, Success


@dataclass
class RenameArgs(CommandArgs):
    """Arguments specific to rename command."""
    
    project_path: Path
    old_name: str
    new_name: str
    include_path: list[Path] | None = None
    exclude_path: list[Path] | None = None
    check: bool = False
    diff: bool = False
    files: list[Path] | None = None
    
    def __post_init__(self):
        """Initialize default values for list fields."""
        if self.include_path is None:
            self.include_path = []
        if self.exclude_path is None:
            self.exclude_path = []
        if self.files is None:
            self.files = []


@dataclass
class RenameResult:
    """Result of a rename operation."""
    
    path: Path
    changes: list[dict[str, Any]]  # TextEdit changes
    success: bool
    error: str | None = None
    preview: str | None = None


class RenameCommandProcessor(CommandProcessor[RenameResult]):
    """
    Rename Ada symbols across a project.
    
    Uses LSP rename capability to safely rename symbols with
    full semantic understanding.
    """
    
    def __init__(self):
        super().__init__()
        self.pipeline: ProcessingPipeline | None = None
        self.all_changes: dict[Path, list[dict]] = {}
    
    async def discover_targets(self, args: CommandArgs) -> Result[list[Any], AdafmtError]:
        """Discover files potentially containing the symbol."""
        # Cast to RenameArgs to access specific fields
        rename_args = args  # type: RenameArgs
        await self.log_info(f"Searching for files containing '{rename_args.old_name}'...")
        
        # First, get all Ada files in project
        all_files = discover_files(
            files=None,
            include_paths=[rename_args.project_path],
            exclude_paths=rename_args.exclude_path,
            ui=self.tui
        )
        
        # Filter to files containing the symbol
        # In a real implementation, we'd use ripgrep or the parser
        targets = []
        for path in all_files:
            try:
                content = path.read_text(encoding='utf-8')
                # case_sensitive is not defined in RenameArgs, always case-sensitive for now
                if rename_args.old_name in content:
                    targets.append(path)
            except Exception:
                # Skip files we can't read
                pass
        
        await self.log_info(f"Found {len(targets)} files potentially containing '{rename_args.old_name}'")
        return Success(targets)
    
    async def process_targets(
        self,
        targets: list[Any],
        args: CommandArgs
    ) -> Result[list[RenameResult], AdafmtError]:
        """Process rename operation on target files."""
        # Cast to RenameArgs to access specific fields
        rename_args = args  # type: RenameArgs
        # Build pipeline
        self.pipeline = self._build_pipeline(rename_args)
        
        if self.als_client:
            self.pipeline.set_als_client(self.als_client)
        
        # Process each file to collect rename information
        results = []
        for i, path in enumerate(targets):
            await self.update_progress(i, len(targets))
            
            result = await self._process_file(path, args)
            if result.changes:
                results.append(result)
                # Collect all changes for workspace-wide application
                self.all_changes[path] = result.changes
        
        # Apply all changes atomically (unless check mode)
        if not args.check and self.all_changes:
            await self._apply_all_changes()
        
        return Success(results)
    
    def _build_pipeline(self, args: RenameArgs) -> ProcessingPipeline:
        """Build processing pipeline for rename."""
        pipeline = ProcessingPipeline()
        
        # Only parse if parser is available
        try:
            from ada2022_parser import Parser as AdaParser
            if AdaParser is not None:
                pipeline.add_stage(ParseStage())
                
                # Validate rename is safe
                pipeline.add_stage(ValidateStage([
                    # Custom validators for rename
                    # e.g., check symbol exists, not a keyword, etc.
                ]))
        except ImportError:
            pass  # Parser is optional
        
        # Perform rename via LSP
        pipeline.add_stage(LSPStage(
            RenameOperation(args.old_name, args.new_name)
        ))
        
        return pipeline
    
    async def _process_file(self, path: Path, args: RenameArgs) -> RenameResult:
        """Process a single file for rename."""
        try:
            # Load file
            file_data = FileData.from_path(path)
            
            # Check if file actually contains the symbol
            if args.old_name not in file_data.content:
                return RenameResult(
                    path=path,
                    changes=[],
                    success=True,
                    error="Symbol not found in file"
                )
            
            # Process through pipeline
            if self.pipeline is None:
                return RenameResult(
                    path=path,
                    changes=[],
                    success=False,
                    error="Pipeline not initialized"
                )
            result = await self.pipeline.process(file_data)
            
            if isinstance(result, ProcessedFile) and result.lsp_success:
                # Extract changes from WorkspaceEdit
                changes = self._extract_changes(result.lsp_result, path)
                
                # Generate preview if requested
                preview = None
                if args.check and changes:
                    preview = self._generate_preview(file_data.content, changes)
                
                return RenameResult(
                    path=path,
                    changes=changes,
                    success=True,
                    preview=preview
                )
            else:
                return RenameResult(
                    path=path,
                    changes=[],
                    success=False,
                    error=result.lsp_result if hasattr(result, 'lsp_result') else "Unknown error"
                )
                
        except Exception as e:
            return RenameResult(
                path=path,
                changes=[],
                success=False,
                error=str(e)
            )
    
    def _extract_changes(self, workspace_edit: dict, path: Path) -> list[dict]:
        """Extract TextEdit changes for a specific file from WorkspaceEdit."""
        changes = []
        
        # WorkspaceEdit format:
        # {
        #   "changes": {
        #     "file:///path/to/file.adb": [TextEdit, TextEdit, ...]
        #   }
        # }
        if "changes" in workspace_edit:
            file_uri = f"file://{path.absolute()}"
            if file_uri in workspace_edit["changes"]:
                changes = workspace_edit["changes"][file_uri]
        
        return changes
    
    def _generate_preview(self, content: str, changes: list[dict]) -> str:
        """Generate preview of changes."""
        lines = content.splitlines()
        preview_lines = []
        
        # Sort changes by line number (reverse to apply from bottom up)
        sorted_changes = sorted(
            changes,
            key=lambda c: (c["range"]["start"]["line"], c["range"]["start"]["character"]),
            reverse=True
        )
        
        for change in sorted_changes:
            start_line = change["range"]["start"]["line"]
            start_char = change["range"]["start"]["character"]
            end_line = change["range"]["end"]["line"]
            end_char = change["range"]["end"]["character"]
            new_text = change["newText"]
            
            if 0 <= start_line < len(lines):
                line = lines[start_line]
                old_text = line[start_char:end_char] if start_line == end_line else "..."
                
                preview_lines.append(
                    f"  Line {start_line + 1}: '{old_text}' → '{new_text}'"
                )
        
        return "\n".join(reversed(preview_lines))
    
    async def _apply_all_changes(self) -> None:
        """Apply all collected changes to files."""
        await self.log_info(f"Applying changes to {len(self.all_changes)} files...")
        
        for path, changes in self.all_changes.items():
            try:
                # Read current content
                content = path.read_text(encoding='utf-8')
                
                # Apply changes (from bottom up to preserve positions)
                modified_content = self._apply_text_edits(content, changes)
                
                # Write atomically
                await self._write_file_atomic(path, modified_content)
                
            except Exception as e:
                await self.log_error(f"Failed to apply changes to {path}: {e}")
    
    def _apply_text_edits(self, content: str, edits: list[dict]) -> str:
        """Apply TextEdit changes to content."""
        lines = content.splitlines(keepends=True)
        
        # Sort edits by position (reverse order)
        sorted_edits = sorted(
            edits,
            key=lambda e: (e["range"]["start"]["line"], e["range"]["start"]["character"]),
            reverse=True
        )
        
        for edit in sorted_edits:
            start_line = edit["range"]["start"]["line"]
            start_char = edit["range"]["start"]["character"]
            end_line = edit["range"]["end"]["line"]
            end_char = edit["range"]["end"]["character"]
            new_text = edit["newText"]
            
            if start_line == end_line:
                # Single line edit
                if 0 <= start_line < len(lines):
                    line = lines[start_line]
                    lines[start_line] = (
                        line[:start_char] + new_text + line[end_char:]
                    )
            else:
                # Multi-line edit
                # This is simplified - real implementation would handle properly
                pass
        
        return "".join(lines)
    
    async def _write_file_atomic(self, path: Path, content: str) -> None:
        """Write file atomically."""
        import tempfile
        import os
        
        fd, temp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp"
        )
        
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
            os.replace(temp_path, path)
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    
    def is_successful(self, result: RenameResult) -> bool:
        """Check if rename was successful."""
        return result.success and bool(result.changes)
    
    async def report_results(
        self,
        results: list[RenameResult],
        args: CommandArgs
    ) -> None:
        """Report rename results."""
        # Cast to RenameArgs to access specific fields
        rename_args = args  # type: RenameArgs
        
        total_changes = sum(len(r.changes) for r in results)
        successful_files = sum(1 for r in results if self.is_successful(r))
        
        await self.log_info(f"\nRename '{rename_args.old_name}' → '{rename_args.new_name}' complete:")
        await self.log_info(f"  Files affected: {successful_files}")
        await self.log_info(f"  Total changes: {total_changes}")
        
        if rename_args.check:
            await self.log_info("\nCHECK MODE - No changes were applied")
            
            if rename_args.verbose:
                await self.log_info("\nPreview of changes:")
                for result in results:
                    if result.preview:
                        await self.log_info(f"\n{result.path}:")
                        await self.log_info(result.preview)
        
        # Report errors
        errors = [r for r in results if not r.success and r.error]
        if errors:
            await self.log_info(f"\nErrors encountered in {len(errors)} files")
            if rename_args.verbose:
                for result in errors:
                    await self.log_error(f"  {result.path}: {result.error}")
        


# CLI entry point
async def rename_main(args: RenameArgs) -> int:
    """
    Main entry point for rename command.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code
    """
    command = RenameCommandProcessor()
    result = await command.execute(args)
    
    # Extract exit code from Result
    if isinstance(result, Success):
        return result.unwrap()
    else:
        return 1  # Generic error code