import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pm_bot.app_modes import RuntimeMode, ValidationStage
from pm_bot.config import AppConfig
from pm_bot.domain.enums import PositionLifecycleState, SessionStatus
from pm_bot.domain.events import SessionOpenedEvent, SessionStoppedEvent, to_ledger_entry
from pm_bot.domain.models import DailyRiskState, LedgerEntry, MarketCandidate, SessionState
from pm_bot.execution.order_router import PaperOrderRouter
from pm_bot.execution.position_service import PaperPosition, rebuild_open_positions
from pm_bot.execution.reconciler import PaperReconciler
from pm_bot.integrations.polymarket.gamma_client import parse_gamma_market
from pm_bot.integrations.polymarket.translators import flatten_candidates
from pm_bot.integrations.reference_odds.models import ReferenceOddsEventDTO
from pm_bot.integrations.reference_odds.translators import parse_reference_event
from pm_bot.risk.kill_switch import KillSwitchState
from pm_bot.risk.limits import RiskLimits
from pm_bot.services.artifacts import ensure_artifact_directories, write_json_artifact
from pm_bot.storage.db import connect_database, initialize_database, require_supported_versions
from pm_bot.storage.projector import LedgerProjector
from pm_bot.storage.repositories import LedgerRepository, ProjectionRepository
from pm_bot.storage.schema import SCHEMA_VERSION
from pm_bot.strategy.confirmation_engine import ConfirmationEngine
from pm_bot.strategy.event_identity_resolver import EventIdentityResolver
from pm_bot.strategy.market_selector import MarketSelector
from pm_bot.strategy.probe_policy import ProbePolicy
from pm_bot.strategy.reference_probability import (
    EstimatedWinProbability,
    ReferenceProbabilityAdapter,
)
from pm_bot.strategy.session_guard import SessionGuard


@dataclass(frozen=True, slots=True)
class PaperSessionResult:
    session_summary_path: Path
    probe_log_path: Path
    stop_reason_path: Path
    weekly_snapshot_path: Path
    incident_note_path: Path | None
    processed_snapshots: int
    stopped_for_day: bool


class PaperTradingLoop:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._selector = MarketSelector(candidate_window_hours=config.candidate_window_hours)
        self._resolver = EventIdentityResolver(
            match_window_minutes=config.event_match_window_minutes
        )
        self._reference_adapter = ReferenceProbabilityAdapter(
            max_staleness_minutes=config.reference_max_staleness_minutes,
            minimum_bookmakers=config.minimum_reference_bookmakers,
        )
        probe_notional = min(
            config.initial_bankroll * config.probe_max_fraction,
            config.probe_max_notional,
        )
        market_max_notional = min(
            config.initial_bankroll * config.market_max_fraction,
            config.market_max_notional,
        )
        daily_loss_limit = min(
            config.initial_bankroll * config.daily_loss_fraction,
            config.daily_loss_notional,
        )
        self._probe_notional = probe_notional
        self._risk_limits = RiskLimits(
            probe_notional=probe_notional,
            market_max_notional=market_max_notional,
            daily_loss_limit=daily_loss_limit,
        )
        self._probe_policy = ProbePolicy(
            probe_edge_threshold=config.probe_edge_threshold,
            confirm_window_hours=config.probe_confirmation_window_hours,
            min_hours_before_resolution=config.min_hours_before_resolution_for_probe,
            probe_notional=probe_notional,
            daily_loss_limit=daily_loss_limit,
            market_max_notional=market_max_notional,
        )
        self._confirmation_engine = ConfirmationEngine(
            confirm_edge_threshold=config.confirm_edge_threshold,
            add_stage_2_edge_threshold=config.add_stage_2_edge_threshold,
            exit_edge_threshold=config.exit_edge_threshold,
            min_hours_before_resolution=config.min_hours_before_resolution_for_probe,
            confirmation_window_hours=config.probe_confirmation_window_hours,
        )
        self._session_guard = SessionGuard()
        self._router = PaperOrderRouter()
        self._reconciler = PaperReconciler()

    def run_fixture(self, fixture_path: Path) -> PaperSessionResult:
        fixture = json.loads(fixture_path.read_text(encoding="utf-8-sig"))
        return self._run_fixture_payload(fixture, evidence_source="fixture_paper")

    def run_snapshot_payload(
        self,
        *,
        timestamp: datetime,
        gamma_markets: list[object],
        reference_events: list[object],
        evidence_source: str = "read_only_live_paper",
    ) -> PaperSessionResult:
        return self._run_fixture_payload(
            {
                "snapshots": [
                    {
                        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
                        "gamma_markets": gamma_markets,
                        "reference_events": reference_events,
                    }
                ]
            },
            evidence_source=evidence_source,
        )

    def _run_fixture_payload(
        self,
        fixture: object,
        *,
        evidence_source: str,
    ) -> PaperSessionResult:
        if not isinstance(fixture, dict) or not isinstance(fixture.get("snapshots"), list):
            msg = "paper session fixture must contain a snapshots list"
            raise ValueError(msg)

        snapshots = fixture["snapshots"]
        if not snapshots:
            msg = "paper session fixture cannot be empty"
            raise ValueError(msg)

        session_date = _parse_timestamp(snapshots[0]["timestamp"]).date()
        ensure_artifact_directories(self._config.artifact_paths)

        connection = connect_database(self._config.database_path)
        initialize_database(connection)
        require_supported_versions(connection)
        ledger_repository = LedgerRepository(connection)
        projection_repository = ProjectionRepository(connection)
        existing_entries = ledger_repository.list_all()
        recovered_positions = rebuild_open_positions(existing_entries)

        existing_session = projection_repository.fetch_session_state(session_date)
        if existing_session is not None:
            session_state = existing_session
            session_open_event: LedgerEntry | None = None
        else:
            previous_session = projection_repository.fetch_session_state(
                session_date - timedelta(days=1)
            )
            session_status = (
                SessionStatus.CAUTIOUS_START
                if previous_session is not None
                and previous_session.status is SessionStatus.STOPPED_FOR_DAY
                else SessionStatus.RUNNING
            )
            session_state = SessionState(
                session_date=session_date,
                status=session_status,
                stop_reason=None,
                cautious_until_probe_confirmed=session_status is SessionStatus.CAUTIOUS_START,
                consecutive_probe_failures=0,
                last_reconcile_at=None,
                last_stop_at=None,
                updated_at=_parse_timestamp(snapshots[0]["timestamp"]),
            )
            session_open_event = to_ledger_entry(
                SessionOpenedEvent(
                    session_date=session_date,
                    status=session_status,
                    updated_at=_parse_timestamp(snapshots[0]["timestamp"]),
                ),
                schema_version=SCHEMA_VERSION,
            )

        daily_risk_state = projection_repository.fetch_daily_risk_state(
            session_date
        ) or DailyRiskState(
            session_date=session_date,
            realized_loss=0.0,
            open_risk=sum(position.notional for position in recovered_positions.values()),
            daily_loss_limit=self._risk_limits.daily_loss_limit,
            kill_switch_engaged=False,
            updated_at=_parse_timestamp(snapshots[0]["timestamp"]),
        )

        events: list[LedgerEntry] = []
        if session_open_event is not None:
            events.append(session_open_event)
        paper_positions: dict[str, PaperPosition] = dict(recovered_positions)
        probe_logs: list[dict[str, object]] = []
        kill_switch = KillSwitchState(engaged=daily_risk_state.kill_switch_engaged)

        for raw_snapshot in snapshots:
            snapshot = _parse_snapshot(raw_snapshot)
            reconcile_result, reconcile_event = self._reconciler.reconcile(
                session_date=session_date,
                observed_open_positions=len(paper_positions),
                recorded_open_positions=len(paper_positions),
                recorded_at=snapshot.timestamp,
            )
            events.append(to_ledger_entry(reconcile_event, schema_version=SCHEMA_VERSION))
            session_state = SessionState(
                session_date=session_state.session_date,
                status=session_state.status,
                stop_reason=session_state.stop_reason,
                cautious_until_probe_confirmed=session_state.cautious_until_probe_confirmed,
                consecutive_probe_failures=session_state.consecutive_probe_failures,
                last_reconcile_at=snapshot.timestamp,
                last_stop_at=session_state.last_stop_at,
                updated_at=snapshot.timestamp,
            )

            candidates = self._selector.select(
                flatten_candidates([parse_gamma_market(item) for item in snapshot.gamma_markets]),
                as_of=snapshot.timestamp,
            )
            reference_events = [parse_reference_event(item) for item in snapshot.reference_events]

            for candidate in candidates:
                position = next(
                    (
                        item
                        for item in paper_positions.values()
                        if item.market_id == candidate.market_id
                        and item.outcome_label == candidate.outcome_label
                    ),
                    None,
                )
                estimate = self._estimate(candidate, reference_events, snapshot.timestamp)
                if position is None:
                    risk_decision = self._risk_limits.allow_probe(
                        daily_risk_state=daily_risk_state,
                        current_market_exposure=self._current_market_exposure(
                            paper_positions,
                            market_id=candidate.market_id,
                        ),
                        kill_switch=kill_switch,
                    )
                    if not risk_decision.allowed:
                        probe_logs.append(
                            {
                                "market_id": candidate.market_id,
                                "outcome_label": candidate.outcome_label,
                                "timestamp": snapshot.timestamp,
                                "result": "observe",
                                "reason": risk_decision.reason,
                            }
                        )
                        continue
                    probe_decision = self._probe_policy.decide(
                        candidate,
                        estimate,
                        session_state=session_state,
                        daily_risk_state=daily_risk_state,
                        current_market_exposure=self._current_market_exposure(
                            paper_positions,
                            market_id=candidate.market_id,
                        ),
                        as_of=snapshot.timestamp,
                    )
                    if probe_decision.action != "probe":
                        probe_logs.append(
                            {
                                "market_id": candidate.market_id,
                                "outcome_label": candidate.outcome_label,
                                "timestamp": snapshot.timestamp,
                                "result": "observe",
                                "reason": probe_decision.reason,
                            }
                        )
                        continue

                    position, probe_event = self._router.open_probe(
                        market_id=candidate.market_id,
                        market_title=candidate.market_title,
                        outcome_label=candidate.outcome_label,
                        price=candidate.market_implied_probability,
                        notional=probe_decision.probe_notional,
                        opened_at=snapshot.timestamp,
                        confirmation_deadline=snapshot.timestamp
                        + self._probe_policy.confirmation_window,
                        reference_event_id=estimate.reference_event_id,
                    )
                    paper_positions[position.position_id] = position
                    daily_risk_state = DailyRiskState(
                        session_date=daily_risk_state.session_date,
                        realized_loss=daily_risk_state.realized_loss,
                        open_risk=daily_risk_state.open_risk + position.notional,
                        daily_loss_limit=daily_risk_state.daily_loss_limit,
                        kill_switch_engaged=daily_risk_state.kill_switch_engaged,
                        updated_at=snapshot.timestamp,
                    )
                    events.append(to_ledger_entry(probe_event, schema_version=SCHEMA_VERSION))
                    probe_logs.append(
                        {
                            "position_id": position.position_id,
                            "market_id": candidate.market_id,
                            "outcome_label": candidate.outcome_label,
                            "timestamp": snapshot.timestamp,
                            "result": "probe_opened",
                            "reason": probe_decision.reason,
                            "edge": estimate.edge,
                        }
                    )
                    continue

                decision = self._confirmation_engine.decide(
                    state=position.state,
                    candidate=candidate,
                    estimate=estimate,
                    opened_at=position.opened_at,
                    as_of=snapshot.timestamp,
                )
                if decision.action == "hold":
                    valuation_event = self._router.value_position(
                        position,
                        price=candidate.market_implied_probability,
                        valued_at=snapshot.timestamp,
                    )
                    events.append(to_ledger_entry(valuation_event, schema_version=SCHEMA_VERSION))
                    continue

                if decision.action == "confirm_stage_1":
                    updated_position, confirm_event, valuation_event = self._router.confirm_stage(
                        position,
                        additional_notional=self._probe_notional,
                        price=candidate.market_implied_probability,
                        target_state=PositionLifecycleState.CONFIRMED_STAGE_1,
                        confirmed_at=snapshot.timestamp,
                    )
                    paper_positions[position.position_id] = updated_position
                    session_state = self._session_guard.record_probe_confirmation(
                        session_state,
                        at=snapshot.timestamp,
                    )
                    daily_risk_state = DailyRiskState(
                        session_date=daily_risk_state.session_date,
                        realized_loss=daily_risk_state.realized_loss,
                        open_risk=daily_risk_state.open_risk + self._probe_notional,
                        daily_loss_limit=daily_risk_state.daily_loss_limit,
                        kill_switch_engaged=daily_risk_state.kill_switch_engaged,
                        updated_at=snapshot.timestamp,
                    )
                    events.extend(
                        [
                            to_ledger_entry(confirm_event, schema_version=SCHEMA_VERSION),
                            to_ledger_entry(valuation_event, schema_version=SCHEMA_VERSION),
                        ]
                    )
                    probe_logs.append(
                        {
                            "position_id": position.position_id,
                            "market_id": candidate.market_id,
                            "timestamp": snapshot.timestamp,
                            "result": "probe_confirmed",
                            "reason": decision.reason,
                            "edge": estimate.edge,
                        }
                    )
                    continue

                if decision.action == "add_stage_2":
                    updated_position, confirm_event, valuation_event = self._router.confirm_stage(
                        position,
                        additional_notional=self._probe_notional,
                        price=candidate.market_implied_probability,
                        target_state=PositionLifecycleState.CONFIRMED_STAGE_2,
                        confirmed_at=snapshot.timestamp,
                    )
                    paper_positions[position.position_id] = updated_position
                    daily_risk_state = DailyRiskState(
                        session_date=daily_risk_state.session_date,
                        realized_loss=daily_risk_state.realized_loss,
                        open_risk=daily_risk_state.open_risk + self._probe_notional,
                        daily_loss_limit=daily_risk_state.daily_loss_limit,
                        kill_switch_engaged=daily_risk_state.kill_switch_engaged,
                        updated_at=snapshot.timestamp,
                    )
                    events.extend(
                        [
                            to_ledger_entry(confirm_event, schema_version=SCHEMA_VERSION),
                            to_ledger_entry(valuation_event, schema_version=SCHEMA_VERSION),
                        ]
                    )
                    probe_logs.append(
                        {
                            "position_id": position.position_id,
                            "market_id": candidate.market_id,
                            "timestamp": snapshot.timestamp,
                            "result": "add_stage_2",
                            "reason": decision.reason,
                            "edge": estimate.edge,
                        }
                    )
                    continue

                close_event = self._router.close_position(
                    position,
                    price=candidate.market_implied_probability,
                    reason="unconfirmed"
                    if position.state is PositionLifecycleState.PROBE_LIVE
                    else decision.reason,
                    closed_at=snapshot.timestamp,
                )
                events.append(to_ledger_entry(close_event, schema_version=SCHEMA_VERSION))
                probe_logs.append(
                    {
                        "position_id": position.position_id,
                        "market_id": candidate.market_id,
                        "timestamp": snapshot.timestamp,
                        "result": "position_closed",
                        "reason": close_event.close_reason,
                        "realized_pnl": close_event.realized_pnl,
                    }
                )
                paper_positions.pop(position.position_id, None)
                daily_risk_state = DailyRiskState(
                    session_date=daily_risk_state.session_date,
                    realized_loss=(
                        daily_risk_state.realized_loss
                        + max(-close_event.realized_pnl, 0.0)
                    ),
                    open_risk=max(daily_risk_state.open_risk - position.notional, 0.0),
                    daily_loss_limit=daily_risk_state.daily_loss_limit,
                    kill_switch_engaged=daily_risk_state.kill_switch_engaged,
                    updated_at=snapshot.timestamp,
                )
                if close_event.close_reason == "unconfirmed":
                    session_state = self._session_guard.record_probe_failure(
                        session_state,
                        at=snapshot.timestamp,
                    )
                    if session_state.status is SessionStatus.STOPPED_FOR_DAY:
                        events.append(
                            to_ledger_entry(
                                SessionStoppedEvent(
                                    session_date=session_date,
                                    reason=session_state.stop_reason or "two_probe_failures",
                                    stopped_at=snapshot.timestamp,
                                ),
                                schema_version=SCHEMA_VERSION,
                            )
                        )
                        break

        for event in events:
            ledger_repository.append(event)

        projector = LedgerProjector(
            runtime_mode=RuntimeMode.PAPER,
            validation_stage=ValidationStage.PAPER_CANARY,
            starting_bankroll=self._config.initial_bankroll,
            daily_loss_limit=self._risk_limits.daily_loss_limit,
        )
        positions, sessions, risks, dashboard_snapshot = projector.project(
            ledger_repository.list_all()
        )
        last_event_id = events[-1].event_id if events else "seed"
        projection_repository.replace_positions(positions, last_event_id=last_event_id)
        projection_repository.replace_session_states(sessions)
        projection_repository.replace_daily_risk_states(risks)
        projection_repository.replace_dashboard_snapshot(dashboard_snapshot)

        session_summary_path = write_json_artifact(
            self._config.artifact_paths.paper,
            prefix="daily-session-summary",
            payload={
                "session_date": session_date,
                "processed_snapshots": len(snapshots),
                "session_status": session_state.status.value,
                "stop_reason": session_state.stop_reason,
                "evidence_source": evidence_source,
                "realized_loss": daily_risk_state.realized_loss,
                "open_risk": daily_risk_state.open_risk,
                "reconcile_summary": reconcile_result.summary,
                "dashboard_snapshot": dashboard_snapshot,
            },
        )
        probe_log_path = write_json_artifact(
            self._config.artifact_paths.paper,
            prefix="probe-outcome-log",
            payload={
                "session_date": session_date,
                "evidence_source": evidence_source,
                "probes": probe_logs,
            },
        )
        stop_reason_path = write_json_artifact(
            self._config.artifact_paths.paper,
            prefix="stop-reason-summary",
            payload={
                "session_date": session_date,
                "evidence_source": evidence_source,
                "stopped_for_day": session_state.status is SessionStatus.STOPPED_FOR_DAY,
                "stop_reason": session_state.stop_reason,
            },
        )
        weekly_snapshot_path = write_json_artifact(
            self._config.artifact_paths.paper,
            prefix="weekly-pnl-snapshot",
            payload={
                "session_date": session_date,
                "evidence_source": evidence_source,
                "total_capital": dashboard_snapshot.total_capital,
                "realized_pnl_today": dashboard_snapshot.realized_pnl_today,
                "realized_pnl_week": dashboard_snapshot.realized_pnl_week,
                "realized_pnl_month": dashboard_snapshot.realized_pnl_month,
            },
        )
        incident_note_path = self._write_incident_note(
            session_date=session_date,
            evidence_source=evidence_source,
            probe_logs=probe_logs,
        )
        return PaperSessionResult(
            session_summary_path=session_summary_path,
            probe_log_path=probe_log_path,
            stop_reason_path=stop_reason_path,
            weekly_snapshot_path=weekly_snapshot_path,
            incident_note_path=incident_note_path,
            processed_snapshots=len(snapshots),
            stopped_for_day=session_state.status is SessionStatus.STOPPED_FOR_DAY,
        )

    def _estimate(
        self,
        candidate: MarketCandidate,
        reference_events: list[ReferenceOddsEventDTO],
        as_of: datetime,
    ) -> EstimatedWinProbability:
        match_result = self._resolver.resolve(candidate, reference_events)
        if match_result.resolved_event is None:
            return EstimatedWinProbability(
                fair_probability=0.0,
                market_implied_probability=candidate.market_implied_probability,
                source_kind="blocked",
                source_timestamp=None,
                staleness_seconds=None,
                confidence_band=0.0,
                is_tradeable=False,
                block_reason=match_result.block_reason,
                reference_event_id=None,
                bookmaker_count=0,
            )
        reference_event = next(
            event
            for event in reference_events
            if event.event_id == match_result.resolved_event.reference_event_id
        )
        return self._reference_adapter.estimate(
            candidate,
            match_result.resolved_event,
            reference_event,
            as_of=as_of,
        )

    def _current_market_exposure(
        self,
        paper_positions: dict[str, PaperPosition],
        *,
        market_id: str,
    ) -> float:
        return sum(
            position.notional
            for position in paper_positions.values()
            if position.market_id == market_id
        )

    def _write_incident_note(
        self,
        *,
        session_date: object,
        evidence_source: str,
        probe_logs: list[dict[str, object]],
    ) -> Path | None:
        actionable_results = {
            "probe_opened",
            "probe_confirmed",
            "add_stage_2",
            "position_closed",
        }
        if any(log.get("result") in actionable_results for log in probe_logs):
            return None

        reason_counts: dict[str, int] = {}
        for log in probe_logs:
            reason = log.get("reason")
            if not isinstance(reason, str):
                continue
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        if not reason_counts:
            return None

        sorted_reasons = sorted(
            reason_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
        return write_json_artifact(
            self._config.artifact_paths.incidents,
            prefix="paper-session-incident",
            payload={
                "session_date": session_date,
                "evidence_source": evidence_source,
                "incident_type": "no_actionable_probes",
                "probe_log_count": len(probe_logs),
                "top_reason": sorted_reasons[0][0],
                "reason_counts": [
                    {"reason": reason, "count": count}
                    for reason, count in sorted_reasons
                ],
            },
        )


@dataclass(frozen=True, slots=True)
class _PaperSnapshot:
    timestamp: datetime
    gamma_markets: list[object]
    reference_events: list[object]


def _parse_snapshot(value: object) -> _PaperSnapshot:
    if not isinstance(value, dict):
        msg = "paper snapshot must be an object"
        raise ValueError(msg)
    gamma_markets = value.get("gamma_markets", [])
    reference_events = value.get("reference_events", [])
    if not isinstance(gamma_markets, list) or not isinstance(reference_events, list):
        msg = "paper snapshot lists are invalid"
        raise ValueError(msg)
    return _PaperSnapshot(
        timestamp=_parse_timestamp(value["timestamp"]),
        gamma_markets=gamma_markets,
        reference_events=reference_events,
    )


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        msg = "paper timestamp must be a string"
        raise ValueError(msg)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
