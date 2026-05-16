# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Column type helpers for ZRDB result metadata."""

from datetime import date
from datetime import datetime
from datetime import time
from decimal import Decimal

try:
    from DateTime.DateTime import DateTime as ZopeDateTime
except ImportError:  # pragma: no cover - DateTime is present with Zope.
    ZopeDateTime = ()

INTEGER_TYPES = (bool, int)
NUMBER_TYPES = (float, Decimal)
DATE_TYPES = (date, datetime)
if ZopeDateTime:
    DATE_TYPES = DATE_TYPES + (ZopeDateTime,)
TIME_TYPES = (time,)
TEXT_TYPES = (str, bytes, bytearray, memoryview)


def zrdb_type_for_column(column, sample_values=()):
    """Return a ZRDB type code for a DB-API cursor description column."""
    type_code = column[1] if len(column) > 1 else None
    result = _zrdb_type_from_type_code(type_code)
    if result:
        return result

    for value in sample_values:
        result = zrdb_type_from_value(value)
        if result:
            return result

    return "s"


def zrdb_type_from_value(value):
    """Return a ZRDB type code for a Python value."""
    if value is None:
        return None
    if isinstance(value, INTEGER_TYPES):
        return "i"
    if isinstance(value, NUMBER_TYPES):
        return "n"
    if isinstance(value, DATE_TYPES):
        return "d"
    if isinstance(value, TIME_TYPES):
        return "t"
    if isinstance(value, TEXT_TYPES):
        return "s"
    return "s"


def _zrdb_type_from_type_code(type_code):
    if type_code is None:
        return None
    if isinstance(type_code, type):
        return zrdb_type_from_value(_sample_for_type(type_code))

    name = type_code.__class__.__name__.lower()
    value = str(type_code).lower()
    text = f"{name} {value}"

    if any(token in text for token in ("bool", "bit", "int", "long", "short")):
        return "i"
    if any(token in text for token in ("decimal", "double", "float", "number", "numeric", "real")):
        return "n"
    if any(token in text for token in ("date", "datetime", "timestamp")):
        return "d"
    if "time" in text:
        return "t"
    if any(token in text for token in ("binary", "bytes", "char", "str", "text", "unicode", "varchar")):
        return "s"

    return None


def _sample_for_type(value_type):
    if issubclass(value_type, bool):
        return True
    if issubclass(value_type, int):
        return 1
    if issubclass(value_type, float):
        return 1.0
    if issubclass(value_type, Decimal):
        return Decimal("1")
    if issubclass(value_type, datetime):
        return datetime(2000, 1, 1, 0, 0, 0)
    if issubclass(value_type, date):
        return date(2000, 1, 1)
    if issubclass(value_type, time):
        return time(0, 0, 0)
    if issubclass(value_type, TEXT_TYPES):
        return ""
    return None
