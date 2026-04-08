import pytest

from pm_bot.app_modes import RuntimeMode, ValidationStage
from pm_bot.config import AppConfig


def test_default_config_stays_in_pre_live_mode() -> None:
    config = AppConfig.from_mapping({})

    assert config.validation_stage is ValidationStage.ARCHITECTURE
    assert config.runtime_mode is RuntimeMode.PAPER
    assert config.artifact_paths.replay.name == "replay"


def test_live_small_requires_explicit_enable_and_credentials() -> None:
    with pytest.raises(ValueError, match="disabled"):
        AppConfig.from_mapping({"runtime_mode": RuntimeMode.LIVE_SMALL})

    with pytest.raises(ValueError, match="missing required environment variables"):
        AppConfig.from_mapping(
            {
                "runtime_mode": RuntimeMode.LIVE_SMALL,
                "enable_live_small": True,
            }
        )


def test_live_small_accepts_complete_guarded_profile() -> None:
    config = AppConfig.from_mapping(
        {
            "runtime_mode": RuntimeMode.LIVE_SMALL,
            "enable_live_small": True,
            "polymarket_private_key": "masked",
            "polymarket_api_key": "masked",
            "polymarket_api_secret": "masked",
            "polymarket_api_passphrase": "masked",
            "polymarket_funder": "masked",
        }
    )

    assert config.runtime_mode is RuntimeMode.LIVE_SMALL
