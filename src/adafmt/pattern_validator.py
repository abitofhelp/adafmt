"""Pattern validation module for adafmt - validates patterns against ALS formatting."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional, Any, Dict

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
                
                # Format with ALS first
                als_result = await self._format_with_als(file_path, format_timeout)
                if not als_result or als_result.get('error'):
                    error_msg = als_result.get('error', 'Unknown ALS error') if als_result else 'ALS timeout'
                    errors_encountered.append(f"{file_path}: ALS error - {error_msg}")
                    error_count += 1
                    continue
                
                als_formatted_content = als_result['content']
                
                # Apply patterns to ALS-formatted content
                pattern_formatted_content, pattern_result = self.pattern_formatter.apply(
                    path=file_path,
                    content=als_formatted_content
                )
                
                # Format the pattern-modified content with ALS again
                with tempfile.NamedTemporaryFile(mode='w', suffix='.adb', delete=False) as tmp:
                    tmp.write(pattern_formatted_content)
                    tmp.flush()
                    tmp_path = Path(tmp.name)
                
                try:
                    als_reformat_result = await self._format_with_als(tmp_path, format_timeout)
                finally:
                    tmp_path.unlink(missing_ok=True)
                
                if not als_reformat_result or als_reformat_result.get('error'):
                    error_msg = als_reformat_result.get('error', 'Unknown ALS error') if als_reformat_result else 'ALS timeout'
                    errors_encountered.append(f"{file_path}: Pattern application broke ALS formatting - {error_msg}")
                    error_count += 1
                    continue
                
                als_reformatted_content = als_reformat_result['content']
                
                # Compare: ALS-formatted should equal ALS-re-formatted after patterns
                if als_formatted_content != als_reformatted_content:
                    # Find which patterns caused issues
                    problematic_patterns = self._identify_problematic_patterns(
                        als_formatted_content,
                        pattern_result,
                        als_reformatted_content
                    )
                    
                    error_msg = f"{file_path}: Patterns interfere with ALS formatting"
                    if problematic_patterns:
                        error_msg += f" (patterns: {', '.join(problematic_patterns)})"
                    errors_encountered.append(error_msg)
                    error_count += 1
                    
                    # Log details for debugging
                    self.logger.write({
                        'ev': 'validation_failure',
                        'file': str(file_path),
                        'patterns_applied': pattern_result.applied_names if hasattr(pattern_result, 'applied_names') else [],
                        'problematic_patterns': problematic_patterns
                    })
                else:
                    validated_count += 1
                    
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
        
    async def _format_with_als(self, file_path: Path, timeout: float) -> Optional[Dict]:
        """Format a file with ALS and return the result."""
        try:
            res = await self.client.request_with_timeout(
                {
                    "method": "textDocument/formatting",
                    "params": {
                        "textDocument": {"uri": file_path.as_uri()},
                        "options": {"tabSize": 3, "insertSpaces": True}
                    }
                },
                timeout=timeout
            )
            
            if res is None:  # Timeout
                return None
                
            if "error" in res:
                return {"error": res["error"].get("message", "Unknown error")}
                
            edits = res.get("result", [])
            if not edits:
                # No changes needed
                content = file_path.read_text(encoding='utf-8')
                return {"content": content}
                
            # Apply edits
            from .edits import replace_range
            content = file_path.read_text(encoding='utf-8')
            new_content = content
            # Apply edits in reverse order to maintain positions
            for edit in sorted(edits, key=lambda e: (e["range"]["start"]["line"], e["range"]["start"]["character"]), reverse=True):
                start_pos = edit["range"]["start"]
                end_pos = edit["range"]["end"]
                new_text = edit["newText"]
                new_content = replace_range(new_content, start_pos, end_pos, new_text)
            return {"content": new_content}
            
        except Exception as e:
            return {"error": f"{type(e).__name__}: {str(e)}"}
            
    def _identify_problematic_patterns(self, als_content: str, 
                                     pattern_result: Any,
                                     als_reformat_content: str) -> List[str]:
        """Identify which patterns likely caused formatting issues."""
        # Simple heuristic: patterns that made replacements are suspects
        if hasattr(pattern_result, 'applied_names'):
            return pattern_result.applied_names
        return []