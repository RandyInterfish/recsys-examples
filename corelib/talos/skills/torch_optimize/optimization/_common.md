# Shared technique rules

Every change preserves numerical output and VJP/gradient contracts; changes to
optimizer updates also preserve post-step parameter/state contracts.

Use a persistent `origin | optimize | compare` flag. Keep origin intact.
Generate `compare` from
[`techniques/compare_branch.py.template`](techniques/compare_branch.py.template):
it runs equal-state branches, returns origin values to training, and records
parity only. Keep compare outside compiled regions. Specialize it, or record
`skipped`, for tied/transformed weights, identity-keyed optimizer state, or
global side effects.

Use the selected Technique's Local Check to iterate. Record its root-cause
signal in `worklog.md` and `report.md`; it does not replace verification.

Leave a cumulative `loop_<n>/loop.patch` and a re-runnable local accuracy
checker using representative input contracts.

Run [`verification/`](verification/verification.md): compare writes
parity and profiler-off E2E to `verification.json`. Correctness plus an E2E
gain meeting its threshold is the keep gate.

Report the root cause, change, Technique signal, parity, Round E2E, and
remaining same-cause work.
