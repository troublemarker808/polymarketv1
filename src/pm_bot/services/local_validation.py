import json
from datetime import datetime
from pathlib import Path
from typing import cast

from pm_bot.app_modes import RuntimeMode, ValidationStage
from pm_bot.config import AppConfig
from pm_bot.domain.enums import AggregateType, LedgerEventType
from pm_bot.domain.models import LedgerEntry
from pm_bot.services.artifacts import ensure_artifact_directories, write_json_artifact
from pm_bot.storage.db import connect_database, initialize_database, require_supported_versions
from pm_bot.storage.projector import LedgerProjector
from pm_bot.storage.repositories import LedgerRepository, ProjectionRepository


def replay_fixture(config: AppConfig, fixture_path: Path) -> Path:
    payload = json.loads(fixture_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        msg = "fixture must contain a JSON array of ledger entries"
        raise ValueError(msg)

    entries = [_ledger_entry_from_dict(item) for item in payload]

    ensure_artifact_directories(config.artifact_paths)
    connection = connect_database(config.database_path)
    initialize_database(connection)
    require_supported_versions(connection)

    ledger_repository = LedgerRepository(connection)
    projection_repository = ProjectionRepository(connection)
    projection_repository.clear()

    connection.execute("DELETE FROM ledger_entries")
    connection.commit()

    for entry in entries:
        ledger_repository.append(entry)

    projector = LedgerProjector(
        runtime_mode=RuntimeMode.PAPER,
        validation_stage=ValidationStage.LOCAL_VALIDATION,
        starting_bankroll=config.initial_bankroll,
        daily_loss_limit=config.daily_loss_notional,
    )
    positions, sessions, risks, snapshot = projector.project(ledger_repository.list_all())
    last_event_id = entries[-1].event_id if entries else "seed"
    projection_repository.replace_positions(positions, last_event_id=last_event_id)
    projection_repository.replace_session_states(sessions)
    projection_repository.replace_daily_risk_states(risks)
    projection_repository.replace_dashboard_snapshot(snapshot)

    return write_json_artifact(
        config.artifact_paths.replay,
        prefix="local-validation",
        payload={
            "fixture": str(fixture_path),
            "positions": positions,
            "sessions": sessions,
            "risks": risks,
            "snapshot": snapshot,
        },
    )


def _ledger_entry_from_dict(value: object) -> LedgerEntry:
    if not isinstance(value, dict):
        msg = "ledger entry fixture items must be objects"
        raise ValueError(msg)

    payload = value.get("payload", {})
    if not isinstance(payload, dict):
        msg = "ledger entry payload must be an object"
        raise ValueError(msg)

    return LedgerEntry(
        event_id=str(value["event_id"]),
        occurred_at=datetime.fromisoformat(cast(str, value["occurred_at"])),
        event_type=LedgerEventType(str(value["event_type"])),
        aggregate_type=AggregateType(str(value["aggregate_type"])),
        aggregate_id=str(value["aggregate_id"]),
        payload={str(key): item for key, item in payload.items()},
        schema_version=int(value["schema_version"]),
    )
