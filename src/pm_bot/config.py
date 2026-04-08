from collections.abc import Mapping
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pm_bot.app_modes import RuntimeMode, ValidationStage


class ArtifactPaths(BaseModel):
    replay: Path
    paper: Path
    incidents: Path
    promotion: Path


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PM_",
        extra="ignore",
        validate_default=True,
    )

    validation_stage: ValidationStage = ValidationStage.ARCHITECTURE
    runtime_mode: RuntimeMode = RuntimeMode.PAPER

    database_path: Path = Path("var/pm_bot.sqlite3")
    artifact_root: Path = Path("artifacts")

    initial_bankroll: float = Field(default=1000.0, gt=0)
    probe_max_fraction: float = Field(default=0.005, gt=0, le=1)
    probe_max_notional: float = Field(default=20.0, gt=0)
    market_max_fraction: float = Field(default=0.015, gt=0, le=1)
    market_max_notional: float = Field(default=60.0, gt=0)
    daily_loss_fraction: float = Field(default=0.02, gt=0, le=1)
    daily_loss_notional: float = Field(default=75.0, gt=0)
    candidate_window_hours: int = Field(default=72, gt=0)
    gamma_scan_limit: int = Field(default=200, gt=0)
    probe_confirmation_window_hours: int = Field(default=4, gt=0)
    min_hours_before_resolution_for_probe: int = Field(default=8, gt=0)
    event_match_window_minutes: int = Field(default=90, gt=0)
    reference_max_staleness_minutes: int = Field(default=20, gt=0)
    minimum_reference_bookmakers: int = Field(default=3, gt=0)
    probe_edge_threshold: float = Field(default=0.04, ge=0, le=1)
    confirm_edge_threshold: float = Field(default=0.05, ge=0, le=1)
    add_stage_2_edge_threshold: float = Field(default=0.06, ge=0, le=1)
    exit_edge_threshold: float = Field(default=0.01, ge=0, le=1)
    promotion_min_paper_sessions: int = Field(default=10, gt=0)
    promotion_min_resolved_probes: int = Field(default=6, gt=0)

    polymarket_gamma_url: str = "https://gamma-api.polymarket.com"
    polymarket_clob_url: str = "https://clob.polymarket.com"
    reference_odds_url: str = "https://api.the-odds-api.com/v4"
    reference_odds_api_key: str | None = None

    enable_live_small: bool = False
    polymarket_private_key: str | None = None
    polymarket_api_key: str | None = None
    polymarket_api_secret: str | None = None
    polymarket_api_passphrase: str | None = None
    polymarket_funder: str | None = None

    @model_validator(mode="after")
    def validate_runtime_guards(self) -> Self:
        if self.market_max_notional < self.probe_max_notional:
            msg = "market_max_notional must be greater than or equal to probe_max_notional"
            raise ValueError(msg)

        if self.daily_loss_notional < self.probe_max_notional:
            msg = "daily_loss_notional must be greater than or equal to probe_max_notional"
            raise ValueError(msg)

        if self.runtime_mode is RuntimeMode.LIVE_SMALL:
            if not self.enable_live_small:
                msg = "live_small is disabled unless PM_ENABLE_LIVE_SMALL=true"
                raise ValueError(msg)

            required = {
                "PM_POLYMARKET_PRIVATE_KEY": self.polymarket_private_key,
                "PM_POLYMARKET_API_KEY": self.polymarket_api_key,
                "PM_POLYMARKET_API_SECRET": self.polymarket_api_secret,
                "PM_POLYMARKET_API_PASSPHRASE": self.polymarket_api_passphrase,
                "PM_POLYMARKET_FUNDER": self.polymarket_funder,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                msg = f"live_small missing required environment variables: {', '.join(missing)}"
                raise ValueError(msg)

        return self

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "AppConfig":
        return cls.model_validate(dict(values))

    @property
    def artifact_paths(self) -> ArtifactPaths:
        root = self.artifact_root
        return ArtifactPaths(
            replay=root / "replay",
            paper=root / "paper",
            incidents=root / "incidents",
            promotion=root / "promotion",
        )


def load_config() -> AppConfig:
    return AppConfig()


def for_paper_canary_runtime(config: AppConfig) -> AppConfig:
    database_path = config.database_path
    if database_path == Path("var/pm_bot.sqlite3"):
        database_path = Path("var/paper_canary.sqlite3")
    return config.model_copy(
        update={
            "validation_stage": ValidationStage.PAPER_CANARY,
            "runtime_mode": RuntimeMode.PAPER,
            "database_path": database_path,
        }
    )
