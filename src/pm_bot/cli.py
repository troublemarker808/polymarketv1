from pathlib import Path

import typer
import uvicorn

from pm_bot.config import for_paper_canary_runtime, load_config
from pm_bot.integrations.polymarket.gamma_client import GammaClient
from pm_bot.services.local_validation import replay_fixture
from pm_bot.services.market_scan_service import MarketScanService
from pm_bot.services.paper_canary import PaperCanaryService
from pm_bot.services.promotion_gate import evaluate_paper_gate
from pm_bot.services.trading_loop import PaperTradingLoop
from pm_bot.storage.db import connect_database, initialize_database, require_supported_versions
from pm_bot.web.app import create_app

app = typer.Typer(add_completion=False)


@app.command("init-db")
def init_db() -> None:
    """Create the local SQLite database and install the current schema."""
    config = load_config()
    connection = connect_database(config.database_path)
    initialize_database(connection)
    require_supported_versions(connection)
    typer.echo(f"Database ready at {config.database_path}")


@app.command("replay-fixture")
def replay_fixture_command(path: Path) -> None:
    """Run fixture-driven local validation and write a replay artifact."""
    config = load_config()
    artifact_path = replay_fixture(config, path)
    typer.echo(f"Replay artifact written to {artifact_path}")


@app.command("scan-gamma-fixture")
def scan_gamma_fixture(path: Path) -> None:
    """Run the candidate selector against a Gamma fixture and write a paper artifact."""
    config = load_config()
    service = MarketScanService(config, GammaClient(config.polymarket_gamma_url))
    selected, artifact_path = service.scan_fixture(path)
    typer.echo(f"Selected {len(selected)} candidates")
    typer.echo(f"Paper artifact written to {artifact_path}")


@app.command("paper-session-fixture")
def paper_session_fixture(path: Path) -> None:
    """Run a fixture-driven paper session and emit evidence artifacts."""
    config = load_config()
    result = PaperTradingLoop(config).run_fixture(path)
    typer.echo(f"Processed {result.processed_snapshots} snapshots")
    typer.echo(f"Stopped for day: {result.stopped_for_day}")
    typer.echo(f"Session summary: {result.session_summary_path}")
    typer.echo(f"Probe log: {result.probe_log_path}")
    if result.incident_note_path is not None:
        typer.echo(f"Incident note: {result.incident_note_path}")


@app.command("paper-canary-live-once")
def paper_canary_live_once() -> None:
    """Run a single read-only live market scan through the paper canary loop."""
    config = for_paper_canary_runtime(load_config())
    result = PaperCanaryService(config).run_live_once()
    typer.echo(f"Processed {result.processed_snapshots} snapshots")
    typer.echo(f"Stopped for day: {result.stopped_for_day}")
    typer.echo(f"Session summary: {result.session_summary_path}")
    typer.echo(f"Probe log: {result.probe_log_path}")
    if result.incident_note_path is not None:
        typer.echo(f"Incident note: {result.incident_note_path}")


@app.command("evaluate-paper-gate")
def evaluate_paper_gate_command() -> None:
    """Evaluate whether paper evidence is sufficient to consider promotion review."""
    config = for_paper_canary_runtime(load_config())
    decision = evaluate_paper_gate(config)
    typer.echo(
        "Ready for small_live_validation: "
        f"{decision.ready_for_small_live_validation}"
    )
    typer.echo(
        "Engineering blockers: "
        f"{', '.join(decision.engineering_blockers) if decision.engineering_blockers else 'none'}"
    )
    typer.echo(
        "Evidence gaps: "
        f"{', '.join(decision.evidence_gaps) if decision.evidence_gaps else 'none'}"
    )
    typer.echo(f"Reasons: {', '.join(decision.reasons) if decision.reasons else 'none'}")
    typer.echo(f"Promotion artifact: {decision.artifact_path}")


@app.command("serve-dashboard")
def serve_dashboard(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Serve the operator dashboard from trusted read models."""
    config = for_paper_canary_runtime(load_config())
    uvicorn.run(create_app(config), host=host, port=port)


if __name__ == "__main__":
    app()
