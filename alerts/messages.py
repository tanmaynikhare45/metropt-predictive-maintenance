"""Build the Slack text (and the one-line summary) for an alert decision."""
import pandas as pd

from . import config
from .recommendations import sensor_of, sensors_from_features, suggest_actions


def esc(text) -> str:
    """Slack treats & < > as control characters."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_time(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M")


def fmt_num(v, digits=2) -> str:
    return "n/a" if v is None or pd.isna(v) else f"{float(v):.{digits}f}"


def fmt_duration(td) -> str:
    minutes = int(pd.Timedelta(td).total_seconds() // 60)
    days, rest = divmod(minutes, 1440)
    hours, mins = divmod(rest, 60)
    parts = []
    if days:
        parts.append(f"{days} d")
    if hours or days:
        parts.append(f"{hours} h")
    parts.append(f"{mins} min")
    return " ".join(parts)


def dashboard_link(ts, base=None) -> str:
    base = (base or config.DASHBOARD_URL).rstrip("/")
    return f"{base}/?end={pd.Timestamp(ts).strftime('%Y-%m-%dT%H:%M:%SZ')}"


def feature_label(feature, z) -> str:
    base = feature.split("__")[0]
    sensor = sensor_of(feature)
    stat = base[len(sensor) + 1:] if base.startswith(sensor + "_") else ""
    name = f"{sensor} {stat}".strip()
    return f"{name} ({float(z):.1f} std from normal)"


def likely_cause(top_features, limit=3) -> str:
    """The sensors that deviate most from normal: one entry per sensor (its strongest feature)."""
    if not top_features:
        return "not available"
    chosen, seen = [], set()
    for feature, z in sorted(top_features.items(), key=lambda kv: -abs(float(kv[1]))):
        sensor = sensor_of(feature)
        if sensor in seen:
            continue
        seen.add(sensor)
        chosen.append(esc(feature_label(feature, z)))
        if len(chosen) == limit:
            break
    return ", ".join(chosen)


def title(decision, kind) -> str:
    if decision.action == "recovered":
        return ":white_check_mark: *Back to normal*"
    if decision.action == "reminder":
        return f":hourglass_flowing_sand: *STILL ACTIVE ({decision.severity})*"
    if decision.severity == "critical":
        head = "ESCALATED to CRITICAL" if decision.action == "escalation" else "CRITICAL"
        return f":rotating_light: *{head}: anomaly and elevated failure risk*"
    what = "elevated failure risk" if kind == "failure_risk" else "compressor behaving abnormally"
    return f":warning: *WARNING: {what}*"


def build_slack_text(decision, kind, summary, thresholds=None, rules=None, base_url=None) -> str:
    """Multi-line Slack text. Works with missing pieces (no LSTM, no risk score, no top features)."""
    thresholds = thresholds or {}
    t = pd.Timestamp(decision.time)
    lines = [title(decision, kind)]

    if decision.action == "recovered":
        since = decision.since
        span = f"{fmt_time(since)} to {fmt_time(t)} UTC ({fmt_duration(t - since)})" if since is not None else f"until {fmt_time(t)} UTC"
        lines.append(f"*Incident:* {span}")
        lines.append(f"<{dashboard_link(t, base_url)}|Open the dashboard at this time>")
        return "\n".join(lines)

    lines.append(f"*Time (UTC):* {fmt_time(t)}    *Severity:* {decision.severity}")
    if decision.action == "reminder" and decision.since is not None:
        lines.append(f"*Ongoing since:* {fmt_time(decision.since)} UTC ({fmt_duration(t - decision.since)})")

    scores = []
    if summary.get("risk") is not None:
        scores.append(f"*Failure risk:* {fmt_num(summary['risk'])} (threshold {fmt_num(thresholds.get('failure_threshold'))})")
    if summary.get("if_score") is not None:
        scores.append(f"*Anomaly score:* {fmt_num(summary['if_score'])} (threshold {fmt_num(thresholds.get('iforest_threshold'))})")
    if scores:
        lines.append("    ".join(scores))

    top = summary.get("top_features") or {}
    lines.append(f"*Likely cause:* {likely_cause(top)}")
    actions = suggest_actions(sensors_from_features(top), rules)
    lines.append("*Suggested action:* " + esc(" ".join(actions)))
    lines.append(f"<{dashboard_link(t, base_url)}|Open the dashboard at this time>")
    return "\n".join(lines)


def preview(text: str) -> str:
    """First line of an alert without Slack formatting (for tables and logs)."""
    first = text.split("\n", 1)[0]
    for token in ("*", ":rotating_light:", ":warning:", ":hourglass_flowing_sand:", ":white_check_mark:"):
        first = first.replace(token, "")
    return first.strip()
