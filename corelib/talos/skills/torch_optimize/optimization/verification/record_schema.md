# Verification records

```json
{
  "real": {
    "skipped": "<reason; empty when verified>",
    "forward":    { "max_abs": 0.0, "max_rel": 0.0 },
    "vjp":        { "max_abs": 0.0, "max_rel": 0.0 },
    "update":     { "max_abs": 0.0, "max_rel": 0.0 }
  },
  "e2e": {
    "baseline": {
      "flags": {
        "prior_loops": { "<PRIOR_FLAG>": "optimize" },
        "prior_rounds": { "<KEPT_FLAG>": "optimize" },
        "current_round": { "<CURRENT_FLAG>": "origin" }
      },
      "avg_step_ms": 0.0
    },
    "candidate": {
      "flags": {
        "prior_loops": { "<PRIOR_FLAG>": "optimize" },
        "prior_rounds": { "<KEPT_FLAG>": "optimize" },
        "current_round": { "<CURRENT_FLAG>": "optimize" }
      },
      "avg_step_ms": 0.0
    },
    "warmup": 20,
    "steps": 30,
    "pct": 0.0,
    "min_gain_pct": 1.0,
    "meets_min_gain": false,
    "metric": "avg_step_ms",
    "valid": true
  }
}
```

`verification.json` stores parity and one profiler-off baseline/candidate
comparison. For backward-affecting patches, `real.vjp` stores gradient parity.
For patches that alter optimizer updates, `real.update` stores post-step
parameter/state parity; otherwise omit it.
`e2e.valid` requires matching conditions; `e2e.meets_min_gain` applies the
gain threshold. It contains measurements, not a verdict.
