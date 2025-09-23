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
            # Note: -gnatwe removed to avoid file naming warnings during validation
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
        
        # result is IOSuccess[bool] here - extract the bool value
        if isinstance(result, IOSuccess):
            # For IOResult, use unsafe_perform_io to extract the boolean value
            from returns.unsafe import unsafe_perform_io
            availability = unsafe_perform_io(result.unwrap())
            return Success(availability)
        else:
            # Should not happen but type safety
            return Failure(ValidationError(
                path=Path(""),
                exit_code=-1,
                command=f"{self.gnat_executable} --version",
                message="Unknown error"
            ))
    
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
            # Auto-detect based on content when no file_path provided
            suffix = self._detect_ada_file_type(content)
        
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
            
            # If this is a package body, create a minimal spec file
            spec_path = None
            if suffix == '.adb' and 'package body ' in content.lower():
                spec_path = self._create_minimal_spec_for_body(content, temp_path)
            
            # Validate the temporary file
            result = self.validate_file(temp_path, ada_version)
            
            # Clean up
            try:
                temp_path.unlink()
                if spec_path and spec_path.exists():
                    spec_path.unlink()
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
        # @future_safe returns IOResult, so we need to handle it accordingly
        result = await self._validate_content_async_internal(content, file_path, ada_version)
        
        # Handle IOResult from @future_safe
        if isinstance(result, IOFailure):
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
        elif isinstance(result, IOSuccess):
            # Extract the validation result using unsafe_perform_io
            from returns.unsafe import unsafe_perform_io
            validation_result = unsafe_perform_io(result.unwrap())
            return Success(validation_result)
        else:
            # Should not happen, but handle just in case
            return Failure(ValidationError(
                path=file_path or Path(""),
                exit_code=-1,
                command=self.gnat_executable,
                message="Unknown async validation error"
            ))
    
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
        if file_path and file_path.suffix.lower() in ['.adb', '.ads', '.ada']:
            suffix = file_path.suffix.lower()
        else:
            # Auto-detect based on content when no file_path provided
            suffix = self._detect_ada_file_type(content)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            encoding='utf-8',
            delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        
        # If this is a package body, create a minimal spec file
        spec_path = None
        if suffix == '.adb' and 'package body ' in content.lower():
            spec_path = self._create_minimal_spec_for_body(content, temp_path)
        
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
                exit_code=process.returncode if process.returncode is not None else -1,
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
                if spec_path and spec_path.exists():
                    spec_path.unlink()
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
        
        # For IOResult, we need to use unsafe_perform_io to extract the actual value
        # This is the recommended approach for boundary operations
        from returns.unsafe import unsafe_perform_io
        validation_result = unsafe_perform_io(result.unwrap())
        return Success(validation_result)
    
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
        
        # For syntax-only checking (-gnatc), don't specify output file
        # GNAT will handle this automatically and won't create object files
        
        # Add source file
        command.append(str(file_path))
        
        return command
    
    def _detect_ada_file_type(self, content: str) -> str:
        """Detect whether Ada content is a specification (.ads) or body (.adb).
        
        Args:
            content: Ada source code content
            
        Returns:
            str: File extension (.ads or .adb)
        """
        # Simple heuristics to detect file type
        content_lower = content.lower().strip()
        
        # Look for package/generic specification keywords without "body"
        lines = content_lower.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('--'):
                continue
                
            # Package specification
            if line.startswith('package ') and ' body ' not in line and line.endswith(' is'):
                return '.ads'
            # Generic package specification  
            if line.startswith('generic') or (line.startswith('package ') and ' body ' not in line):
                return '.ads'
            # Procedure/function specification (might be in spec)
            if (line.startswith('procedure ') or line.startswith('function ')) and ' is ' in line:
                # Could be spec or body, continue checking
                continue
            # Package body
            if 'package body ' in line:
                return '.adb'
            # Procedure/function body with "begin"
            if line.startswith('procedure ') and 'begin' in content_lower:
                return '.adb'
            if line.startswith('function ') and 'begin' in content_lower:
                return '.adb'
        
        # Default to body if unclear
        return '.adb'
    
    def _create_minimal_spec_for_body(self, body_content: str, body_path: Path) -> Path | None:
        """Create a minimal specification file for a package body.
        
        Args:
            body_content: Content of the package body
            body_path: Path to the body file
            
        Returns:
            Path: Path to created spec file, or None if creation failed
        """
        try:
            # Extract package name from body (preserve original case)
            package_name = None
            for line in body_content.split('\n'):
                line = line.strip()
                if line.lower().startswith('package body '):
                    # Extract package name, preserving case
                    parts = line.split()
                    if len(parts) >= 3:
                        package_name = parts[2]
                        # Remove 'is' if present
                        if package_name.endswith(' is'):
                            package_name = package_name[:-3]
                        break
            
            if not package_name:
                return None
            
            # Create minimal spec content (use exact case from body)
            # Extract function/procedure declarations from body for spec
            declarations = self._extract_declarations_from_body(body_content)
            
            spec_content = f"""package {package_name} is
{declarations}
   pragma Elaborate_Body;
end {package_name};
"""
            
            # Create spec file in same directory with package name
            # GNAT expects filename to match package name in lowercase
            package_filename = package_name.lower() + '.ads'
            spec_path = body_path.parent / package_filename
            spec_path.write_text(spec_content, encoding='utf-8')
            
            return spec_path
            
        except Exception:
            return None
    
    def _extract_declarations_from_body(self, body_content: str) -> str:
        """Extract function and procedure declarations from package body.
        
        Args:
            body_content: Content of the package body
            
        Returns:
            str: Declaration strings for the specification
        """
        declarations = []
        lines = body_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for function or procedure declarations
            if (line.startswith('function ') or line.startswith('procedure ')) and ' is ' in line:
                # Extract the declaration part (before 'is')
                declaration = line.split(' is ')[0].strip()
                
                # Handle multi-line declarations
                while not declaration.endswith(';') and i + 1 < len(lines):
                    i += 1
                    next_line = lines[i].strip()
                    if ' is ' in next_line:
                        declaration += ' ' + next_line.split(' is ')[0].strip()
                        break
                    else:
                        declaration += ' ' + next_line
                
                # Clean up and add semicolon if needed
                if not declaration.endswith(';'):
                    declaration += ';'
                
                declarations.append(f'   {declaration}')
            
            i += 1
        
        return '\n'.join(declarations) if declarations else '   -- No public declarations'
    
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