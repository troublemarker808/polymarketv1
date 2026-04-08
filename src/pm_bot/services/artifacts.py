import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pm_bot.config import ArtifactPaths


def ensure_artifact_directories(paths: ArtifactPaths) -> None:
    for path in (paths.replay, paths.paper, paths.incidents, paths.promotion):
        path.mkdir(parents=True, exist_ok=True)


def write_json_artifact(base_dir: Path, *, prefix: str, payload: dict[str, Any]) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    target = base_dir / f"{prefix}-{timestamp}.json"
    serializable_payload = _to_serializable(payload)
    target.write_text(json.dumps(serializable_payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def _to_serializable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _to_serializable(asdict(value))
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _to_serializable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_serializable(item) for item in value]
    return value
