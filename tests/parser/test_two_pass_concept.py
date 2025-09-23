# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

"""Demonstrate the concept of two-pass formatting with type awareness."""


def demonstrate_two_pass_concept():
    """Show how two-pass formatting would work conceptually."""
    
    print("=== Two-Pass Formatting Concept ===\n")
    print("Using parser type information to handle formatting correctly\n")
    
    # Original code
    print("ORIGINAL CODE:")
    print("-" * 80)
    original = '''procedure Example is
   -- Long string that ALS might corrupt
   Msg : String := "This is a very long message that exceeds line limit and ALS might break incorrectly";
   X:Integer:=42;  -- Needs spacing
begin
   null;
end Example;'''
    print(original)
    
    print("\n\nPASS 1: Pre-ALS Patterns")
    print("-" * 80)
    print("Goal: Prepare code for ALS, prevent ALS bugs")
    print("\n1. Parser identifies string literal nodes:")
    print("   - visitString_literal() called for line 3")
    print("   - Node type: String_literal")
    print("   - Content: \"This is a very long message...\"")
    print("   - Line length: 93 chars (exceeds 80)")
    
    print("\n2. Pre-ALS pattern: Break long strings safely")
    print("   Action: Split string using Ada concatenation")
    
    pre_als_result = '''procedure Example is
   -- Long string that ALS might corrupt
   Msg : String := 
      "This is a very long message that exceeds line limit " &
      "and ALS might break incorrectly";
   X:Integer:=42;  -- Needs spacing
begin
   null;
end Example;'''
    
    print("\nResult after Pre-ALS patterns:")
    print(pre_als_result)
    
    print("\n\nPASS 2: ALS Formatting")
    print("-" * 80)
    print("ALS runs on the pre-processed code")
    print("- Validates syntax (no parse errors)")
    print("- Formats structure and indentation")
    print("- DOESN'T corrupt strings (they're already safe)")
    
    als_result = '''procedure Example is
   -- Long string that ALS might corrupt
   Msg : String := 
      "This is a very long message that exceeds line limit " &
      "and ALS might break incorrectly";
   X:Integer:=42;  -- Needs spacing
begin
   null;
end Example;'''
    
    print("\nResult after ALS:")
    print(als_result)
    
    print("\n\nPASS 3: Post-ALS Patterns")
    print("-" * 80)
    print("Goal: Fix issues ALS doesn't handle")
    
    print("\n1. Parser identifies nodes needing fixes:")
    print("   - visitObject_declaration() for line 6")
    print("   - Found ':=' without proper spacing")
    print("   - NOT inside string literal (parser confirms)")
    
    print("\n2. Post-ALS pattern: Fix operator spacing")
    print("   Action: Add spaces around :=")
    
    final_result = '''procedure Example is
   -- Long string that ALS might corrupt
   Msg : String := 
      "This is a very long message that exceeds line limit " &
      "and ALS might break incorrectly";
   X : Integer := 42;  -- Needs spacing
begin
   null;
end Example;'''
    
    print("\nFINAL RESULT:")
    print(final_result)
    
    print("\n\nKEY INSIGHTS:")
    print("-" * 80)
    print("1. Parser provides TYPE information:")
    print("   - visitString_literal() → We're in a string")
    print("   - visitObject_declaration() → We're in a declaration")
    print("   - visitAssignment_statement() → We're in an assignment")
    print()
    print("2. Two-phase approach prevents issues:")
    print("   - Pre-ALS: Fix things that would confuse ALS")
    print("   - Post-ALS: Fix things ALS doesn't handle")
    print()
    print("3. Type awareness prevents corruption:")
    print("   - Never modify operators inside string literals")
    print("   - Apply patterns only in appropriate contexts")


def show_visitor_pattern():
    """Show how the visitor pattern gives us type information."""
    
    print("\n\n=== Visitor Pattern Type Information ===\n")
    
    print("When the parser visits the AST, it calls specific methods:")
    print()
    
    print("class FormattingVisitor(Ada2022ParserVisitor):")
    print("    ")
    print("    def visitString_literal(self, ctx):")
    print("        # We KNOW this is a string literal")
    print("        # Safe to break long strings here")
    print("        text = ctx.getText()")
    print("        if len(text) > 80:")
    print("            return self.break_string_safely(text)")
    print("    ")
    print("    def visitObject_declaration(self, ctx):")
    print("        # We KNOW this is an object declaration")
    print("        # Safe to fix := spacing here")
    print("        # Check for := operator and fix spacing")
    print("    ")
    print("    def visitAssignment_statement(self, ctx):")
    print("        # We KNOW this is an assignment")
    print("        # Different context, same := fix needed")
    print()
    print("The parser tells us EXACTLY what type of construct we're in!")


if __name__ == "__main__":
    demonstrate_two_pass_concept()
    show_visitor_pattern()
    
    print("\n\nCONCLUSION:")
    print("=" * 80)
    print("Using parser type information, we can:")
    print("1. Apply patterns only in the correct context")
    print("2. Prevent ALS bugs with pre-processing")
    print("3. Clean up remaining issues post-ALS")
    print("4. Never corrupt string literals or other constructs")
    print("=" * 80)