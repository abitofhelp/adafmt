# ALS/GNATformat Formatting Holes Matrix

**Version:** 1.0.0  
**Date:** January 2025  
**License:** BSD-3-Clause  
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.  
**Authors:** Michael Gardner, A Bit of Help, Inc.  
**Status:** Research Document

This document catalogs known formatting limitations and "holes" in Ada Language Server (ALS) and GNATformat/gnatpp, and defines how adafmt addresses them with parser-based patterns.

## Validation Authority

**The gcc/gnat compiler is always right!** All fixes must pass GNAT compilation and style checking.

## Formatting Holes Matrix

| Hole/Issue | Category | ALS/GNATformat Behavior | GNAT Compiler Check | adafmt Fix | Phase |
|------------|----------|-------------------------|---------------------|------------|-------|
| **String Literal Corruption** | Critical | Breaks long strings incorrectly, corrupts content | Compilation error | Pre-ALS: Proper concatenation | Pre-ALS |
| **Operator Spacing in Declarations** | Medium | Often missed in complex declarations | Style warning with -gnaty | Post-ALS: Parser-based := spacing | Post-ALS |
| **Comment Spacing After --** | Low | Inconsistent spacing after -- | Style warning with -gnatyy | Post-ALS: Comment pattern | Post-ALS |
| **Range Operator Spacing** | Medium | Misses .. in complex expressions | Style warning with -gnaty | Post-ALS: Range pattern | Post-ALS |
| **Arrow Operator Spacing** | Medium | Inconsistent => spacing | Style warning with -gnaty | Post-ALS: Arrow pattern | Post-ALS |
| **Preprocessing Directives** | Critical | Cannot process sources with preprocessing | Compilation error | Pre-ALS: Skip or handle separately | Pre-ALS |
| **Line Length Violations** | Medium | May break strings incorrectly | Style warning with -gnatyM | Pre-ALS: Safe line breaking | Pre-ALS |
| **Syntax Error Handling** | Critical | Terminates with error, no output | Compilation error | Pre-ALS: Syntax validation | Pre-ALS |
| **Multiline Generic Instantiations** | Medium | Poor formatting of complex generics | Compiles but poor style | Post-ALS: Generic formatting | Post-ALS |
| **Special Comment Forms** | Low | Doesn't handle SPARK comments --# | Compiles, but tools confused | Post-ALS: Special comment handling | Post-ALS |

## Detailed Analysis

### 1. String Literal Corruption (CRITICAL)

**Problem:** ALS breaks long string literals across lines without proper Ada concatenation syntax.

```ada
-- Before ALS
Message : String := "This is a very long message that exceeds line limit";

-- After ALS (BROKEN!)
Message : String := "This is a very long message that exceeds line 
limit";

-- What adafmt does (Pre-ALS)
Message : String := 
   "This is a very long message that exceeds line " &
   "limit";
```

**GNAT Check:** `-gnatf` will report syntax error for broken strings  
**adafmt Solution:** Pre-ALS pattern breaks strings safely using concatenation

### 2. Operator Spacing in Declarations

**Problem:** ALS misses operator spacing in complex declarations.

```ada
-- Before
X:Integer:=42;
Y:array(1..10)of Integer:=(others=>0);

-- GNAT Style Check
gnatmake -gnaty file.adb  -- Reports style violations

-- adafmt Fix (Post-ALS)
X : Integer := 42;
Y : array (1 .. 10) of Integer := (others => 0);
```

**GNAT Check:** `-gnaty` reports spacing violations  
**adafmt Solution:** Post-ALS parser patterns for operator spacing

### 3. Comment Spacing

**Problem:** Inconsistent spacing after `--` in comments.

```ada
-- Before
--This comment needs space
X : Integer;  --This too

-- GNAT Style Check  
gnatmake -gnatyy file.adb  -- Reports comment style violations

-- adafmt Fix (Post-ALS)
-- This comment needs space
X : Integer;  -- This too
```

**GNAT Check:** `-gnatyy` checks comment formatting  
**adafmt Solution:** Post-ALS comment spacing patterns

### 4. Preprocessing Directives

**Problem:** GNATformat cannot process sources with preprocessing directives.

```ada
-- Before (causes ALS to fail)
#if DEBUG
   Put_Line("Debug mode");
#end if;

-- adafmt Solution
-- Pre-ALS: Detect and skip files with preprocessing
-- Or handle with special preprocessing-aware mode
```

**GNAT Check:** `-gnatep` processes correctly  
**adafmt Solution:** Pre-ALS detection and handling

## Classification Framework

### Pre-ALS Patterns (Prevent ALS Issues)
- **String literal safety** - Break long strings properly
- **Syntax validation** - Ensure code parses before ALS
- **Preprocessing detection** - Handle special cases
- **Line length management** - Prevent ALS corruption

### Post-ALS Patterns (Fix ALS Omissions)  
- **Operator spacing** - Fix `:=`, `=>`, `..`, etc.
- **Comment formatting** - Proper `--` spacing
- **Declaration spacing** - Complex declaration cleanup
- **Generic formatting** - Multiline generic cleanup

## Validation Workflow

```
1. Pre-ALS Patterns
   ↓
2. GNAT Syntax Check (gnatmake -gnats)
   ↓ 
3. ALS Formatting
   ↓
4. Post-ALS Patterns  
   ↓
5. GNAT Style Check (gnatmake -gnaty -gnatyM120)
   ↓
6. Final GNAT Compilation Check
```

Each step must pass before proceeding to the next.

## Research Sources

### AdaCore Documentation
- [GNAT User's Guide - gnatpp](https://docs.adacore.com/gnat_ugn-docs/html/gnat_ugn/gnat_ugn/gnat_utility_programs.html)
- [Ada Language Server GitHub](https://github.com/AdaCore/ada_language_server)
- [GNATformat Documentation](https://docs.adacore.com/live/wave/gnatformat/html/user-guide/user-guide/configuration.html)

### Known Issues Sources
- [libadalang-tools Issues](https://github.com/AdaCore/libadalang-tools/issues)
- [Ada Language Server Issues](https://github.com/AdaCore/ada_language_server/issues)
- Stack Overflow Ada formatting discussions

### Community Sources
- Ada Forum discussions on formatting tools
- AdaCore blog posts on formatting improvements

## Future Research

### Areas Needing Investigation
1. **Aspect clause formatting** - How does ALS handle aspects?
2. **Generic instantiation edge cases** - Complex generic formatting
3. **Pragma formatting** - Pragma alignment and spacing
4. **Access type formatting** - Complex access type declarations
5. **Task/protected type formatting** - Concurrent construct formatting

### Testing Matrix Expansion
For each identified hole:
1. Create minimal Ada test case
2. Test with current ALS/GNATformat
3. Test with GNAT compiler and style checking
4. Develop parser-based adafmt solution
5. Validate fix with GNAT

## Implementation Priority

### Phase 1 (Critical)
- [ ] String literal corruption protection
- [ ] Preprocessing directive detection  
- [ ] Syntax validation before ALS

### Phase 2 (High)
- [ ] Operator spacing patterns
- [ ] Range and arrow operator formatting
- [ ] Comment spacing patterns

### Phase 3 (Medium)  
- [ ] Generic instantiation formatting
- [ ] Complex declaration cleanup
- [ ] Special comment form handling

### Phase 4 (Low)
- [ ] Pragma formatting enhancement
- [ ] Aspect clause formatting
- [ ] Performance optimization

## Conclusion

This matrix provides a systematic approach to identifying, classifying, and addressing formatting limitations in ALS/GNATformat. By using parser-based patterns in a two-phase approach (pre-ALS and post-ALS), adafmt can provide comprehensive Ada code formatting that addresses the gaps in existing tools while maintaining compatibility with the Ada Language Server ecosystem.

The key insight is that **context awareness** through parsing is essential for safe, correct formatting of a complex language like Ada.