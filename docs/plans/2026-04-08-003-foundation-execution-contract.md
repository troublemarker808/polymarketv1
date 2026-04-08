---
date: 2026-04-08
sequence: 003
type: plan
title: "Foundation Execution Contract"
status: active
origin: docs/plans/2026-04-07-001-feat-polymarket-phase1-validation-bot-plan.md
---

# Foundation Execution Contract

## Purpose

This document freezes the execution contract for the first implementation slice of Polymarket V3.

It exists to keep the current round narrow, testable, and aligned with the repository's harness rules.

## Current Stage

- Stage name: `architecture`
- Target exit for this round:
  - foundation structure exists
  - module boundaries are explicit
  - `local_validation` has a usable fixture-driven base
  - `paper_canary` has artifact and gate scaffolding
  - `small_live_validation` remains disabled but structurally prepared

## This Round Scope

### In scope

- Repository engineering baseline
- Config contract and runtime mode gates
- Domain state model
- Durable storage schema
- Ledger replay and read-model rebuild
- Artifact directory and file contract for replay / paper evidence
- Local fixture-driven validation entrypoints

### Out of scope

- Real wallet usage
- Real order submission
- Real signing
- `small_live_validation` execution
- Multi-strategy support
- Multi-page dashboard
- Complex UI work

## Document Alignment Notes

### Resolved interpretation

- The requirements document says phase-1 candidate discovery starts from Polymarket itself.
- The phase-1 plan later freezes edge validation around external reference probability.

Current implementation interpretation:

- Polymarket price and market metadata are allowed to drive candidate discovery.
- Tradeability and edge validation must later be decided by reference probability.
- Until that reference path exists, any future candidate should be able to degrade to `observe_only`.

This keeps both documents aligned without pretending the reference-probability path already exists.

### Gaps frozen by this contract

- Artifact file layout is required by the harness document, but exact file names and schemas were not frozen.
- This round will create a minimal artifact contract under `artifacts/` so later replay and paper outputs are stable and reviewable.

- The harness document requires stage gates, while the phase-1 plan defines them at a higher level.
- This round will encode stage and runtime enums plus config validation, but will not claim that promotion logic is complete.

## Hard Prohibitions

- Do not read or use live credentials unless explicitly required for a later approved task.
- Do not auto-load `.env` as part of normal runtime startup.
- Do not allow `live_small` to start without explicit opt-in and full required credentials.
- Do not treat config-only protections as effective until they are part of the execution path.

## Acceptance Criteria For This Slice

1. The repository can run lint, type-check, and tests from a single Python project baseline.
2. Runtime config clearly separates `paper` from `live_small`.
3. Storage can rebuild state and dashboard snapshot from append-only ledger events.
4. Replay and paper artifact directories exist with a stable write contract.
5. Tests demonstrate:
   - dependency boundaries
   - live gating
   - replay rebuild
   - snapshot version checks

## Next Planned Slice

After this foundation slice is complete, the next priority remains:

1. Market discovery and selector
2. Probe / confirmation / session-stop logic
3. Risk / execution / reconcile
4. Dashboard on top of trusted read models
