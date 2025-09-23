#!/usr/bin/env python3
"""Test the assignment spacing rule and demonstrate parameterization concepts."""

import pytest
from pathlib import Path
import sys
import os

# Add src to path so we can import adafmt modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from adafmt.commands.format_command import FormatCommandProcessor


class TestAssignmentSpacingRule:
    """Test assignment spacing rule with different parameterization scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = FormatCommandProcessor()
    
    def test_basic_assignment_spacing(self):
        """Test basic assignment operator spacing."""
        # Test cases: input → expected output
        test_cases = [
            # Basic cases
            ("X:=5;", "X := 5;"),
            ("Count:=0;", "Count := 0;"),
            ("Result:=Function_Call();", "Result := Function_Call();"),
            
            # Already correct (should not change)
            ("X := 5;", "X := 5;"),
            ("Count := 0;", "Count := 0;"),
            
            # Type declarations with assignments
            ("Variable:Integer:=42;", "Variable : Integer := 42;"),
            ("Status:Boolean:=True;", "Status : Boolean := True;"),
            
            # Function parameters
            ("Call(Param:=Value);", "Call(Param := Value);"),
            ("Func(A:=1,B:=2);", "Func(A := 1, B := 2);"),
        ]
        
        for input_code, expected in test_cases:
            result = self.processor._fix_assignment_spacing(input_code)
            assert result == expected, f"Input: {input_code!r}, Expected: {expected!r}, Got: {result!r}"
    
    def test_assignment_rule_parameterization_concepts(self):
        """Demonstrate how the assignment rule could be parameterized."""
        
        # Current rule (hardcoded): X:=Y → X := Y (single space before and after)
        input_code = "Variable:=42;"
        current_result = self.processor._fix_assignment_spacing(input_code)
        assert current_result == "Variable := 42;"
        
        # Parameterization concepts (hypothetical configurations):
        
        # Config 1: No spaces around :=
        # {"rule": "assignment_spacing", "spaces_before": 0, "spaces_after": 0}
        # Expected: "Variable:=42;"
        
        # Config 2: Two spaces around :=  
        # {"rule": "assignment_spacing", "spaces_before": 2, "spaces_after": 2}
        # Expected: "Variable  :=  42;"
        
        # Config 3: Space only after :=
        # {"rule": "assignment_spacing", "spaces_before": 0, "spaces_after": 1}
        # Expected: "Variable:= 42;"
        
        # Config 4: Different spacing for type declarations vs assignments
        # {"rule": "assignment_spacing", "type_decl_spaces": 1, "assignment_spaces": 1}
        # For "Var:Integer:=42;" → "Var : Integer := 42;"
        
        print("✅ Assignment rule parameterization concepts demonstrated")
        print("   - Current: single space before and after :=")
        print("   - Could parameterize: spaces_before, spaces_after") 
        print("   - Could handle: type declarations vs regular assignments")
        print("   - Could support: different spacing policies")
    
    def test_hypothetical_rule_configuration_structure(self):
        """Show how rule configuration could be structured."""
        
        # Hypothetical JSON configuration for assignment spacing rule:
        hypothetical_config = {
            "rule_name": "assignment_spacing",
            "enabled": True,
            "parameters": {
                "spaces_before": 1,
                "spaces_after": 1,
                "apply_to_type_declarations": True,
                "apply_to_assignments": True,
                "apply_to_parameters": True
            },
            "exceptions": [
                # Could have file patterns or other exceptions
                "*.generated.adb"  # Skip generated files
            ]
        }
        
        # This shows how each rule could have:
        # 1. A human-friendly name
        # 2. Enable/disable toggle  
        # 3. Configurable parameters
        # 4. Exception handling
        
        print("✅ Rule configuration structure concept:")
        print(f"   {hypothetical_config}")
        
        # The rule implementation would read these parameters:
        # def _fix_assignment_spacing(self, content: str, config: dict) -> str:
        #     spaces_before = config.get("spaces_before", 1)
        #     spaces_after = config.get("spaces_after", 1)
        #     pattern = rf'(\w|\))(:=)(\w)'
        #     replacement = rf'\1{" " * spaces_before}\2{" " * spaces_after}\3'
        #     return re.sub(pattern, replacement, content)