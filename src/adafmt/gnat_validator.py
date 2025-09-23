# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
GNAT compiler validation for Ada source code.

This module provides validation of Ada source code using the GNAT compiler
to ensure that formatting changes do not introduce syntax or semantic errors.
It uses functional error handling with Result types.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from returns.future import future_safe
from returns.io import IOFailure, IOResult, IOSuccess, impure_safe
from returns.result import Failure, Result, Success

from .errors import ValidationError


@dataclass(frozen=True)
class ValidationResult:
    """Result of GNAT validation.
    
    Attributes:
        valid: Whether the code passed validation
        exit_code: GNAT compiler exit code
        stdout: Standard output from compiler
        stderr: Standard error from compiler
        warnings: List of warning messages
        errors: List of error messages
        command_used: The GNAT command that was executed
    """
    valid: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    command_used: str = ""
    
    @property
    def has_warnings(self) -> bool:
        """Check if validation produced warnings."""
        return len(self.warnings) > 0
    
    @property
    def has_errors(self) -> bool:
        """Check if validation produced errors."""
        return len(self.errors) > 0


class GNATValidator:
    """GNAT compiler validator for Ada source code.
    
    This validator uses the GNAT compiler to check Ada syntax and semantics.
    It supports various GNAT flags and can handle both syntax-only checks
    and full semantic validation.
    """
    
    def __init__(
        self,
        gnat_executable: str = "gcc",
        gnat_flags: Optional[List[str]] = None,
        timeout_seconds: float = 30.0,
        use_syntax_only: bool = True
    ):
        """Initialize the GNAT validator.
        
        Args:
            gnat_executable: Path to GCC/GNAT executable
            gnat_flags: Additional GNAT flags to use
            timeout_seconds: Timeout for compilation
            use_syntax_only: If True, use syntax-only checking (-gnatc)
        """
        self.gnat_executable = gnat_executable
        self.timeout_seconds = timeout_seconds
        self.use_syntax_only = use_syntax_only
        
        # Default GNAT flags for validation
        default_flags = [
            "-c",           # Compile only
            "-gnatc",       # Syntax/semantic check only (no code generation)
            "-gnatf",       # Full error messages
            "-gnat2022",    # Use Ada 2022 standard
            "-gnatwe",      # Treat warnings as errors
        ]
        
        if gnat_flags:
            self.gnat_flags = default_flags + gnat_flags
        else:
            self.gnat_flags = default_flags
    
    def is_available(self) -> Result[bool, ValidationError]:
        """Check if GNAT compiler is available.
        
        Returns:
            Result[bool, ValidationError]: True if available, or error
        """
        return self._check_gnat_availability()
    
    @impure_safe
    def _check_gnat_availability_internal(self) -> bool:
        """Internal availability check with automatic exception handling.
        
        Returns:
            bool: True if GNAT is available
            
        Note:
            @impure_safe automatically converts exceptions to IOResult[bool, Exception]
        """
        import subprocess
        
        try:
            # Try to run gcc --version
            result = subprocess.run(
                [self.gnat_executable, "--version"],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            return result.returncode == 0
        except FileNotFoundError:
            raise RuntimeError(f"GNAT compiler '{self.gnat_executable}' not found in PATH")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"GNAT compiler '{self.gnat_executable}' timed out")
    
    def _check_gnat_availability(self) -> Result[bool, ValidationError]:
        """Check GNAT availability with error mapping.
        
        Returns:
            Result[bool, ValidationError]: Availability result or error
        """
        result = self._check_gnat_availability_internal()
        
        if isinstance(result, IOFailure):
            exc = result.failure()
            return Failure(ValidationError(
                path=Path(""),
                exit_code=-1,
                command=f"{self.gnat_executable} --version",
                message=str(exc)
            ))
        
        # result is IOSuccess[bool] here
        return Success(result.unwrap())
    
    def validate_content(
        self,
        content: str,
        file_path: Optional[Path] = None,
        ada_version: str = "2022"
    ) -> Result[ValidationResult, ValidationError]:
        """Validate Ada content using GNAT compiler.
        
        Args:
            content: Ada source code to validate
            file_path: Optional path for context (affects file extension)
            ada_version: Ada version to use (2022, 2012, 2005, 95)
            
        Returns:
            Result[ValidationResult, ValidationError]: Validation result or error
        """
        if not content.strip():
            return Success(ValidationResult(
                valid=True,
                exit_code=0,
                command_used="(empty content - skipped)"
            ))
        
        # Determine file extension
        if file_path:
            suffix = file_path.suffix.lower()
            if suffix not in ['.adb', '.ads', '.ada']:
                suffix = '.adb'  # Default to body
        else:
            suffix = '.adb'  # Default to body
        
        # Create temporary file
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=suffix,
                encoding='utf-8',
                delete=False
            ) as temp_file:
                temp_file.write(content)
                temp_path = Path(temp_file.name)
            
            # Validate the temporary file
            result = self.validate_file(temp_path, ada_version)
            
            # Clean up
            try:
                temp_path.unlink()
            except OSError:
                pass  # Ignore cleanup errors
            
            return result
            
        except Exception as e:
            return Failure(ValidationError(
                path=file_path or Path(""),
                exit_code=-1,
                command="tempfile creation",
                message=f"Failed to create temporary file: {e}"
            ))
    
    async def validate_content_async(
        self,
        content: str,
        file_path: Optional[Path] = None,
        ada_version: str = "2022"
    ) -> Result[ValidationResult, ValidationError]:
        """Asynchronously validate Ada content.
        
        Args:
            content: Ada source code to validate
            file_path: Optional path for context
            ada_version: Ada version to use
            
        Returns:
            Result[ValidationResult, ValidationError]: Validation result or error
        """
        # Use async subprocess for validation
        result = await self._validate_content_async_internal(content, file_path, ada_version)
        
        # Convert FutureResult to Result
        if isinstance(result, Failure):
            exc = result.failure()
            if isinstance(exc, ValidationError):
                return Failure(exc)
            else:
                return Failure(ValidationError(
                    path=file_path or Path(""),
                    exit_code=-1,
                    command=self.gnat_executable,
                    message=str(exc)
                ))
        
        return Success(result.unwrap())
    
    @future_safe
    async def _validate_content_async_internal(
        self,
        content: str,
        file_path: Optional[Path],
        ada_version: str
    ) -> ValidationResult:
        """Internal async validation with automatic exception handling.
        
        Args:
            content: Ada source code to validate
            file_path: Optional path for context
            ada_version: Ada version to use
            
        Returns:
            ValidationResult: Validation result
            
        Note:
            @future_safe automatically converts exceptions to IOResult[ValidationResult, Exception]
        """
        import asyncio
        
        if not content.strip():
            return ValidationResult(
                valid=True,
                exit_code=0,
                command_used="(empty content - skipped)"
            )
        
        # Determine file extension
        suffix = '.adb'
        if file_path and file_path.suffix.lower() in ['.adb', '.ads', '.ada']:
            suffix = file_path.suffix.lower()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            encoding='utf-8',
            delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        
        try:
            # Build command
            command = self._build_command(temp_path, ada_version)
            
            # Run GNAT compilation
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=temp_path.parent
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds
            )
            
            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')
            
            # Parse output for warnings and errors
            warnings, errors = self._parse_gnat_output(stdout_text, stderr_text)
            
            return ValidationResult(
                valid=process.returncode == 0,
                exit_code=process.returncode or -1,
                stdout=stdout_text,
                stderr=stderr_text,
                warnings=warnings,
                errors=errors,
                command_used=' '.join(command)
            )
            
        finally:
            # Clean up temporary file
            try:
                temp_path.unlink()
            except OSError:
                pass
    
    def validate_file(
        self,
        file_path: Union[str, Path],
        ada_version: str = "2022"
    ) -> Result[ValidationResult, ValidationError]:
        """Validate Ada file using GNAT compiler.
        
        Args:
            file_path: Path to Ada source file
            ada_version: Ada version to use
            
        Returns:
            Result[ValidationResult, ValidationError]: Validation result or error
        """
        path = Path(file_path)
        
        if not path.exists():
            return Failure(ValidationError(
                path=path,
                exit_code=-1,
                command="file check",
                message=f"File does not exist: {path}"
            ))
        
        return self._validate_file_internal(path, ada_version)
    
    @impure_safe
    def _validate_file_sync_internal(self, path: Path, ada_version: str) -> ValidationResult:
        """Internal synchronous file validation with automatic exception handling.
        
        Args:
            path: Path to Ada file
            ada_version: Ada version to use
            
        Returns:
            ValidationResult: Validation result
            
        Note:
            @impure_safe automatically converts exceptions to IOResult[ValidationResult, Exception]
        """
        import subprocess
        
        # Build command
        command = self._build_command(path, ada_version)
        
        # Run GNAT compilation
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            cwd=path.parent
        )
        
        # Parse output for warnings and errors
        warnings, errors = self._parse_gnat_output(result.stdout, result.stderr)
        
        return ValidationResult(
            valid=result.returncode == 0,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            warnings=warnings,
            errors=errors,
            command_used=' '.join(command)
        )
    
    def _validate_file_internal(
        self,
        path: Path,
        ada_version: str
    ) -> Result[ValidationResult, ValidationError]:
        """Internal file validation with error mapping.
        
        Args:
            path: Path to Ada file
            ada_version: Ada version to use
            
        Returns:
            Result[ValidationResult, ValidationError]: Validation result or error
        """
        result = self._validate_file_sync_internal(path, ada_version)
        
        if isinstance(result, IOFailure):
            exc = result.failure()
            return Failure(ValidationError(
                path=path,
                exit_code=-1,
                command=f"gnat validation of {path}",
                message=str(exc)
            ))
        
        return Success(result.unwrap())
    
    def _build_command(self, file_path: Path, ada_version: str) -> List[str]:
        """Build GNAT command for validation.
        
        Args:
            file_path: Path to Ada file
            ada_version: Ada version to use
            
        Returns:
            List[str]: Command arguments
        """
        command = [self.gnat_executable]
        
        # Add base flags
        command.extend(self.gnat_flags)
        
        # Set Ada version
        ada_flag = f"-gnat{ada_version}"
        if ada_flag not in command:
            # Replace existing -gnat flag if present
            for i, flag in enumerate(command):
                if flag.startswith('-gnat') and len(flag) > 5:
                    command[i] = ada_flag
                    break
            else:
                command.append(ada_flag)
        
        # Add output file (to temp location)
        output_file = file_path.parent / f"{file_path.stem}_validation.ali"
        command.extend(["-o", str(output_file)])
        
        # Add source file
        command.append(str(file_path))
        
        return command
    
    def _parse_gnat_output(self, stdout: str, stderr: str) -> tuple[List[str], List[str]]:
        """Parse GNAT compiler output to extract warnings and errors.
        
        Args:
            stdout: Standard output from GNAT
            stderr: Standard error from GNAT
            
        Returns:
            tuple[List[str], List[str]]: (warnings, errors)
        """
        warnings = []
        errors = []
        
        # Combine stdout and stderr for parsing
        all_output = stdout + "\n" + stderr
        
        for line in all_output.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Check for warning patterns
            if ("warning:" in line.lower() or 
                "warning --" in line.lower() or
                line.endswith("(warning)")):
                warnings.append(line)
            
            # Check for error patterns
            elif ("error:" in line.lower() or
                  "fatal error:" in line.lower() or
                  "compilation error" in line.lower() or
                  line.endswith("(error)") or
                  "illegal" in line.lower()):
                errors.append(line)
            
            # Check for compilation failed messages
            elif "compilation failed" in line.lower():
                errors.append(line)
        
        return warnings, errors


# Convenience functions for common validation scenarios

def validate_ada_content(
    content: str,
    file_path: Optional[Path] = None,
    gnat_flags: Optional[List[str]] = None
) -> Result[ValidationResult, ValidationError]:
    """Validate Ada content using default GNAT settings.
    
    Args:
        content: Ada source code to validate
        file_path: Optional path for context
        gnat_flags: Optional additional GNAT flags
        
    Returns:
        Result[ValidationResult, ValidationError]: Validation result or error
    """
    validator = GNATValidator(gnat_flags=gnat_flags)
    return validator.validate_content(content, file_path)


def validate_ada_file(
    file_path: Union[str, Path],
    gnat_flags: Optional[List[str]] = None
) -> Result[ValidationResult, ValidationError]:
    """Validate Ada file using default GNAT settings.
    
    Args:
        file_path: Path to Ada source file
        gnat_flags: Optional additional GNAT flags
        
    Returns:
        Result[ValidationResult, ValidationError]: Validation result or error
    """
    validator = GNATValidator(gnat_flags=gnat_flags)
    return validator.validate_file(file_path)


async def validate_ada_content_async(
    content: str,
    file_path: Optional[Path] = None,
    gnat_flags: Optional[List[str]] = None
) -> Result[ValidationResult, ValidationError]:
    """Asynchronously validate Ada content using default GNAT settings.
    
    Args:
        content: Ada source code to validate
        file_path: Optional path for context
        gnat_flags: Optional additional GNAT flags
        
    Returns:
        Result[ValidationResult, ValidationError]: Validation result or error
    """
    validator = GNATValidator(gnat_flags=gnat_flags)
    return await validator.validate_content_async(content, file_path)