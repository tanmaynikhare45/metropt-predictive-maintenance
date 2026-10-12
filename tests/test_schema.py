import json

from ml.features import SENSORS
from streaming.schema import SENSOR_FIELDS, parse_reading


def good(**over):
    msg = {"time": "2020-06-05T08:00:10", **{c: 1.5 for c in SENSOR_FIELDS}}
    msg.update(over)
    return msg


def test_valid_message():
    r, err = parse_reading(json.dumps(good()).encode())
    assert err is None
    assert len(r.to_row()) == 15 == len(SENSORS)
    assert r.time.tzinfo is None


def test_timezone_is_converted_to_naive_utc():
    r, _ = parse_reading(good(time="2020-06-05T10:00:00+02:00"))
    assert str(r.time) == "2020-06-05 08:00:00"


def test_numeric_strings_are_accepted_but_text_is_not():
    assert parse_reading(good(tp2="5.25"))[0].tp2 == 5.25
    r, err = parse_reading(good(tp2="abc"))
    assert r is None and "tp2" in err


def test_missing_sensor_is_rejected():
    msg = good()
    del msg["oil_temperature"]
    r, err = parse_reading(msg)
    assert r is None and "oil_temperature" in err


def test_nan_and_inf_are_rejected():
    assert parse_reading(good(tp2=float("nan")))[0] is None
    assert parse_reading(good(tp3=float("inf")))[0] is None
    # NaN also arrives as the bare token NaN in JSON text
    text = json.dumps(good()).replace('"tp2": 1.5', '"tp2": NaN')
    assert parse_reading(text)[0] is None


def test_garbage_is_rejected_without_raising():
    for payload in [b"not json", b"[1, 2, 3]", b"", None, b'{"time": "not-a-time"}']:
        r, err = parse_reading(payload)
        assert r is None and err
