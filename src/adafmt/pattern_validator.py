"""Pattern validation module for adafmt - validates patterns against ALS formatting."""

import asyncio
from pathlib import Path
from typing import List, Tuple, Any

from .als_client import ALSClient
from .pattern_formatter import PatternFormatter
from .logging_jsonl import JsonlLogger


class PatternValidator:
    """Validates that patterns don't interfere with ALS formatting."""
    
    def __init__(self, client: ALSClient, pattern_formatter: PatternFormatter,
                 logger: JsonlLogger, ui: Any):
        self.client = client
        self.pattern_formatter = pattern_formatter
        self.logger = logger
        self.ui = ui
        
    async def validate_patterns(self, file_paths: List[Path], 
                              format_timeout: float = 5.0) -> Tuple[int, List[str]]:
        """
        Validate patterns against ALS formatting.
        
        Returns:
            Tuple of (error_count, error_messages)
        """
        errors_encountered = []
        ui = self.ui
        
        ui.log_line(f"[validate] Validating {self.pattern_formatter.loaded_count} patterns against {len(file_paths)} files")
        
        # Track results
        total_files = len(file_paths)
        validated_count = 0
        error_count = 0
        
        for idx, file_path in enumerate(file_paths, 1):
            try:
                # Progress update using log_line
                if ui:
                    progress = f"[{idx:4d}/{total_files}]"
                    ui.log_line(
                        f"[validate] {progress} Checking {file_path.name}..."
                    )
                
                # Read original content
                original_content = file_path.read_text(encoding='utf-8')
                
                # Apply patterns first
                pattern_content, pattern_result = self.pattern_formatter.apply(
                    path=file_path,
                    text=original_content
                )
                
                # Skip if no patterns were applied
                if not pattern_result or not hasattr(pattern_result, 'applied_names') or len(pattern_result.applied_names) == 0:
                    validated_count += 1
                    continue
                
                # Run pattern result through ALS
                await self.client._notify("textDocument/didOpen", {
                    "textDocument": {
                        "uri": file_path.as_uri(),
                        "languageId": "ada",
                        "version": 1,
                        "text": pattern_content,
                    }
                })
                
                try:
                    edits = await self.client.request_with_timeout({
                        "method": "textDocument/formatting",
                        "params": {
                            "textDocument": {"uri": file_path.as_uri()},
                            "options": {"tabSize": 3, "insertSpaces": True},
                        }
                    }, timeout=format_timeout)
                    
                    if edits:
                        # ALS wants to make changes to pattern output
                        errors_encountered.append(
                            f"{file_path}: Patterns break ALS formatting - "
                            f"ALS wants {len(edits)} edits after applying: {', '.join(pattern_result.applied_names)}"
                        )
                        error_count += 1
                    else:
                        validated_count += 1
                        
                except asyncio.TimeoutError:
                    errors_encountered.append(f"{file_path}: ALS timeout during validation")
                    error_count += 1
                except Exception as e:
                    errors_encountered.append(f"{file_path}: ALS error - {str(e)}")
                    error_count += 1
                finally:
                    await self.client._notify("textDocument/didClose", {
                        "textDocument": {"uri": file_path.as_uri()}
                    })
                    
            except Exception as e:
                error_msg = f"{file_path}: Validation error - {type(e).__name__}: {str(e)}"
                errors_encountered.append(error_msg)
                error_count += 1
                
        # Final summary (use log_line instead of footer which doesn't exist in PlainUI)
        if ui:
            ui.log_line(
                f"[validate] Summary: Validated: {validated_count}/{total_files} | "
                f"Errors: {error_count} | "
                f"Patterns: {self.pattern_formatter.loaded_count}"
            )
            
        if error_count > 0:
            ui.log_line(f"\n[validate] ❌ Validation failed with {error_count} errors:")
            for error in errors_encountered[:10]:  # Show first 10 errors
                ui.log_line(f"  • {error}")
            if len(errors_encountered) > 10:
                ui.log_line(f"  ... and {len(errors_encountered) - 10} more errors")
        else:
            ui.log_line(f"\n[validate] ✅ All {validated_count} files validated successfully!")
            
        return error_count, errors_encountered