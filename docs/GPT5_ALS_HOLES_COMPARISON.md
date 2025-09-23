# GPT-5 vs Research Comparison: ALS Formatting Holes

**Version:** 1.0.0  
**Date:** January 2025  
**License:** BSD-3-Clause  
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Analysis Document

Comparison between GPT-5's analysis and our empirical research findings.

## GPT-5 Response Analysis

GPT-5 provided a **very practical, experience-based list** with excellent source citations. Key insights:

### GPT-5's Top 6 ALS Formatting Holes:

1. **End-of-line comment spacing after `--`** ✓
   - **Status**: Confirmed by our testing
   - **Source**: [GCC GNAT User's Guide](https://gcc.gnu.org/onlinedocs/gcc-4.4.7/gnat_ugn_unw/Formatting-Comments.html)
   - **Note**: GNATpp explicitly preserves existing spacing

2. **Vertical alignment across lines** ✓
   - **Status**: Confirmed - not in our initial matrix but critical
   - **Examples**: Aligning `:`, `:=`, `=>`, `--` into columns
   - **Source**: [AdaCore GNAT Utils](https://docs.adacore.com/gnat_ugn-docs/html/gnat_ugn/gnat_ugn/gnat_utility_programs.html)

3. **Two spaces after `--` for whole-line vs EOL comments** ✓
   - **Status**: Matches our comment spacing findings
   - **Distinction**: Whole-line vs end-of-line comment rules differ

4. **Identifier/keyword casing with dictionary exceptions** ✓
   - **Status**: New - not in our matrix but important
   - **Example**: Keep `USB_ID` as written, not `Usb_Id`
   - **Tool**: GNATpp supports this; GNATformat doesn't

5. **Region-based "don't format this" guards** ✓
   - **Status**: New - critical for mixed code
   - **Example**: `--!pp off/on` guards not honored by VS Code extension
   - **Source**: [Ada Forum](https://forum.ada-lang.io/t/customizing-formatting-with-the-ada-vs-code-extension/1426)

6. **Project-specific operator/delimiter spacing** ✓
   - **Status**: Matches our operator spacing findings
   - **Note**: GNATformat is "intentionally less configurable"

## Comparison Matrix

| Issue | Our Research | GPT-5 | Sources Match | Priority |
|-------|-------------|-------|---------------|----------|
| **Comment spacing after --** | ✓ | ✓ | Yes | High |
| **Operator spacing** | ✓ | ✓ | Yes | High |
| **String literal corruption** | ✓ | ✗ | N/A | Critical |
| **Vertical alignment** | ✗ | ✓ | N/A | High |
| **Casing dictionaries** | ✗ | ✓ | N/A | Medium |
| **Format guard regions** | ✗ | ✓ | N/A | Medium |
| **Preprocessing directives** | ✓ | ✗ | N/A | Critical |
| **Syntax error handling** | ✓ | ✗ | N/A | Critical |

## Key Insights

### GPT-5 Strengths:
- **Practical focus** on real-world team needs
- **Excellent source citations** with direct links
- **Experience-based** rather than theoretical
- **Covers workflow issues** (VS Code extension limitations)

### Our Research Strengths:
- **Discovered critical bugs** (string corruption)
- **Lower-level technical details** (preprocessing, syntax)
- **AdaCore documentation mining**
- **Empirical testing approach**

### Combined Coverage:
Together, we have identified **10+ distinct formatting holes** with both practical and technical perspectives.

## Updated Priority List

### Critical (Can break code)
1. **String literal corruption** - Our finding
2. **Preprocessing directive handling** - Our finding  
3. **Syntax error prevention** - Our finding

### High (Style violations, team workflow)
4. **Comment spacing normalization** - Both sources
5. **Operator spacing enforcement** - Both sources
6. **Vertical alignment** - GPT-5 finding
7. **Casing dictionary support** - GPT-5 finding

### Medium (Nice to have)
8. **Format guard regions** - GPT-5 finding
9. **Generic instantiation formatting** - Our finding
10. **Special comment forms** - Our finding

## Implementation Strategy

### Pre-ALS Phase
```
1. Syntax validation (prevent ALS crashes)
2. String literal safety (prevent corruption)  
3. Preprocessing detection (skip problematic files)
```

### Post-ALS Phase  
```
4. Comment spacing normalization
5. Operator spacing enforcement
6. Vertical alignment (optional)
7. Casing dictionary application
```

## GPT-5's Practical Checklist

GPT-5 provided an excellent starting checklist:

> * Normalize trailing comment spacing: ensure exactly one space before `--`, then two spaces after, for both whole-line and EOL comments
> * Optional: align `:`, `:=`, `=>`, and `--` to a chosen column within contiguous blocks
> * Enforce project-specific spacing around `..`, `=>`, and call parentheses
> * Apply casing exceptions (dictionary) for identifiers your team cares about

This aligns perfectly with our parser-based approach!

## Source Quality Assessment

GPT-5's sources are **excellent**:
- Direct links to official AdaCore documentation
- GCC/GNAT official guides
- Community forums with real user experiences
- GitHub repositories for tools

This validates our research direction and adds practical team-workflow perspectives.

## Next Steps

1. **Incorporate GPT-5 findings** into our matrix
2. **Test vertical alignment** - major gap in our analysis
3. **Research casing dictionaries** - important for enterprise teams
4. **Investigate format guard regions** - workflow critical
5. **Validate all sources** GPT-5 provided

## Conclusion

GPT-5's response complements our research perfectly:
- **Our focus**: Technical correctness, preventing corruption
- **GPT-5 focus**: Practical team workflow, style consistency

Together, we have a comprehensive view of ALS formatting limitations and can build a complete solution that addresses both critical bugs and practical workflow needs.

The combination of **empirical testing** (our approach) and **community experience** (GPT-5's sources) gives us high confidence in our formatting hole identification and prioritization.