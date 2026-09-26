"""Structured logger: one JSON object per line, including the `extra=` fields."""

import json
import logging

from utils.structured_logger import JsonFormatter, get_logger


def _format(**extra) -> dict:
    record = logging.makeLogRecord({"name": "argus.test", "levelname": "INFO", "msg": "hi %s"})
    record.args = ("there",)
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(JsonFormatter().format(record))


def test_extra_fields_are_included():
    line = _format(task_id="kyc-1", agents=["identity"])

    assert line["msg"] == "hi there"
    assert line["task_id"] == "kyc-1"
    assert line["agents"] == ["identity"]
    assert line["ts"].endswith("Z")


def test_standard_record_attributes_are_not_repeated():
    assert set(_format()) == {"ts", "level", "name", "msg"}


def test_values_that_are_not_json_are_stringified():
    assert _format(path=object())["path"].startswith("<object object")


def test_get_logger_configures_once():
    first = get_logger("argus.test.once")
    second = get_logger("argus.test.once")

    assert first is second
    assert len(first.handlers) == 1
