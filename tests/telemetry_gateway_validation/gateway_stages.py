"""The stages, deadlines, NRQL and verdicts behind the gateway telemetry test (NR-638736).

No network and no pytest in here, so test_gateway_stage_logic.py can show offline that every check can both pass and
fail. test_gateway_telemetry.py runs the NRQL against New Relic and feeds the rows to these functions.

Time is measured in minutes after T0, the moment the scenario service switched archive throttling on. The ticket's
stages, each judged +/- 2 minutes, where "by" means earlier is fine:

    export failure rate > 50%              by T+3
    queue saturation >= 95%                by T+8
    queue drops > 0                        by T+8
    receiver refused > 0                   by T+20
    a gap in New Relic-bound logs          by T+20
    back to baseline after the reset       by T+28, read as 8 minutes after a reset at T+20
"""

import statistics
from dataclasses import dataclass, fields
from typing import Callable, Dict, List, Optional, Tuple

GATEWAY_SERVICE = "relibank-telemetry-gateway"
# The archive exporter is told apart from the New Relic exporter by this metric attribute. Both are unconfirmed until the
# first live run, so test_gateway_telemetry.py checks them first and names what it found instead.
EXPORTER_ATTRIBUTE = "exporter"
ARCHIVE_EXPORTER = "otlphttp/archive"

TOLERANCE_MIN = 2
END_GRACE_MIN = 0.5  # a run switched off by hand this much before a stage's deadline is still judged on that stage
RECOVERY_AFTER_RESET_MIN = 8
BASELINE_MINUTES = 10  # minutes before T0 that describe the healthy baseline
BASELINE_PER_MIN = 1200  # items received a minute, from the ticket
BASELINE_TOLERANCE = 0.25
BASELINE_SATURATION_PCT = 5
MIN_MINUTES_WITH_TRAFFIC = 5  # a window with less traffic than this proves nothing, so it is not called healthy
FAILURE_RATE_PCT = 50
SATURATION_PCT = 95
GAP_FRACTION = 0.5  # a minute is a gap when New Relic-bound logs fall below this share of the baseline


@dataclass(frozen=True)
class Minute:
    """Everything measured in one minute. A value with no data in that minute counts as 0."""

    t: float  # minutes after T0 at the start of this minute
    received: float = 0.0
    refused: float = 0.0
    sent: float = 0.0  # archive exporter
    failed: float = 0.0
    dropped: float = 0.0
    queue_size: float = 0.0
    queue_capacity: float = 0.0
    nr_logs: float = 0.0  # logs that actually reached New Relic

    @property
    def failure_rate(self) -> float:
        total = self.failed + self.sent
        return 100 * self.failed / total if total else 0.0

    @property
    def saturation(self) -> float:
        return 100 * self.queue_size / self.queue_capacity if self.queue_capacity else 0.0


def merge_minutes(t0: float, *row_lists: List[dict]) -> List[Minute]:
    """Join the query results on the start of their minute. All queries must use the same SINCE and UNTIL."""
    merged: Dict[int, dict] = {}
    for rows in row_lists:
        for row in rows:
            merged.setdefault(int(row["beginTimeSeconds"]), {}).update(row)
    names = [f.name for f in fields(Minute) if f.name != "t"]
    return [
        Minute(t=(begin - t0) / 60, **{name: float(row.get(name) or 0) for name in names})
        for begin, row in sorted(merged.items())
    ]


# --- NRQL ------------------------------------------------------------------------------------------------------------


def _window(start_s: float, end_s: float) -> str:
    return f"SINCE {int(start_s)} UNTIL {int(end_s)} TIMESERIES 1 minute"


def received_query(start_s: float, end_s: float) -> str:
    return (
        "SELECT sum(otelcol_receiver_accepted_log_records) AS received, "
        "sum(otelcol_receiver_refused_log_records) AS refused "
        f"FROM Metric WHERE service.name = '{GATEWAY_SERVICE}' {_window(start_s, end_s)}"
    )


def archive_exporter_query(
    start_s: float, end_s: float, attribute: str = EXPORTER_ATTRIBUTE, exporter: str = ARCHIVE_EXPORTER
) -> str:
    return (
        "SELECT sum(otelcol_exporter_sent_log_records) AS sent, "
        "sum(otelcol_exporter_send_failed_log_records) AS failed, "
        "sum(otelcol_exporter_enqueue_failed_log_records) AS dropped, "
        "max(otelcol_exporter_queue_size) AS queue_size, "
        "max(otelcol_exporter_queue_capacity) AS queue_capacity "
        f"FROM Metric WHERE service.name = '{GATEWAY_SERVICE}' AND {attribute} = '{exporter}' "
        f"{_window(start_s, end_s)}"
    )


def new_relic_logs_query(start_s: float, end_s: float) -> str:
    # The loadgen's two message bodies; log.type does not work as a facet in New Relic
    return (
        f"SELECT count(*) AS nr_logs FROM Log WHERE message IN ('audit event', 'other event') {_window(start_s, end_s)}"
    )


def exporters_query(attribute: str = EXPORTER_ATTRIBUTE) -> str:
    return (
        f"SELECT uniques({attribute}) AS exporters FROM Metric "
        f"WHERE metricName = 'otelcol_exporter_queue_size' AND service.name = '{GATEWAY_SERVICE}' SINCE 24 hours ago"
    )


# --- baseline --------------------------------------------------------------------------------------------------------


def is_baseline_minute(m: Minute, expected: float = BASELINE_PER_MIN, tolerance: float = BASELINE_TOLERANCE) -> bool:
    return (
        abs(m.received - expected) <= tolerance * expected
        and m.saturation < BASELINE_SATURATION_PCT
        and m.refused == 0
        and m.dropped == 0
        and m.failed == 0
    )


def baseline_problems(
    minutes: List[Minute], expected: float = BASELINE_PER_MIN, tolerance: float = BASELINE_TOLERANCE
) -> List[str]:
    """What is wrong with a window that should be healthy, each naming the measure and what was seen. [] means healthy."""
    flowing = [m for m in minutes if m.received > 0]
    if len(flowing) < MIN_MINUTES_WITH_TRAFFIC:
        return [
            f"only {len(flowing)} of {len(minutes)} minutes received any logs (need {MIN_MINUTES_WITH_TRAFFIC}); "
            "a window without traffic proves nothing"
        ]
    problems = []
    typical = statistics.median(m.received for m in flowing)
    if abs(typical - expected) > tolerance * expected:
        problems.append(f"received a typical {typical:.0f} items/min, expected {expected:.0f} +/-{tolerance:.0%}")
    peak = max(m.saturation for m in minutes)
    if peak >= BASELINE_SATURATION_PCT:
        problems.append(f"queue saturation peaked at {peak:.1f}%, expected under {BASELINE_SATURATION_PCT}%")
    for name, total in (
        ("refused", sum(m.refused for m in minutes)),
        ("queue drops", sum(m.dropped for m in minutes)),
        ("export failures", sum(m.failed for m in minutes)),
    ):
        if total > 0:
            problems.append(f"{name}: {total:.0f} records, expected 0")
    return problems


def minutes_before_t0(minutes: List[Minute], count: int = BASELINE_MINUTES) -> List[Minute]:
    """The last `count` whole minutes that ended at or before T0.

    The minute that contains T0 is left out on purpose. T0 is rarely on a minute boundary (the first sandbox proof run
    switched throttling on 0.09 s after one), so that minute is almost entirely throttled and its queue is already filling.
    """
    ended = [m for m in minutes if m.t + 1 <= 1e-9]
    return ended[-count:]


def baseline_nr_logs(minutes: List[Minute]) -> float:
    """Typical New Relic-bound logs a minute before T0; 0 when none arrived."""
    before = [m.nr_logs for m in minutes_before_t0(minutes) if m.nr_logs > 0]
    return statistics.median(before) if before else 0.0


# --- failure stages --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage:
    key: str
    title: str
    deadline_min: float
    unit: str
    measure: Callable[[Minute], float]
    hit: Callable[[Minute], bool]
    closest: Callable = (
        max  # picks the value shown when the stage is missed: highest for rising measures, lowest for a gap
    )


def failure_stages(baseline_logs: float) -> List[Stage]:
    return [
        Stage(
            "export_failures",
            f"export failure rate > {FAILURE_RATE_PCT}%",
            3,
            "%",
            lambda m: m.failure_rate,
            lambda m: m.failure_rate > FAILURE_RATE_PCT,
        ),
        Stage(
            "queue_saturation",
            f"queue saturation >= {SATURATION_PCT}%",
            8,
            "%",
            lambda m: m.saturation,
            lambda m: m.saturation >= SATURATION_PCT,
        ),
        Stage("queue_drops", "queue drops > 0", 8, " records", lambda m: m.dropped, lambda m: m.dropped > 0),
        Stage("receiver_refused", "receiver refused > 0", 20, " records", lambda m: m.refused, lambda m: m.refused > 0),
        Stage(
            "new_relic_gap",
            f"gap in New Relic-bound logs (below {GAP_FRACTION:.0%} of the {baseline_logs:.0f}/min baseline)",
            20,
            " logs/min",
            lambda m: m.nr_logs,
            lambda m: m.nr_logs < GAP_FRACTION * baseline_logs,
            closest=min,
        ),
    ]


@dataclass(frozen=True)
class Verdict:
    title: str
    ok: bool
    deadline_min: float
    first_hit: Optional[float]  # minutes after T0, None if never
    closest: Optional[float]
    closest_at: Optional[float]
    unit: str

    def describe(self) -> str:
        limit = self.deadline_min + TOLERANCE_MIN
        needed = f"needed by T+{self.deadline_min:g} min (+{TOLERANCE_MIN} min tolerance, T+{limit:g})"
        if self.ok:
            return f"stage '{self.title}': reached at T+{self.first_hit:.0f} min, {needed}"
        seen = "never reached" if self.first_hit is None else f"first reached at T+{self.first_hit:.0f} min, too late"
        if self.closest is None:
            return f"stage '{self.title}' missed: {seen}; {needed}; no data in that window"
        return (
            f"stage '{self.title}' missed: {seen}; {needed}; "
            f"closest value up to T+{limit:g} was {self.closest:.1f}{self.unit} at T+{self.closest_at:.0f} min"
        )


def evaluate_stage(minutes: List[Minute], stage: Stage, throttle_minutes: Optional[float] = None) -> Verdict:
    """Judge one stage. Only minutes while throttling was on count (throttle_minutes=None: still on)."""
    limit = stage.deadline_min + TOLERANCE_MIN
    # The minute that contains T0 counts (it is almost entirely throttled), so a minute counts when it ends after T0
    during = [m for m in minutes if m.t > -1 and (throttle_minutes is None or m.t < throttle_minutes)]
    hits = [m for m in during if stage.hit(m)]
    first = max(0.0, hits[0].t) if hits else None
    window = [m for m in during if m.t <= limit]
    pick = stage.closest(window, key=stage.measure) if window else None
    return Verdict(
        title=stage.title,
        ok=first is not None and first <= limit,
        deadline_min=stage.deadline_min,
        first_hit=first,
        closest=stage.measure(pick) if pick else None,
        closest_at=max(0.0, pick.t) if pick else None,
        unit=stage.unit,
    )


def too_short_to_judge(stage: Stage, throttle_minutes: float) -> Optional[str]:
    """The reason to skip a stage because throttling ended before its deadline, or None when it can be judged.

    A stage is judged once throttling has lasted until its deadline (a 20 minute run judges the T+20 stages), allowing
    END_GRACE_MIN for a run that was switched off by hand a little early.
    """
    if throttle_minutes < stage.deadline_min - END_GRACE_MIN:
        return f"throttling was on for {throttle_minutes:.1f} min and '{stage.title}' is due by T+{stage.deadline_min:g} min"
    return None


# --- recovery --------------------------------------------------------------------------------------------------------


def recovery_not_yet_judgeable(minutes: List[Minute], reset_min: float) -> Optional[str]:
    """The reason to skip the recovery check because not enough time has passed after the reset, or None."""
    needed = reset_min + RECOVERY_AFTER_RESET_MIN + TOLERANCE_MIN
    last = minutes[-1].t if minutes else None
    if last is None or last < needed:
        have = "no data" if last is None else f"data up to T+{last:.0f} min"
        return f"recovery is judged {RECOVERY_AFTER_RESET_MIN + TOLERANCE_MIN} min after the reset (T+{needed:.0f}); {have}"
    return None


def evaluate_recovery(
    minutes: List[Minute],
    reset_min: float,
    expected: float = BASELINE_PER_MIN,
    tolerance: float = BASELINE_TOLERANCE,
) -> Tuple[bool, str]:
    """Back to baseline = two minutes in a row that look like the baseline, within 8 (+2) minutes after the reset."""
    # A minute that starts a few seconds before the reset is almost all after it, so it counts
    after = [m for m in minutes if m.t >= reset_min - 0.05]
    limit = RECOVERY_AFTER_RESET_MIN + TOLERANCE_MIN
    needed = f"needed within {RECOVERY_AFTER_RESET_MIN} min of the reset (+{TOLERANCE_MIN} min tolerance)"
    for first, second in zip(after, after[1:]):
        if is_baseline_minute(first, expected, tolerance) and is_baseline_minute(second, expected, tolerance):
            took = max(0.0, first.t - reset_min)
            if took <= limit:
                return True, f"stage 'back to baseline': {took:.0f} min after the reset, {needed}"
            return False, f"stage 'back to baseline' missed: back after {took:.0f} min, too late; {needed}"
    if not after:
        return False, f"stage 'back to baseline' missed: no data after the reset; {needed}"
    last = after[-1]
    return False, (
        f"stage 'back to baseline' missed: never back to baseline in the {len(after)} min after the reset; {needed}; "
        f"last minute: received {last.received:.0f}, saturation {last.saturation:.1f}%, refused {last.refused:.0f}, "
        f"queue drops {last.dropped:.0f}, export failures {last.failed:.0f}"
    )
