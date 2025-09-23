# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""
Integration tests for GNAT validation functionality.

These tests validate the GNAT validator with real Ada code examples,
testing both valid and invalid scenarios. They require GNAT to be
installed on the system.
"""

import pytest
from pathlib import Path
from returns.result import Failure, Success

from adafmt.gnat_validator import (
    GNATValidator,
    validate_ada_content,
    validate_ada_file
)
from adafmt.validation_pipeline import (
    ValidationPipeline,
    validate_and_format_content
)
from adafmt.errors import ValidationError


class TestGNATValidationIntegration:
    """Integration tests for GNAT validation with real Ada code."""
    
    @pytest.fixture
    def validator(self):
        """Create a GNAT validator instance."""
        return GNATValidator()
    
    @pytest.fixture
    def gnat_available(self, validator):
        """Check if GNAT is available, skip tests if not."""
        result = validator.is_available()
        if isinstance(result, Failure):
            pytest.skip("GNAT compiler not available")
        return result.unwrap()
    
    def test_valid_simple_procedure(self, validator, gnat_available):
        """Test validation of a simple valid Ada procedure."""
        ada_code = """
procedure Hello is
begin
   null;
end Hello;
"""
        
        result = validator.validate_content(ada_code)
        
        assert isinstance(result, Success)
        validation_result = result.unwrap()
        assert validation_result.valid
        assert validation_result.exit_code == 0
        assert not validation_result.has_errors
    
    def test_valid_package_spec(self, validator, gnat_available):
        """Test validation of a valid Ada package specification."""
        ada_code = """
package Math_Utils is
   
   function Add (X, Y : Integer) return Integer;
   
   procedure Initialize;
   
end Math_Utils;
"""
        
        result = validator.validate_content(ada_code)
        
        assert isinstance(result, Success)
        validation_result = result.unwrap()
        assert validation_result.valid
        assert validation_result.exit_code == 0
    
    def test_valid_package_body(self, validator, gnat_available):
        """Test validation of a valid Ada package body."""
        ada_code = """
package body Math_Utils is
   
   function Add (X, Y : Integer) return Integer is
   begin
      return X + Y;
   end Add;
   
   procedure Initialize is
   begin
      null;
   end Initialize;
   
end Math_Utils;
"""
        
        result = validator.validate_content(ada_code)
        
        assert isinstance(result, Success)
        validation_result = result.unwrap()
        assert validation_result.valid
        assert validation_result.exit_code == 0
    
    def test_syntax_error_detection(self, validator, gnat_available):
        """Test detection of syntax errors."""
        ada_code = """
procedure Invalid is
begin
   -- Missing semicolon here
   X := 5
   Y := 10;
end Invalid;
"""
        
        result = validator.validate_content(ada_code)
        
        assert isinstance(result, Success)
        validation_result = result.unwrap()
        assert not validation_result.valid
        assert validation_result.exit_code != 0
        assert validation_result.has_errors
        
        # Check that error messages contain useful information
        error_text = " ".join(validation_result.errors).lower()
        assert any(keyword in error_text for keyword in ["syntax", "error", "expected", "missing"])
    
    def test_semantic_error_detection(self, validator, gnat_available):
        """Test detection of semantic errors."""
        ada_code = """
procedure Semantic_Error is
   X : Integer;
   Y : Undefined_Type;  -- Undefined type
begin
   X := Y + 1;
end Semantic_Error;
"""
        
        result = validator.validate_content(ada_code)
        
        assert isinstance(result, Success)
        validation_result = result.unwrap()
        assert not validation_result.valid
        assert validation_result.exit_code != 0
        assert validation_result.has_errors
        
        # Check for semantic error indicators
        error_text = " ".join(validation_result.errors).lower()
        assert any(keyword in error_text for keyword in ["undefined", "not declared", "error"])
    
    def test_warning_detection(self, validator, gnat_available):
        """Test detection of warnings (with -gnatwe they become errors)."""
        ada_code = """
procedure With_Warning is
   X : Integer;  -- Unused variable
begin
   null;
end With_Warning;
"""
        
        result = validator.validate_content(ada_code)
        
        assert isinstance(result, Success)
        validation_result = result.unwrap()
        
        # With -gnatwe flag, warnings become errors
        if not validation_result.valid:
            # Warning treated as error
            assert validation_result.exit_code != 0
            combined_output = (validation_result.stdout + " " + validation_result.stderr).lower()
            assert any(keyword in combined_output for keyword in ["warning", "unused", "not referenced"])
    
    def test_ada_2022_features(self, validator, gnat_available):
        """Test validation with Ada 2022 features."""
        ada_code = """
procedure Ada_2022_Test is
   X : Integer := 42;
begin
   -- Ada 2022 feature: target name symbol
   X := @ + 1;
end Ada_2022_Test;
"""
        
        result = validator.validate_content(ada_code)
        
        assert isinstance(result, Success)
        validation_result = result.unwrap()
        # Should be valid with Ada 2022
        assert validation_result.valid
        assert validation_result.exit_code == 0
    
    def test_file_validation(self, validator, gnat_available, tmp_path):
        """Test validation of actual Ada files."""
        # Create a temporary Ada file
        ada_file = tmp_path / "test.adb"
        ada_content = """
procedure Test_File is
   Message : constant String := "Hello, World!";
begin
   null;
end Test_File;
"""
        ada_file.write_text(ada_content)
        
        result = validator.validate_file(ada_file)
        
        assert isinstance(result, Success)
        validation_result = result.unwrap()
        assert validation_result.valid
        assert validation_result.exit_code == 0
    
    def test_invalid_file_handling(self, validator, gnat_available):
        """Test handling of non-existent files."""
        non_existent_file = Path("/non/existent/file.adb")
        
        result = validator.validate_file(non_existent_file)
        
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, ValidationError)
        assert "does not exist" in error.message.lower()
    
    def test_empty_content_handling(self, validator, gnat_available):
        """Test handling of empty content."""
        result = validator.validate_content("")
        
        assert isinstance(result, Success)
        validation_result = result.unwrap()
        assert validation_result.valid  # Empty content is considered valid
        assert validation_result.exit_code == 0
    
    @pytest.mark.asyncio
    async def test_async_validation(self, validator, gnat_available):
        """Test asynchronous validation."""
        ada_code = """
procedure Async_Test is
   X : Integer := 123;
begin
   X := X + 1;
end Async_Test;
"""
        
        result = await validator.validate_content_async(ada_code)
        
        assert isinstance(result, Success)
        validation_result = result.unwrap()
        assert validation_result.valid
        assert validation_result.exit_code == 0
    
    def test_convenience_functions(self, gnat_available):
        """Test convenience functions for validation."""
        valid_code = """
procedure Convenience_Test is
begin
   null;
end Convenience_Test;
"""
        
        # Test validate_ada_content convenience function
        result = validate_ada_content(valid_code)
        
        assert isinstance(result, Success)
        validation_result = result.unwrap()
        assert validation_result.valid


class TestValidationPipelineIntegration:
    """Integration tests for the complete validation pipeline."""
    
    @pytest.fixture
    def pipeline(self):
        """Create a validation pipeline."""
        return ValidationPipeline(
            enabled_patterns={"comment_spacing", "assignment_spacing"},
            validate_with_gnat=True
        )
    
    @pytest.fixture
    def gnat_available(self, pipeline):
        """Check if GNAT is available, skip tests if not."""
        result = pipeline.is_gnat_available()
        if isinstance(result, Failure) or not result.unwrap():
            pytest.skip("GNAT compiler not available")
        return True
    
    def test_format_and_validate_valid_code(self, pipeline, gnat_available):
        """Test formatting and validation of valid Ada code."""
        ada_code = """
procedure Format_Test is
   X:=42;  -- Poor spacing
   --No space after comment
begin
   X := X + 1;
end Format_Test;
"""
        
        result = pipeline.process_content(ada_code)
        
        assert isinstance(result, Success)
        pipeline_result = result.unwrap()
        
        assert pipeline_result.success
        assert pipeline_result.formatting_applied  # Should have fixed spacing
        assert pipeline_result.validation_passed   # Should pass GNAT validation
        assert pipeline_result.is_safe_to_apply
        
        # Check that formatting was applied
        assert pipeline_result.has_changes
        assert "X := 42" in pipeline_result.formatted_content  # Fixed assignment spacing
        assert "-- No space" in pipeline_result.formatted_content  # Fixed comment spacing
    
    def test_format_and_validate_breaks_syntax(self, pipeline, gnat_available):
        """Test handling when formatting would break syntax (shouldn't happen)."""
        # This is a theoretical test - our parser-based formatting shouldn't break syntax
        ada_code = """
procedure Syntax_Test is
   X : Integer := 42;
begin
   X := X + 1;
end Syntax_Test;
"""
        
        result = pipeline.process_content(ada_code)
        
        assert isinstance(result, Success)
        pipeline_result = result.unwrap()
        
        # Should succeed and pass validation
        assert pipeline_result.success
        assert pipeline_result.validation_passed
    
    def test_invalid_code_rejected(self, pipeline, gnat_available):
        """Test that invalid Ada code is properly rejected."""
        invalid_ada = """
procedure Invalid is
begin
   -- Syntax error: missing semicolon
   X := 5
   Y := 10;
end Invalid;
"""
        
        result = pipeline.process_content(invalid_ada)
        
        # Should fail at the parsing stage before formatting
        assert isinstance(result, Failure)
    
    def test_convenience_pipeline_function(self, gnat_available):
        """Test convenience function for pipeline processing."""
        ada_code = """
procedure Convenience is
   X:=1;  -- Bad spacing
begin
   null;
end Convenience;
"""
        
        result = validate_and_format_content(
            ada_code,
            enabled_patterns={"assignment_spacing"},
            validate_with_gnat=True
        )
        
        assert isinstance(result, Success)
        pipeline_result = result.unwrap()
        
        assert pipeline_result.success
        assert pipeline_result.formatting_applied
        assert pipeline_result.validation_passed
        assert "X := 1" in pipeline_result.formatted_content
    
    def test_pipeline_statistics(self, pipeline, gnat_available):
        """Test pipeline statistics reporting."""
        stats = pipeline.get_pipeline_statistics()
        
        assert isinstance(stats, dict)
        assert "gnat_validation_enabled" in stats
        assert "ada_version" in stats
        assert "gnat_available" in stats
        assert stats["gnat_available"] is True  # Should be available in this test
        assert "available_patterns" in stats
    
    @pytest.mark.asyncio
    async def test_async_pipeline(self, pipeline, gnat_available):
        """Test asynchronous pipeline processing."""
        ada_code = """
procedure Async_Pipeline is
   X:=42;
begin
   null;
end Async_Pipeline;
"""
        
        result = await pipeline.process_content_async(ada_code)
        
        assert isinstance(result, Success)
        pipeline_result = result.unwrap()
        
        assert pipeline_result.success
        assert pipeline_result.formatting_applied
        assert pipeline_result.validation_passed


class TestRealWorldScenarios:
    """Integration tests with real-world Ada code scenarios."""
    
    @pytest.fixture
    def pipeline_no_gnat(self):
        """Create pipeline without GNAT validation for comparison."""
        return ValidationPipeline(validate_with_gnat=False)
    
    @pytest.fixture  
    def pipeline_with_gnat(self):
        """Create pipeline with GNAT validation."""
        pipeline = ValidationPipeline(validate_with_gnat=True)
        # Skip if GNAT not available
        gnat_result = pipeline.is_gnat_available()
        if isinstance(gnat_result, Failure) or not gnat_result.unwrap():
            pytest.skip("GNAT compiler not available")
        return pipeline
    
    def test_complex_ada_package(self, pipeline_with_gnat):
        """Test with a more complex Ada package."""
        ada_code = """
with Ada.Text_IO;
package body Complex_Example is
   
   procedure Process_Data(Input:Integer;Output:out Integer) is
      Temp:Integer:=Input*2;--Poor spacing
   begin
      --Check bounds
      if Temp>100 then
         Output:=100;
      else
         Output:=Temp;
      end if;
   end Process_Data;
   
   function Calculate(X,Y:Float)return Float is
   begin
      return X*Y+1.0;
   end Calculate;
   
end Complex_Example;
"""
        
        result = pipeline_with_gnat.process_content(ada_code)
        
        assert isinstance(result, Success)
        pipeline_result = result.unwrap()
        
        # Should format successfully
        assert pipeline_result.success
        assert pipeline_result.formatting_applied
        
        # Check some specific formatting improvements
        formatted = pipeline_result.formatted_content
        assert "Input : Integer; Output : out Integer" in formatted  # Fixed parameter spacing
        assert "Temp : Integer := Input * 2; -- Poor spacing" in formatted  # Fixed multiple issues
        assert "-- Check bounds" in formatted  # Fixed comment spacing
        
        # Should pass GNAT validation
        assert pipeline_result.validation_passed
    
    def test_string_literal_preservation(self, pipeline_with_gnat):
        """Test that string literals are preserved during formatting."""
        ada_code = """
procedure String_Test is
   Message1 : String := "Don't change:=this=>spacing..in--strings";
   Message2:String:="Or  this  :=  spacing";
   X:=42;  -- But fix this spacing
begin
   null;
end String_Test;
"""
        
        result = pipeline_with_gnat.process_content(ada_code)
        
        assert isinstance(result, Success)
        pipeline_result = result.unwrap()
        
        assert pipeline_result.success
        assert pipeline_result.formatting_applied
        assert pipeline_result.validation_passed
        
        formatted = pipeline_result.formatted_content
        
        # String contents should be unchanged
        assert "Don't change:=this=>spacing..in--strings" in formatted
        assert "Or  this  :=  spacing" in formatted
        
        # But spacing outside strings should be fixed
        assert "X := 42" in formatted
        assert "Message2 : String :=" in formatted