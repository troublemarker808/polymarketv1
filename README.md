# Polymarket Bot V3

Polymarket Bot V3 is the phase-1 foundation for a controlled automated trading system.

The current repository stage is `local_validation` moving toward `paper_canary`.

This codebase is being built toward:

- clear module boundaries
- replayable state
- paper evidence
- strict promotion gates

It is not live-ready and must not be presented as live-ready.

## Current Scope

This round focuses on:

- repository foundation
- config and runtime gates
- durable state model
- replayable ledger and read models
- runnable `local_validation`
- runnable fixture-driven `paper_canary`
- read-only-source `paper_canary` entrypoint
- promotion evidence and gate evaluation scaffolding

## Runtime Stages

- `architecture`
- `local_validation`
- `paper_canary`
- `small_live_validation`

## Runtime Modes

- `paper`
- `live_small`

`live_small` is structurally reserved but must stay disabled unless explicitly approved and fully gated.

## Development

```bash
uv sync --dev
uv run ruff check .
uv run mypy src tests
uv run pytest
```

## Current Commands

```bash
uv run python -m pm_bot.cli init-db
uv run python -m pm_bot.cli replay-fixture tests/fixtures/local_validation/sample_session.json
uv run python -m pm_bot.cli scan-gamma-fixture tests/fixtures/gamma_markets/sample_markets.json
uv run python -m pm_bot.cli paper-session-fixture tests/fixtures/paper_sessions/healthy_session.json
uv run python -m pm_bot.cli paper-canary-live-once
uv run python -m pm_bot.cli evaluate-paper-gate
uv run python -m pm_bot.cli serve-dashboard
```

These commands are safe for `local_validation` and `paper_canary`.
They do not place live orders and do not auto-load `.env`.

## Project Layout

```text
docs/          planning, requirements, harness rules
src/pm_bot/    application code
tests/         unit, integration, and architecture tests
artifacts/     replay, paper, incidents, and promotion evidence
```

## Safety Notes

- Do not auto-use `.env` during normal startup.
- Do not place secrets in fixtures, tests, or artifacts.
- Do not bypass reconcile, kill switch, or promotion gates.
