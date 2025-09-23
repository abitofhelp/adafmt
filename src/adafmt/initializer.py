"""Initialization module for adafmt - handles setup of loggers, clients, and formatters."""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List, Tuple, Any, Dict

from .als_client import ALSClient
from .logging_jsonl import JsonlLogger
from .pattern_formatter import PatternFormatter
from .tui import make_ui
from .utils import run_hook, preflight

class Initializer:
    """Handles initialization of all components needed for the formatter."""
    
    def __init__(self, ui=None):
        self.ui = ui
        self.cleanup_vars = {}
        
    def setup_ui(self, mode: str = "plain") -> Any:
        """Initialize the UI."""
        ui = make_ui(mode)
        self.ui = ui
        self.cleanup_vars['ui'] = ui
        return ui
        
    def setup_stderr_redirect(self, stderr_path: Path, using_default: bool) -> Tuple[Any, Any]:
        """Redirect stderr to a file."""
        # Simplified stderr handling without old CLI dependencies
        original_stderr = sys.stderr
        
        if using_default:
            stderr_path.parent.mkdir(parents=True, exist_ok=True)
            
        try:
            stderr_file = stderr_path.open("w", encoding="utf-8")
            self.cleanup_vars['stderr_file'] = stderr_file
            # TODO: Implement Tee functionality when needed
            # For now, just use original stderr
            return original_stderr, stderr_file
        except Exception as e:
            print(f"Error setting up stderr redirect: {e}", file=original_stderr)
            return original_stderr, None
            
    def setup_loggers(self, log_path: Path, pattern_log_path: Path) -> Tuple[JsonlLogger, JsonlLogger]:
        """Initialize JSON loggers."""
        # Main logger
        logger = JsonlLogger(str(log_path))
        logger.start_fresh()
        self.cleanup_vars['logger'] = logger
        
        # Pattern logger
        pattern_logger = JsonlLogger(str(pattern_log_path))
        pattern_logger.start_fresh()
        self.cleanup_vars['pattern_logger'] = pattern_logger
        
        return logger, pattern_logger
        
    async def setup_als_client(self, project_path: Path, logger: JsonlLogger,
                              include_paths: List[Path], trace_io: bool,
                              als_exe: str, warmup_delay: float,
                              stderr_path: Path, debug: bool) -> Optional[ALSClient]:
        """Initialize and start the ALS client."""
        client = ALSClient(
            project_file=project_path,
            stderr_file_path=stderr_path,
            logger=logger,
            debug_logger=logger if debug else None
        )
        self.cleanup_vars['client'] = client
        
        if self.ui:
            self.ui.update(status="info", detail="Starting ada_language_server...")
            
        await client.start()
        await asyncio.sleep(0.1)  # Brief delay for ALS to initialize
        
        # Warmup delay if specified
        if warmup_delay > 0:
            if self.ui:
                self.ui.update(status="info", detail=f"Waiting {warmup_delay}s for ALS warmup...")
            await asyncio.sleep(warmup_delay)
            
        return client
        
    def setup_pattern_formatter(self, patterns_path: Optional[Path], no_patterns: bool,
                               pattern_logger: JsonlLogger, ui: Any) -> Optional[PatternFormatter]:
        """Initialize the pattern formatter."""
        if no_patterns:
            return None
            
        # Handle default patterns path
        using_default_patterns = False
        if not patterns_path:
            patterns_path = Path(__file__).parent.parent.parent / "adafmt_patterns.json"
            using_default_patterns = True
            
        # Check if patterns file exists
        if not patterns_path.exists():
            if ui:
                ui.log_line(f"Warning: patterns file not found: {patterns_path}")
            return None
            
        # Load patterns
        formatter = PatternFormatter(debug_logger=pattern_logger)
        loaded = formatter.load_from_json(patterns_path)
        
        if loaded == 0:
            if ui:
                ui.log_line(f"Warning: No patterns loaded from {patterns_path}")
            return None
            
        return formatter
        
    def run_preflight_checks(self, preflight_mode: str, dry_run: bool) -> None:
        """Run preflight checks for existing ALS processes."""
        if preflight_mode != "off":
            preflight(
                mode=preflight_mode,
                logger=self.ui.log_line if self.ui else print,
                dry_run=dry_run
            )
            
    def run_hook(self, hook_cmd: str, hook_type: str, hook_timeout: float, dry_run: bool) -> None:
        """Execute a hook command."""
        if hook_cmd:
            run_hook(
                hook_cmd,
                hook_type,
                logger=self.ui.log_line if self.ui else print,
                timeout=int(hook_timeout),
                dry_run=dry_run
            )
            
    def get_cleanup_vars(self) -> Dict[str, Any]:
        """Return cleanup variables for proper shutdown."""
        return self.cleanup_vars