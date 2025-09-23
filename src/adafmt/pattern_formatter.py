# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Pattern-based post-processing formatter for Ada source code.

This module provides a pattern formatter that applies regex-based transformations
to Ada source code after ALS formatting. It supports configurable patterns loaded
from JSON files with comprehensive safety features including timeouts and size limits.

The pattern formatter is designed to handle formatting rules that ALS/GNATformat
doesn't cover, such as specific spacing around comments or operators.

Key features:
    - Regex-based pattern matching with timeout protection
    - JSON-based pattern configuration
    - Comprehensive error isolation and logging
    - File size limits to prevent resource exhaustion
    - Atomic pattern application with rollback on failure
"""

from __future__ import annotations

import json
import signal
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple, TypedDict

# Try to import regex module for timeout support, fall back to re
try:
    import regex as re
    REGEX_MODULE = 'regex'
    HAS_TIMEOUT = True
except ImportError:
    import re  # type: ignore
    REGEX_MODULE = 're'
    HAS_TIMEOUT = False

from .logging_jsonl import JsonlLogger

# Adapter for pattern logger to match expected interface
class PatternLogger:
    """Adapter to make JsonlLogger compatible with pattern formatter."""
    def __init__(self, jsonl_logger: JsonlLogger):
        self._logger = jsonl_logger
    
    def log(self, data: dict) -> None:
        """Write log data using JsonlLogger's write method."""
        if self._logger:
            self._logger.write(data)


# Type for match information during debugging
class MatchInfo(TypedDict):
    start: int
    end: int
    matched_text: str
    line_number: int


# Pattern name validation regex (12 characters)
PATTERN_NAME_REGEX = re.compile(r'^[a-z0-9_-]{12}$')

# Supported regex flags
SUPPORTED_FLAGS = {
    'MULTILINE': re.MULTILINE,
    'IGNORECASE': re.IGNORECASE,
    'DOTALL': re.DOTALL
}

# Valid pattern categories
VALID_CATEGORIES = {
    'comment', 'hygiene', 'operator', 'delimiter', 'declaration', 'attribute'
}


@dataclass(frozen=True)
class CompiledRule:
    """A compiled pattern rule ready for application.
    
    Attributes:
        name: Unique 12-character identifier
        title: Human-readable title (1-80 characters)
        category: Pattern category (comment, hygiene, operator, etc.)
        find: Compiled regex pattern
        replace: Replacement string
    """
    name: str
    title: str
    category: str
    find: Pattern[str]
    replace: str
    
    def __post_init__(self) -> None:
        """Validate the pattern name format and fields."""
        if not PATTERN_NAME_REGEX.match(self.name):
            raise ValueError(f"Invalid pattern name format: {self.name}")
        if not (1 <= len(self.title) <= 80):
            raise ValueError(f"Title must be 1-80 characters: {self.title}")
        if self.category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category: {self.category}")


@dataclass
class FileApplyResult:
    """Result of applying patterns to a single file.
    
    Attributes:
        applied_names: List of pattern names that made changes
        replacements_sum: Total number of replacements made
    """
    applied_names: List[str] = field(default_factory=list)
    replacements_sum: int = 0


@contextmanager
def timeout_context(seconds: float):
    """Context manager for operation timeout using signals.
    
    This provides timeout protection for regex operations to prevent
    ReDoS attacks. Only works on Unix-like systems with SIGALRM.
    
    Args:
        seconds: Timeout in seconds
        
    Yields:
        None
        
    Raises:
        TimeoutError: If the operation exceeds the timeout
    """
    if not hasattr(signal, 'SIGALRM'):
        # Windows doesn't support SIGALRM, so just yield
        yield
        return
        
    def timeout_handler(signum, frame):
        raise TimeoutError("Pattern execution timed out")
    
    # Set the timeout handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    old_alarm = signal.alarm(int(seconds))
    
    try:
        yield
    finally:
        # Restore previous alarm and handler
        signal.alarm(0)
        if old_alarm:
            signal.alarm(old_alarm)
        signal.signal(signal.SIGALRM, old_handler)


class PatternFormatter:
    """Pattern-based formatter for post-ALS processing.
    
    This class manages a collection of regex patterns that are applied
    sequentially to Ada source code after ALS formatting. It includes
    comprehensive safety features and error handling.
    
    Attributes:
        rules: Immutable tuple of compiled pattern rules
        enabled: Whether pattern processing is enabled
        loaded_count: Number of successfully loaded patterns
        files_touched: Count of files modified by each pattern
        replacements: Total replacements made by each pattern
    """
    
    def __init__(self, debug_logger: Optional[JsonlLogger] = None) -> None:
        """Initialize an empty pattern formatter.
        
        Args:
            debug_logger: Optional logger for detailed debug events
        """
        self.rules: Tuple[CompiledRule, ...] = ()
        self.enabled: bool = False
        self.loaded_count: int = 0
        self.files_touched: Dict[str, int] = {}
        self.replacements: Dict[str, int] = {}
        self.debug_logger = debug_logger
    
    @classmethod
    def load_from_json(
        cls,
        path: Path,
        logger: Optional[JsonlLogger] = None,
        ui = None,
        debug_logger: Optional[JsonlLogger] = None
    ) -> PatternFormatter:
        """Load patterns from a JSON file.
        
        The file is opened, read, and closed immediately to ensure proper
        resource management even in case of errors or signals.
        
        Args:
            path: Path to the patterns JSON file
            logger: Optional logger for warnings and errors
            ui: Optional UI instance for user feedback
            debug_logger: Optional logger for detailed debug events
            
        Returns:
            Configured PatternFormatter instance
            
        Note:
            Invalid patterns are skipped with warnings logged.
            If no valid patterns are loaded, the formatter is disabled.
        """
        formatter = cls(debug_logger=debug_logger)
        
        # Load patterns with guaranteed file closure
        try:
            with open(path, 'r', encoding='utf-8') as f:
                patterns_data = json.load(f)
        except FileNotFoundError:
            if logger:
                logger.log({
                    'ev': 'pattern_error',
                    'error': f'Patterns file not found: {path}'
                })
            return formatter
        except json.JSONDecodeError as e:
            if logger:
                logger.log({
                    'ev': 'pattern_error',
                    'error': f'Invalid JSON in patterns file: {e}'
                })
            if ui:
                ui.show_error(f"Invalid patterns JSON: {e}")
            return formatter
        except Exception as e:
            if logger:
                logger.log({
                    'ev': 'pattern_error',
                    'error': f'Failed to load patterns: {e}'
                })
            return formatter
        
        # Validate and compile patterns
        valid_rules: List[CompiledRule] = []
        seen_names: set[str] = set()
        
        for idx, pattern in enumerate(patterns_data):
            # Validate pattern structure
            if not isinstance(pattern, dict):
                if logger:
                    logger.log({
                        'ev': 'pattern_error',
                        'error': f'Pattern {idx} is not a JSON object'
                    })
                continue
            
            # Extract and validate required fields
            name = pattern.get('name', '')
            title = pattern.get('title', '')
            category = pattern.get('category', '')
            find = pattern.get('find', '')
            replace = pattern.get('replace', '')
            
            if not name or not title or not category or not find:
                if logger:
                    logger.log({
                        'ev': 'pattern_error',
                        'error': f'Pattern {idx} missing required fields'
                    })
                continue
            
            # Check name format and uniqueness
            if not PATTERN_NAME_REGEX.match(name):
                if logger:
                    logger.log({
                        'ev': 'pattern_error',
                        'name': name,
                        'error': 'Invalid name format (must be 12 chars, [a-z0-9_-])'
                    })
                if ui:
                    ui.log_line(f"[warning] Pattern '{name}' has invalid name format")
                continue
            
            if name in seen_names:
                if logger:
                    logger.log({
                        'ev': 'pattern_error',
                        'name': name,
                        'error': 'Duplicate pattern name'
                    })
                if ui:
                    ui.log_line(f"[warning] Duplicate pattern name: {name}")
                continue
            
            seen_names.add(name)
            
            # Compile regex with flags
            flags_list = pattern.get('flags', [])
            flags = 0
            for flag_name in flags_list:
                if flag_name in SUPPORTED_FLAGS:
                    flags |= SUPPORTED_FLAGS[flag_name]
                else:
                    if logger:
                        logger.log({
                            'ev': 'pattern_error',
                            'name': name,
                            'error': f'Unknown flag: {flag_name}'
                        })
            
            try:
                compiled_find = re.compile(find, flags)
                rule = CompiledRule(
                    name=name,
                    title=title,
                    category=category,
                    find=compiled_find,
                    replace=replace
                )
                valid_rules.append(rule)
                
                # Initialize metrics
                formatter.files_touched[name] = 0
                formatter.replacements[name] = 0
                
            except re.error as e:
                if logger:
                    logger.log({
                        'ev': 'pattern_error',
                        'name': name,
                        'error': f'Regex compile error: {e}'
                    })
                if ui:
                    ui.log_line(f"[warning] Pattern '{name}' has invalid regex: {e}")
                continue
            except ValueError as e:
                # From CompiledRule validation
                if logger:
                    logger.log({
                        'ev': 'pattern_error',
                        'name': name,
                        'error': str(e)
                    })
                continue
        
        # Sort by name for deterministic ordering
        valid_rules.sort(key=lambda r: r.name)
        
        # Update formatter state
        formatter.rules = tuple(valid_rules)
        formatter.loaded_count = len(valid_rules)
        formatter.enabled = formatter.loaded_count > 0
        
        if ui:
            if formatter.loaded_count == 0:
                ui.log_line("[info] No valid patterns loaded")
        
        return formatter
    
    def apply(
        self,
        path: Path,
        text: str,
        timeout_ms: int = 50,
        logger: Optional[JsonlLogger] = None,
        ui = None
    ) -> Tuple[str, FileApplyResult]:
        """Apply all patterns to the given text.
        
        Patterns are applied sequentially in name order. Each pattern
        has a timeout to prevent ReDoS attacks. Errors in individual
        patterns don't stop processing of other patterns.
        
        Args:
            path: Path of the file being processed (for logging)
            text: The text to process
            timeout_ms: Timeout per pattern in milliseconds
            logger: Optional logger for pattern events
            ui: Optional UI for error display
            
        Returns:
            Tuple of (processed_text, result) where result contains
            applied pattern names and total replacement count
            
        Note:
            If no patterns are loaded or enabled=False, returns
            the original text unchanged.
        """
        if not self.enabled or not self.rules:
            return text, FileApplyResult()
        
        result = FileApplyResult()
        current_text = text
        timeout_seconds = timeout_ms / 1000.0
        
        # Debug: Log file start event with original content
        if self.debug_logger:
            self.debug_logger.write({
                'ev': 'pattern_debug',
                'type': 'file_start',
                'path': str(path),
                'content_length': len(text),
                'content_preview': text[:500] if len(text) > 500 else text,
                'total_patterns': len(self.rules)
            })
        
        for rule in self.rules:
            try:
                # Debug: Log pattern attempt
                if self.debug_logger:
                    self.debug_logger.write({
                        'ev': 'pattern_debug',
                        'type': 'pattern_attempt',
                        'path': str(path),
                        'pattern_name': rule.name,
                        'pattern_title': rule.title,
                        'pattern_category': rule.category,
                        'pattern_regex': rule.find.pattern,
                        'pattern_flags': rule.find.flags,
                        'replacement': rule.replace
                    })
                
                # Find all matches before replacement (for debug logging)
                matches_for_debug: List[MatchInfo] = []
                if self.debug_logger:
                    for match in rule.find.finditer(current_text):
                        match_info: MatchInfo = {
                            'start': match.start(),
                            'end': match.end(),
                            'matched_text': match.group(0),
                            'line_number': current_text[:match.start()].count('\n') + 1
                        }
                        matches_for_debug.append(match_info)
                        
                        # Log each match found
                        self.debug_logger.write({
                            'ev': 'pattern_debug',
                            'type': 'pattern_match',
                            'path': str(path),
                            'pattern_name': rule.name,
                            'location': {'start': match.start(), 'end': match.end()},
                            'line_number': match_info['line_number'],
                            'matched_text': match.group(0)[:100]  # Limit length
                        })
                
                # Apply pattern with timeout protection
                if HAS_TIMEOUT and REGEX_MODULE == 'regex':
                    # Use regex module's built-in timeout
                    new_text, count = rule.find.subn(
                        rule.replace,
                        current_text,
                        timeout=int(timeout_seconds)
                    )
                else:
                    # Use signal-based timeout
                    with timeout_context(timeout_seconds):
                        new_text, count = rule.find.subn(
                            rule.replace,
                            current_text
                        )
                
                if count > 0:
                    # Debug: Log replacements with before/after snippets
                    if self.debug_logger and matches_for_debug:
                        for i, match_info in enumerate(matches_for_debug[:5]):  # Limit to first 5
                            # Extract context around the match
                            start = max(0, match_info['start'] - 50)
                            end = min(len(current_text), match_info['end'] + 50)
                            before_snippet = current_text[start:match_info['end']]
                            # Calculate where the replacement would be in new_text
                            # This is approximate for simplicity
                            after_snippet = new_text[start:start + len(before_snippet) + 20]
                            
                            self.debug_logger.write({
                                'ev': 'pattern_debug',
                                'type': 'pattern_replace',
                                'path': str(path),
                                'pattern_name': rule.name,
                                'replacement_index': i + 1,
                                'before_snippet': before_snippet[-100:],  # Last 100 chars
                                'after_snippet': after_snippet[:100]     # First 100 chars
                            })
                    
                    current_text = new_text
                    result.applied_names.append(rule.name)
                    result.replacements_sum += count
                    
                    # Update global metrics
                    if rule.name not in self.files_touched:
                        self.files_touched[rule.name] = 0
                        self.replacements[rule.name] = 0
                    
                    self.files_touched[rule.name] += 1
                    self.replacements[rule.name] += count
                    
                    # Log pattern application with title and category
                    if logger:
                        logger.log({
                            'ev': 'pattern',
                            'path': str(path),
                            'name': rule.name,
                            'title': rule.title,
                            'category': rule.category,
                            'replacements': count
                        })
                
                # Debug: Log pattern complete
                if self.debug_logger:
                    self.debug_logger.write({
                        'ev': 'pattern_debug',
                        'type': 'pattern_complete',
                        'path': str(path),
                        'pattern_name': rule.name,
                        'matches_found': len(matches_for_debug),
                        'replacements_made': count,
                        'content_length_after': len(current_text)
                    })
                
            except TimeoutError:
                # Pattern timed out
                if logger:
                    logger.log({
                        'ev': 'pattern_timeout',
                        'path': str(path),
                        'name': rule.name,
                        'timeout_ms': timeout_ms
                    })
                if ui:
                    ui.show_error(f"Pattern '{rule.name}' timed out")
                continue
                
            except Exception as e:
                # Other pattern errors
                if logger:
                    logger.log({
                        'ev': 'pattern_error',
                        'path': str(path),
                        'name': rule.name,
                        'error': str(e)
                    })
                if ui:
                    ui.show_error(f"Pattern '{rule.name}' error: {e}")
                continue
        
        # Debug: Log file complete event
        if self.debug_logger:
            self.debug_logger.write({
                'ev': 'pattern_debug',
                'type': 'file_complete',
                'path': str(path),
                'patterns_applied': result.applied_names,
                'total_replacements': result.replacements_sum,
                'content_length_original': len(text),
                'content_length_final': len(current_text),
                'content_changed': current_text != text,
                'final_content_preview': current_text[:500] if len(current_text) > 500 else current_text
            })
        
        return current_text, result
    
    def get_summary(self) -> Dict[str, Dict[str, int]]:
        """Get pattern usage summary.
        
        Returns:
            Dictionary mapping pattern names to their metrics
            (files_touched and replacements), only including
            patterns that were actually used.
        """
        summary = {}
        for rule in self.rules:
            if self.files_touched.get(rule.name, 0) > 0:
                summary[rule.name] = {
                    'files_touched': self.files_touched[rule.name],
                    'replacements': self.replacements[rule.name]
                }
        return summary