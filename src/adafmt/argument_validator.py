"""Argument validation module for adafmt - validates CLI arguments and paths."""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from .path_validator import validate_path


class ArgumentValidator:
    """Validates command-line arguments for the formatter."""
    
    @staticmethod
    def validate_paths(project_path: Path,
                      include_paths: List[Path],
                      exclude_paths: List[Path],
                      patterns_path: Optional[Path],
                      files: Optional[List[str]],
                      log_path: Optional[Path],
                      stderr_path: Optional[Path],
                      metrics_path: Optional[Path],
                      no_patterns: bool) -> Tuple[bool, List[str]]:
        """
        Validate all path arguments.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Validate project path
        if not project_path.exists():
            errors.append(f"Project path does not exist: {project_path}")
        elif not project_path.is_file():
            errors.append(f"Project path is not a file: {project_path}")
        elif project_path.suffix.lower() != ".gpr":
            errors.append(f"Project path must be a .gpr file, got: {project_path}")
        else:
            validation_error = validate_path(str(project_path))
            if validation_error:
                errors.append(f"Project path {validation_error}: {project_path}")
            
        # Validate include paths
        for i, include_path in enumerate(include_paths):
            validation_error = validate_path(str(include_path))
            if validation_error:
                errors.append(f"Include path {i+1} {validation_error}: {include_path}")
            # Don't check existence - may be created later
                
        # Validate exclude paths  
        for i, exclude_path in enumerate(exclude_paths):
            validation_error = validate_path(str(exclude_path))
            if validation_error:
                errors.append(f"Exclude path {i+1} {validation_error}: {exclude_path}")
            # Don't check existence - pattern matching
                
        # Validate patterns path
        if patterns_path and not no_patterns:
            if not patterns_path.exists():
                errors.append(f"Patterns file does not exist: {patterns_path}")
            elif not patterns_path.is_file():
                errors.append(f"Patterns path is not a file: {patterns_path}")
            elif patterns_path.suffix.lower() != ".json":
                errors.append(f"Patterns file must be a .json file, got: {patterns_path}")
            else:
                validation_error = validate_path(str(patterns_path))
                if validation_error:
                    errors.append(f"Patterns path {validation_error}: {patterns_path}")
                
        # Validate explicit files
        if files:
            for i, file_path in enumerate(files):
                validation_error = validate_path(file_path)
                if validation_error:
                    errors.append(f"File path {i+1} {validation_error}: {file_path}")
                    
                path = Path(file_path)
                if not path.exists():
                    errors.append(f"File does not exist: {file_path}")
                elif not path.is_file():
                    errors.append(f"Path is not a file: {file_path}")
                elif path.suffix.lower() not in (".ads", ".adb", ".ada"):
                    errors.append(f"Not an Ada file: {file_path}")
                    
        # Validate log path
        if log_path:
            validation_error = validate_path(str(log_path))
            if validation_error:
                errors.append(f"Log path {validation_error}: {log_path}")
            # Parent directory will be created if needed
                
        # Validate stderr path  
        if stderr_path:
            validation_error = validate_path(str(stderr_path))
            if validation_error:
                errors.append(f"Stderr path {validation_error}: {stderr_path}")
            # Parent directory will be created if needed
                
        # Validate metrics path
        if metrics_path:
            validation_error = validate_path(str(metrics_path))
            if validation_error:
                errors.append(f"Metrics path {validation_error}: {metrics_path}")
            # Parent directory will be created if needed
                
        return len(errors) == 0, errors
        
    @staticmethod
    def validate_options(no_patterns: bool, no_als: bool,
                        validate_patterns: bool, write: bool,
                        diff: bool, check: bool) -> Tuple[bool, List[str]]:
        """
        Validate option combinations.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check conflicting options
        if no_patterns and no_als:
            errors.append("Cannot use both --no-patterns and --no-als (nothing to do)")
            
        if validate_patterns and no_patterns:
            errors.append("Cannot use --validate-patterns with --no-patterns")
            
        if validate_patterns and no_als:
            errors.append("Pattern validation requires ALS (cannot use --no-als)")
            
        if write and check:
            errors.append("Cannot use both --write and --check")
            
        # Diff requires either write or check (unless in validation mode)
        if diff and not (write or check or validate_patterns):
            errors.append("--diff requires either --write or --check")
            
        return len(errors) == 0, errors
        
    @staticmethod
    def ensure_absolute_path(path: Path, name: str) -> Path:
        """Ensure a path is absolute."""
        if not path.is_absolute():
            abs_path = path.expanduser().resolve()
            print(f"Note: Converting relative {name} to absolute: {path} → {abs_path}", 
                  file=sys.stderr)
            return abs_path
        return path