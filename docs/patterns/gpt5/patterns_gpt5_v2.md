I incorporated Claude’s five safeguards and tightened the docs. Highlights:
Regex timeout protection (ReDoS) is now mandatory with a new --pattern-timeout-ms (default 50 ms) and a pattern_timeout event.
Pat Log filename typo fixed to adafmt_<timestamp>_patterns.log everywhere (footer + TTY + logging).
Python 3.8-compatible typing called out in SDD (use Dict, List, Tuple).
Stronger pattern validation at load (schema + compile), invalid rules skipped with warnings.
File size cap for the pattern step (default 10 MiB), with --patterns-max-bytes and a file_skipped_large event.
Reaffirmed error isolation so pattern issues never break the formatting pipeline.

If anything in Claude’s list needs a different default (e.g., timeout ms or size cap), I can tweak and regenerate instantly.
