import pandas as pd

from alerts.messages import build_slack_text, dashboard_link, esc, fmt_duration, likely_cause, preview
from alerts.recommendations import load_rules, sensor_of, sensors_from_features, suggest_actions
from alerts.rules import Decision

T = pd.Timestamp("2020-06-05 09:40")
SUMMARY = {
    "risk": 0.82, "if_score": 0.61,
    "top_features": {"TP2_mean": 3.2, "Oil_temperature_std": 2.1, "COMP_mean": 1.0},
}
THRESHOLDS = {"failure_threshold": 0.5, "iforest_threshold": 0.55}


def text(action="start", severity="critical", kind="failure_risk", summary=SUMMARY, since=None):
    d = Decision(action, severity, T, since or T)
    return build_slack_text(d, kind, summary, THRESHOLDS, base_url="http://dash.test")


def test_feature_names_become_sensor_names():
    assert sensor_of("TP2_mean") == "TP2"
    assert sensor_of("Oil_temperature_std") == "Oil_temperature"
    assert sensor_of("DV_pressure_max") == "DV_pressure"
    assert sensor_of("Caudal_impulses_mean") == "Caudal_impulses"
    assert sensor_of("TP2_mean__std6h") == "TP2"
    assert sensors_from_features({"A_mean": 1.0, "TP2_mean": 3.0, "TP2_max": 2.5, "Oil_temperature_min": 2.0}) == \
        ["TP2", "Oil_temperature", "A"]


def test_recommendations_follow_the_strongest_sensors():
    rules = load_rules()
    assert "leaks" in suggest_actions(["TP2", "TP3"], rules)[0]
    assert "oil" in suggest_actions(["Oil_temperature"], rules)[0].lower()
    assert suggest_actions(["Unknown"], rules) == [rules["default"]]
    assert suggest_actions([], rules) == [rules["default"]]
    assert len(suggest_actions(["TP2", "Oil_temperature", "Motor_current"], rules, max_actions=2)) == 2


def test_critical_message_has_cause_action_scores_and_link():
    m = text()
    assert "CRITICAL" in m and "2020-06-05 09:40" in m
    assert "0.82" in m and "threshold 0.50" in m and "0.61" in m
    assert "TP2 mean (3.2 std from normal)" in m
    assert "Suggested action:" in m and "leaks" in m
    assert "http://dash.test/?end=2020-06-05T09:40:00Z" in m


def test_warning_titles_depend_on_the_kind():
    assert "compressor behaving abnormally" in text(severity="warning", kind="anomaly")
    assert "elevated failure risk" in text(severity="warning", kind="failure_risk")
    assert "ESCALATED to CRITICAL" in text(action="escalation")


def test_reminder_shows_how_long_it_has_been_going():
    m = text(action="reminder", severity="warning", since=pd.Timestamp("2020-06-05 03:40"))
    assert "STILL ACTIVE" in m and "Ongoing since" in m and "6 h 0 min" in m


def test_recovered_message():
    m = text(action="recovered", severity="info", since=pd.Timestamp("2020-06-04 08:20"))
    assert "Back to normal" in m and "1 d 1 h 20 min" in m and "Suggested action" not in m


def test_message_survives_missing_information():
    m = text(summary={})
    assert "not available" in m and "Suggested action" in m
    m = text(summary={"if_score": 0.6})
    assert "Failure risk" not in m and "Anomaly score" in m


def test_slack_control_characters_are_escaped():
    assert esc("a < b & c > d") == "a &lt; b &amp; c &gt; d"
    assert "<script>" not in likely_cause({"<script>_mean": 5.0})


def test_likely_cause_lists_each_sensor_once_strongest_first():
    cause = likely_cause({"TP2_mean": 5.0, "TP2_max": 4.0, "TP3_mean": 3.0, "H1_std": 2.0, "Motor_current_mean": 1.0})
    assert cause.count("TP2") == 1 and cause.startswith("TP2 mean (5.0 std from normal)")
    assert "TP3" in cause and "H1" in cause and "Motor_current" not in cause      # three sensors at most


def test_helpers():
    assert fmt_duration(pd.Timedelta(minutes=45)) == "45 min"
    assert fmt_duration(pd.Timedelta(hours=2, minutes=5)) == "2 h 5 min"
    assert dashboard_link(T, "http://x/") == "http://x/?end=2020-06-05T09:40:00Z"
    assert preview(text()).startswith("CRITICAL")
