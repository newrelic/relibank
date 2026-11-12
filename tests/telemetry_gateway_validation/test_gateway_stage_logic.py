"""Offline tests for the gateway telemetry checks (NR-638736): no cluster and no New Relic account needed.

The gateway telemetry test (test_gateway_telemetry.py) is only worth anything if it can fail. These tests feed
gateway_stages.py made-up minutes: a run that behaves like the first sandbox run (failures from T+2, refusals from T+6,
a full queue and drops from T+7, back to baseline a minute after the reset), the same run made slow or broken, and a
quiet window with throttling off. Every check must pass on the first and fail, naming the stage and the value, on the
others.
"""

import pytest

from gateway_stages import (
    BASELINE_PER_MIN,
    Minute,
    archive_exporter_query,
    baseline_nr_logs,
    baseline_problems,
    evaluate_recovery,
    evaluate_stage,
    exporters_query,
    failure_stages,
    merge_minutes,
    minutes_before_t0,
    new_relic_logs_query,
    received_query,
    recovery_not_yet_judgeable,
    too_short_to_judge,
)

HEALTHY = dict(received=1200, refused=0, sent=960, failed=0, dropped=0, queue_size=1, queue_capacity=6000, nr_logs=1200)
RESET_AT = 20


def minute(t, **changes):
    return Minute(t=t, **{**HEALTHY, **changes})


def run_of_minutes(failures_at=2, refused_at=6, saturated_at=7, dropped_at=7, gap_at=7, recovered_at=21, end=40):
    """Minutes -10 .. end of a run with throttling on from T+0 to T+20. Pass a later (or None) *_at to slow a stage."""
    minutes = []
    for t in range(-10, end):
        changes = {}
        if recovered_at is not None and RESET_AT <= t < recovered_at:
            changes.update(queue_size=2000, nr_logs=600)  # draining after the reset
        if t >= 0 and t < RESET_AT:
            if failures_at is not None and t >= failures_at:
                changes.update(sent=0, failed=960, queue_size=min(5000, 1000 * (t - failures_at + 1)))
            if saturated_at is not None and t >= saturated_at:
                changes.update(queue_size=6000)
            if refused_at is not None and t >= refused_at:
                changes.update(refused=300, received=900)
            if dropped_at is not None and t >= dropped_at:
                changes.update(dropped=500)
            if gap_at is not None and t >= gap_at:
                changes.update(nr_logs=100)
        if recovered_at is None and t >= RESET_AT:
            changes.update(queue_size=6000, refused=300, dropped=500, sent=0, failed=960, nr_logs=100)
        minutes.append(minute(t, **changes))
    return minutes


def verdicts(minutes, throttle_minutes=RESET_AT):
    stages = failure_stages(baseline_nr_logs(minutes))
    return {s.key: evaluate_stage(minutes, s, throttle_minutes) for s in stages}


# --- a run that behaves as designed ----------------------------------------------------------------------------------


def test_a_healthy_baseline_has_no_problems():
    assert baseline_problems([m for m in run_of_minutes() if m.t < 0]) == []


def test_every_stage_of_a_run_that_behaves_as_designed_is_reached_in_time():
    for key, verdict in verdicts(run_of_minutes()).items():
        assert verdict.ok, f"{key}: {verdict.describe()}"


def test_the_gateway_is_back_to_baseline_a_minute_after_the_reset():
    ok, message = evaluate_recovery(run_of_minutes(), RESET_AT)
    assert ok, message
    assert "1 min after the reset" in message


def test_the_single_item_in_the_queue_seen_in_the_real_baseline_is_not_a_problem():
    window = [minute(t, queue_size=1 if t % 3 else 0) for t in range(-10, 0)]
    assert baseline_problems(window) == []


# --- the same run made slow or broken: each check must fail and say why ----------------------------------------------


def test_failures_that_start_too_late_miss_their_stage_and_report_the_value_seen():
    verdict = verdicts(run_of_minutes(failures_at=12))["export_failures"]
    assert not verdict.ok
    message = verdict.describe()
    assert "export failure rate > 50%" in message
    assert "needed by T+3" in message
    assert "first reached at T+12 min, too late" in message


def test_a_queue_that_never_fills_reports_the_highest_saturation_it_reached():
    verdict = verdicts(run_of_minutes(saturated_at=None))["queue_saturation"]
    assert not verdict.ok
    message = verdict.describe()
    assert "never reached" in message
    assert "closest value up to T+10 was 83.3%" in message  # 5000 of 6000 items


@pytest.mark.parametrize(
    "slowed, stage",
    [
        ({"dropped_at": None}, "queue_drops"),
        ({"refused_at": None}, "receiver_refused"),
        ({"gap_at": None}, "new_relic_gap"),
        ({"failures_at": None}, "export_failures"),
    ],
)
def test_a_stage_that_never_happens_is_reported_as_missed(slowed, stage):
    verdict = verdicts(run_of_minutes(**slowed))[stage]
    assert not verdict.ok
    assert "never reached" in verdict.describe()


def test_a_gap_in_new_relic_logs_reports_the_lowest_count_it_saw():
    verdict = verdicts(run_of_minutes(gap_at=None))["new_relic_gap"]
    assert "closest value up to T+22 was 1200.0 logs/min" in verdict.describe()


def test_a_gateway_that_never_recovers_says_what_the_last_minute_looked_like():
    ok, message = evaluate_recovery(run_of_minutes(recovered_at=None), RESET_AT)
    assert not ok
    assert "never back to baseline" in message
    assert "saturation 100.0%" in message
    assert "refused 300" in message


def test_a_slow_recovery_is_reported_as_too_late():
    ok, message = evaluate_recovery(run_of_minutes(recovered_at=35, end=45), RESET_AT)
    assert not ok
    assert "back after 15 min, too late" in message


# --- the negative control: with throttling off nothing may look like a failure ---------------------------------------


def test_with_throttling_off_no_failure_stage_is_reached():
    quiet = [minute(t) for t in range(0, 30)]
    for key, verdict in verdicts(quiet, throttle_minutes=None).items():
        assert not verdict.ok, f"{key} would pass on a healthy gateway, so the check could never fail"


def test_a_window_with_traffic_and_no_failures_passes_the_control_and_one_with_refusals_does_not():
    assert baseline_problems([minute(t) for t in range(30)]) == []
    problems = baseline_problems([minute(t, refused=40) if t == 12 else minute(t) for t in range(30)])
    assert problems == ["refused: 40 records, expected 0"]


def test_silence_is_not_mistaken_for_a_healthy_gateway():
    problems = baseline_problems([minute(t, received=0, sent=0, nr_logs=0) for t in range(30)])
    assert len(problems) == 1 and "proves nothing" in problems[0]


def test_a_baseline_with_the_wrong_rate_names_the_rate_it_saw():
    problems = baseline_problems([minute(t, received=1800) for t in range(-10, 0)])
    assert problems == [f"received a typical 1800 items/min, expected {BASELINE_PER_MIN:.0f} +/-25%"]


def test_every_kind_of_trouble_in_a_baseline_is_listed():
    window = [minute(t, queue_size=1500, dropped=2, failed=3, refused=4) for t in range(-10, 0)]
    problems = baseline_problems(window)
    assert [p.split(":")[0].split(" peaked")[0] for p in problems] == [
        "queue saturation",
        "refused",
        "queue drops",
        "export failures",
    ]


# --- deciding whether a run can be judged at all ---------------------------------------------------------------------


def test_a_short_run_is_only_judged_on_the_stages_that_were_due_while_throttling_was_on():
    stages = {s.key: s for s in failure_stages(1200)}
    assert "due by T+3 min" in too_short_to_judge(stages["export_failures"], 1)
    assert too_short_to_judge(stages["export_failures"], 3) is None
    assert "due by T+8 min" in too_short_to_judge(stages["queue_saturation"], 4)
    assert too_short_to_judge(stages["receiver_refused"], 19) is not None
    assert too_short_to_judge(stages["receiver_refused"], 19.6) is None  # switched off by hand a little early


def test_a_standard_twenty_minute_run_is_judged_on_every_stage():
    assert [too_short_to_judge(stage, RESET_AT) for stage in failure_stages(1200)] == [None] * 5


def test_recovery_is_not_judged_until_ten_minutes_after_the_reset():
    minutes = [minute(t) for t in range(-10, 28)]
    assert "T+30" in recovery_not_yet_judgeable(minutes, RESET_AT)
    assert recovery_not_yet_judgeable([minute(t) for t in range(-10, 31)], RESET_AT) is None
    assert recovery_not_yet_judgeable([], RESET_AT) is not None


# --- joining the query results ---------------------------------------------------------------------------------------


def test_query_results_are_joined_by_minute_and_a_missing_value_counts_as_zero():
    t0 = 1_000_000
    gateway = [
        {"beginTimeSeconds": t0 - 60, "received": 1200, "refused": None},
        {"beginTimeSeconds": t0, "received": 1100, "refused": 7},
    ]
    archive = [
        {"beginTimeSeconds": t0, "sent": 0, "failed": 960, "dropped": None, "queue_size": 3000, "queue_capacity": 6000}
    ]
    logs = [{"beginTimeSeconds": t0 - 60, "nr_logs": 1190}, {"beginTimeSeconds": t0, "nr_logs": None}]
    merged = merge_minutes(t0, gateway, archive, logs)
    assert [m.t for m in merged] == [-1, 0]
    assert merged[0].received == 1200 and merged[0].refused == 0 and merged[0].nr_logs == 1190
    assert merged[1].failed == 960 and merged[1].dropped == 0 and merged[1].nr_logs == 0
    assert merged[1].failure_rate == 100 and merged[1].saturation == 50


def test_the_queries_read_the_gateway_and_use_one_window_so_the_minutes_line_up():
    window = "SINCE 1000 UNTIL 2000 TIMESERIES 1 minute"
    for query in (received_query(1000, 2000), archive_exporter_query(1000, 2000), new_relic_logs_query(1000, 2000)):
        assert query.endswith(window), query
        assert '"' not in query  # sent as a GraphQL variable, but keep it simple to paste into the query builder
    assert "service.name = 'relibank-telemetry-gateway'" in received_query(1000, 2000)
    assert "exporter = 'otlphttp/archive'" in archive_exporter_query(1000, 2000)
    assert "exporter = 'other'" in archive_exporter_query(1000, 2000, exporter="other")
    assert "uniques(exporter)" in exporters_query()


# --- minutes that do not line up with T0: the first sandbox proof run -----------------------------------------------------
# Throttling went on at 1794472655.094 and was reset at 1794473855.045. The test asks New Relic for whole-second minutes that
# start 11 minutes before T0, so one minute starts at 1794472655, 0.09 s BEFORE T0. That minute is the first throttled minute
# (the queue was already at 9.3% in it), but its start is before T0, which once made the baseline check fail on a healthy
# gateway.
REAL_T0 = 1794472655.0941465
REAL_RESET = 1794473855.0450747
REAL_RESET_MIN = (REAL_RESET - REAL_T0) / 60


def real_alignment_run(failures_from=2):
    """The proof run as New Relic reported it: the queue already holds 558 items in the minute that contains T0, and export
    failures are first counted two minutes in (failures_from)."""
    start = int(REAL_T0 - (10 + 1) * 60)
    minutes = []
    for k in range(36):
        t = (start + 60 * k - REAL_T0) / 60
        n = k - 11  # n = 0 is the minute that contains T0
        changes = {}
        if 0 <= n < 20:
            changes.update(queue_size=min(6000, 558 + 1000 * n))
            if n >= failures_from:
                changes.update(sent=60, failed=900)
            if n >= 6:
                changes.update(refused=300, received=900)
            if n >= 7:
                changes.update(dropped=500, nr_logs=100)
        elif n == 20:  # starts 0.05 s before the reset, draining
            changes.update(queue_size=2000, nr_logs=600)
        minutes.append(minute(t, **changes))
    return minutes


def test_the_minute_that_contains_t0_is_the_first_throttled_minute_not_part_of_the_baseline():
    minutes = real_alignment_run()
    old_filter = [m for m in minutes if -10 <= m.t < 0]
    assert baseline_problems(old_filter) == ["queue saturation peaked at 9.3%, expected under 5%"]  # what went wrong
    before = minutes_before_t0(minutes)
    assert len(before) == 10
    assert all(m.t + 1 <= 0 for m in before)
    assert baseline_problems(before) == []


def test_the_minute_that_contains_t0_counts_towards_the_failure_stages():
    minutes = real_alignment_run(failures_from=0)  # failures already visible in the first throttled minute
    verdict = verdicts(minutes, throttle_minutes=REAL_RESET_MIN)["export_failures"]
    assert verdict.ok and verdict.first_hit == 0, verdict.describe()
    later = verdicts(real_alignment_run(), throttle_minutes=REAL_RESET_MIN)["export_failures"]
    assert round(later.first_hit) == 2  # the minute starts 0.09 s before T0 + 2 min


def test_every_stage_and_the_recovery_pass_on_the_real_alignment():
    minutes = real_alignment_run()
    for key, verdict in verdicts(minutes, throttle_minutes=REAL_RESET_MIN).items():
        assert verdict.ok, f"{key}: {verdict.describe()}"
    ok, message = evaluate_recovery(minutes, REAL_RESET_MIN)
    assert ok, message
    assert "1 min after the reset" in message  # the minute that starts at the reset is still draining
