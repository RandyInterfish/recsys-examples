# Verification

Inputs: current flag, `RUN_CMD`, and `WARMUP=20`, `STEPS=30`,
`MIN_GAIN_PCT=1.0` unless overridden.

1. Set the current flag to `compare` and run `RUN_CMD`. Compare runs origin and
   optimize on equal input, weights, buffers, and RNG; it returns origin values
   to training. Record forward and VJP/gradient parity in `verification.json`.
   Restore the flag even if the run fails.
2. If the change batches, reorders, caches, or otherwise alters optimizer
   updates, run a warmed full-step origin/optimize check over relevant alias
   cases. Compare post-step parameters and optimizer state; record
   `real.update`.
3. Run profiler-off E2E once for each condition. Baseline is the accepted
   pre-Round flag map with the current flag `origin`; candidate changes only
   that flag to `optimize`. Each run starts from the same deterministic
   initialization and data position. Use identical hardware, process shape, and
   runtime settings; discard warmup and average `STEPS` steps. Set `valid=true`
   only when these conditions, the step window, and flag maps match; otherwise
   set it to `false`.
4. Compute `pct = (baseline_ms - candidate_ms) / baseline_ms * 100`. Set
   `meets_min_gain=true` when `pct >= MIN_GAIN_PCT`. Write it under `e2e` in
   `verification.json`.

`verification.json` contains measurements only. Its minimal format is in
[`record_schema.md`](record_schema.md). Never use profiled Nsys step time as
E2E evidence.
