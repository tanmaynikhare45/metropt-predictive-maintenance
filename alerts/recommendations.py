"""Turn the features that deviate most into sensor names and a suggested action."""
import json
from pathlib import Path

from . import config

_STATS = ("_mean", "_std", "_min", "_max")


def sensor_of(feature: str) -> str:
    """'TP2_mean' -> 'TP2', 'Oil_temperature_std' -> 'Oil_temperature', 'TP2_mean__std6h' -> 'TP2'."""
    base = feature.split("__")[0]
    for suffix in _STATS:
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def sensors_from_features(top_features) -> list:
    """Unique sensor names, strongest deviation first. top_features: {feature: z-score}."""
    if not top_features:
        return []
    ordered = sorted(top_features.items(), key=lambda kv: -abs(float(kv[1])))
    seen, out = set(), []
    for feature, _ in ordered:
        s = sensor_of(feature)
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def load_rules(path=None) -> dict:
    return json.loads(Path(path or config.RECOMMENDATIONS_FILE).read_text(encoding="utf-8"))


def suggest_actions(sensors, rules=None, max_actions=2) -> list:
    """Rules that match the most (and the strongest) sensors come first. Falls back to a generic hint."""
    rules = rules or load_rules()
    scored = []
    for rule in rules.get("rules", []):
        positions = [i for i, s in enumerate(sensors) if s in rule["sensors"]]
        if positions:
            scored.append((-len(positions), min(positions), rule["action"]))
    scored.sort()
    actions = [a for _, _, a in scored[:max_actions]]
    return actions or [rules.get("default", "Review the dashboard and inspect the compressor.")]
