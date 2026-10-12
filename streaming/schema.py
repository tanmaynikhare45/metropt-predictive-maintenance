"""Validation of one sensor reading (one Kafka message)."""
import json
from datetime import datetime, timezone
from typing import Annotated, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ml.features import SENSORS

Sensor = Annotated[float, Field(allow_inf_nan=False)]     # NaN / inf are rejected


class Reading(BaseModel):
    model_config = ConfigDict(extra="ignore")

    time: datetime
    tp2: Sensor
    tp3: Sensor
    h1: Sensor
    dv_pressure: Sensor
    reservoirs: Sensor
    oil_temperature: Sensor
    motor_current: Sensor
    comp: Sensor
    dv_eletric: Sensor
    towers: Sensor
    mpg: Sensor
    lps: Sensor
    pressure_switch: Sensor
    oil_level: Sensor
    caudal_impulses: Sensor

    @field_validator("time")
    @classmethod
    def _to_naive_utc(cls, v):
        # the whole project uses naive timestamps that mean UTC
        if v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        return v

    def to_row(self) -> tuple:
        """The 15 sensor values in ml.features.SENSORS order."""
        return tuple(float(getattr(self, name)) for name in SENSOR_FIELDS)


SENSOR_FIELDS = [c.lower() for c in SENSORS]
assert SENSOR_FIELDS == [f for f in Reading.model_fields if f != "time"], "Reading fields out of sync with ml.features.SENSORS"


def parse_reading(payload) -> Tuple[Optional[Reading], Optional[str]]:
    """Parse bytes / str / dict into a Reading. Returns (reading, None) or (None, error message)."""
    try:
        data = payload if isinstance(payload, dict) else json.loads(payload)
    except (ValueError, TypeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "message is not a JSON object"
    try:
        return Reading.model_validate(data), None
    except ValidationError as exc:
        msg = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
        return None, msg
