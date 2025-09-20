# Parallel Processing in adafmt

## Why Parallel Workers with Default of 1?

You might notice that adafmt has a `--num-workers` flag but defaults to just 1 worker. This might seem contradictory - why build parallel processing infrastructure if we're not using it by default? Here's the story.

## Current Architecture

adafmt processes files in two main stages:
1. **ALS Formatting** - Using Ada Language Server to format code
2. **Post-Processing** - Applying custom patterns and writing files to disk

The parallel workers operate in the second stage only, processing files *after* ALS has formatted them.

## Why We Built It

We implemented parallel processing for several reasons:

1. **Future-Ready**: When ALS eventually supports parallel formatting, we'll be ready to scale immediately
2. **Pattern Processing**: Running without ALS (`--no-als`) shows 7% performance improvement with multiple workers
3. **Large Codebases**: Projects with thousands of files benefit from parallel I/O operations
4. **Clean Architecture**: The queue-based design provides better separation of concerns
5. **Minimal Overhead**: Our benchmarks show only 0.46% overhead - essentially free

## Why Default to 1 Worker?

Our comprehensive benchmarking revealed:

- **ALS is the bottleneck**: 95%+ of processing time is in ALS formatting (sequential)
- **No benefit for typical use**: With ALS enabled, multiple workers provide no speed improvement
- **Simpler behavior**: Single worker provides predictable, sequential-like output ordering
- **Resource efficiency**: No need to spawn threads that will mostly wait

## When to Use Multiple Workers

Consider increasing workers in these scenarios:

```bash
# Pattern-only processing (no ALS)
adafmt format --no-als --patterns-path patterns.json --num-workers 3

# Very large codebases with fast ALS
adafmt format --num-workers 4 --project-path huge_project.gpr

# Experimental: Multiple ALS instances (future)
# When ALS supports parallel operation
```

## Benchmark Results

Our benchmarks on a typical 303-file project showed:

| Configuration | Time | Notes |
|--------------|------|-------|
| Sequential (no workers) | 22.426s | Pure sequential baseline |
| 1 Worker | 22.529s | 0.46% overhead - negligible |
| 3 Workers + ALS | 22.655s | No improvement due to ALS bottleneck |
| 3 Workers (patterns only) | 3.363s | 7% faster than 1 worker |

## The Future

The parallel infrastructure positions adafmt for:

1. **Parallel ALS**: When available, we can immediately leverage multiple ALS instances
2. **Distributed Processing**: Foundation for multi-machine processing
3. **Advanced Patterns**: Complex pattern processors that benefit from parallelism
4. **Pipeline Extensions**: Additional processing stages can run in parallel

## Summary

We built parallel processing not for today's performance, but for tomorrow's possibilities. The minimal overhead (< 0.5%) means we get architectural flexibility essentially for free. When ALS evolves to support parallelism, adafmt will scale with it automatically.

For now, enjoy the simplicity of single-worker processing, knowing that power is there when you need it.