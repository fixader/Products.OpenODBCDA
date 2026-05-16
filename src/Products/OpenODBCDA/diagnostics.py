# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Runtime diagnostics for OpenODBCDA."""

from datetime import date
from datetime import datetime
from datetime import time
from decimal import Decimal

from .types import zrdb_type_for_column
from .types import zrdb_type_from_value


TYPE_MAPPING_CASES = (
    ("integer value", 1, "i"),
    ("boolean value", True, "i"),
    ("float value", 1.5, "n"),
    ("decimal value", Decimal("1.5"), "n"),
    ("date value", date(2026, 5, 16), "d"),
    ("datetime value", datetime(2026, 5, 16, 12, 30, 0), "d"),
    ("time value", time(12, 30, 0), "t"),
    ("text value", "text", "s"),
    ("bytes value", b"binary", "s"),
)


def run_type_mapping_diagnostics():
    """Run internal type-mapping diagnostics without touching a database."""
    results = []
    for label, value, expected in TYPE_MAPPING_CASES:
        actual = zrdb_type_from_value(value)
        results.append(_result(label, expected, actual))

    results.append(
        _result(
            "unknown type with decimal sample",
            "n",
            zrdb_type_for_column(("amount", object, None, None), (None, Decimal("9.99"))),
        )
    )
    results.append(
        _result(
            "unknown type with integer sample",
            "i",
            zrdb_type_for_column(("small_number", object, None, None), (None, 7)),
        )
    )
    results.append(
        _result(
            "unknown all-null column fallback",
            "s",
            zrdb_type_for_column(("empty", object, None, None), (None, None)),
        )
    )
    return results


def run_connection_diagnostics(database_connection):
    """Run a small connection diagnostic against the open ODBC connection."""
    sql = _connection_test_sql(database_connection)
    items, rows = database_connection.query(sql, max_rows=1)
    results = [
        _result("connection query returned one row", True, len(rows) == 1),
        _result("connection query returned one column", True, len(items) == 1),
    ]
    if items:
        results.append(_result("connection integer metadata", "i", items[0]["type"]))
    if rows and rows[0]:
        results.append(_result("connection integer value", 1, rows[0][0]))
    return sql, results


def diagnostics_passed(results):
    return all(item["passed"] for item in results)


def _connection_test_sql(database_connection):
    dbms_name = ""
    try:
        dbms_name = database_connection.dbms_name().lower()
    except Exception:
        pass
    if "oracle" in dbms_name:
        return "select 1 as openodbc_integer from dual"
    return "select 1 as openodbc_integer"


def _result(label, expected, actual):
    return {
        "label": label,
        "expected": expected,
        "actual": actual,
        "passed": expected == actual,
    }
