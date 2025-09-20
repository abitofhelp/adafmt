# Terminal Colors Guide

**Version:** 1.0.0
**Date:** January 2025
**License:** BSD-3-Clause
**Copyright:** © 2025 Michael Gardner, A Bit of Help, Inc.
**Authors:** Michael Gardner, A Bit of Help, Inc.
**Status:** Released

This guide provides recommended terminal color settings for optimal display of adafmt output.

## Overview

adafmt uses ANSI color codes to provide visual feedback during formatting operations. The colors are designed to create a clear visual hierarchy:

- **Failed operations** - Bright red (ANSI 91) to grab immediate attention
- **Normal operations** - Light gray (256-color ANSI 253) for readability without distraction

## Color Usage in adafmt

adafmt uses the following colors:

| Status | Icon | ANSI Code | Description |
|--------|------|-----------|-------------|
| failed | ✗ | 91 (bright red) | Errors that require attention |
| found | ✓ | 253 (light gray) | Files discovered for processing |
| formatted | ~ | 253 (light gray) | Files processed by ALS |
| amended | Δ | 253 (light gray) | Files modified by patterns |
| unchanged | = | 253 (light gray) | Files with no changes |

## Recommended Terminal Colors

For the best visual experience, we recommend terminal colors similar to these:

### Background
- **Color:** Pure black
- **RGB:** (0, 0, 0)
- **Hex:** #000000

### Normal ANSI Colors (0-7)
| Color | ANSI # | RGB | Hex |
|-------|--------|-----|-----|
| Black | 0 | (0,0,0) | #000000 |
| Red | 1 | (153,0,0) | #990000 |
| Green | 2 | (0,166,0) | #00A600 |
| Yellow | 3 | (153,153,0) | #999900 |
| Blue | 4 | (0,0,178) | #0000B2 |
| Magenta | 5 | (178,0,178) | #B200B2 |
| Cyan | 6 | (0,166,178) | #00A6B2 |
| White | 7 | (191,191,191) | #BFBFBF |

### Bright ANSI Colors (8-15)
| Color | ANSI # | RGB | Hex |
|-------|--------|-----|-----|
| Bright Black | 8 | (102,102,102) | #666666 |
| Bright Red | 9 | (255,0,0) | #FF0000 |
| Bright Green | 10 | (0,255,0) | #00FF00 |
| Bright Yellow | 11 | (255,255,0) | #FFFF00 |
| Bright Blue | 12 | (0,0,255) | #0000FF |
| Bright Magenta | 13 | (230,0,230) | #E600E6 |
| Bright Cyan | 14 | (0,230,230) | #00E6E6 |
| Bright White | 15 | (255,255,255) | #FFFFFF |

### Important Note on Bright Black

Some terminals map "bright black" (ANSI 8) to colors that are too dark or too bright. If your terminal shows bright black as:
- Too dark (like RGB 34,32,36): The text will be nearly invisible
- Too bright (like bright blue): The text will be distracting

In these cases, adafmt uses 256-color mode (ANSI 253) which renders consistently across terminals.

## Terminal Compatibility

adafmt's color output has been tested with:
- macOS Terminal.app
- iTerm2
- GNOME Terminal
- Windows Terminal
- VS Code integrated terminal

Most modern terminals support 256-color mode, ensuring consistent appearance regardless of the basic 16-color palette configuration.

## Customizing Colors

If you prefer different colors, you can:

1. Adjust your terminal's ANSI color palette
2. Set the `NO_COLOR` environment variable to disable all colors
3. Redirect output to a file (colors are automatically disabled for non-TTY output)

## Troubleshooting

If colors appear incorrect:

1. **Check terminal color support:**
   ```bash
   echo $TERM
   ```
   Should show something like `xterm-256color`

2. **Test 256-color support:**
   ```bash
   for i in {0..255}; do printf "\e[38;5;${i}mcolor${i}\e[0m "; done
   ```

3. **Test specific colors used by adafmt:**
   ```bash
   echo -e "\e[91mBright Red (failed status)\e[0m"
   echo -e "\e[38;5;253mLight Gray (normal status)\e[0m"
   ```

## See Also

- [Getting Started Guide](getting-started-guide.md)
- [Command Line Guide](command-line-guide.md)
- [Output Format Guide](output-format-guide.md)