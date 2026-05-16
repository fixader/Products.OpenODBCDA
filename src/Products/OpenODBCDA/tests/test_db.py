# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Tests for DB-API result handling."""

from datetime import date
from datetime import datetime
from datetime import time
import unittest

from DateTime.DateTime import DateTime as ZopeDateTime

from Products.OpenODBCDA.db import ResultOptions
from Products.OpenODBCDA.db import _query


class FakeCursor:
    def __init__(self, description=None, rows=None):
        self.description = description or (
            ("", int, None, None, None, None, None),
            ("Named", str, None, None, None, None, None),
        )
        self.rows = rows or [(1, "value")]

    def execute(self, sql):
        self.sql = sql

    def fetchmany(self, max_rows):
        return self.rows[:max_rows]

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor=None):
        self.cursor_obj = cursor or FakeCursor()

    def cursor(self):
        return self.cursor_obj


class QueryTests(unittest.TestCase):
    def test_empty_column_names_get_stable_fallbacks(self):
        items, rows = _query(FakeConnection(), "select 1")

        self.assertEqual(items[0]["name"], "Column1")
        self.assertEqual(items[1]["name"], "Named")
        self.assertEqual(rows, [(1, "value")])

    def test_zero_max_rows_fetches_all_rows(self):
        cursor = FakeCursor(rows=[(1, "first"), (2, "second"), (3, "third")])

        _items, rows = _query(FakeConnection(cursor), "select many", max_rows=0)

        self.assertEqual(rows, [(1, "first"), (2, "second"), (3, "third")])

    def test_nulls_can_be_returned_as_empty_strings(self):
        cursor = FakeCursor(
            description=(("Nullable", str, None, None, None, None, True),),
            rows=[(None,)],
        )

        _items, rows = _query(
            FakeConnection(cursor),
            "select nullable_col",
            result_options=ResultOptions(null_as_empty_string=True),
        )

        self.assertEqual(rows, [("",)])

    def test_nulls_are_none_by_default(self):
        cursor = FakeCursor(
            description=(("Nullable", str, None, None, None, None, True),),
            rows=[(None,)],
        )

        _items, rows = _query(FakeConnection(cursor), "select nullable_col")

        self.assertEqual(rows, [(None,)])

    def test_time_values_can_be_returned_as_strings(self):
        cursor = FakeCursor(
            description=(("TimeValue", time, None, None, None, None, True),),
            rows=[(time(12, 30, 5),)],
        )

        _items, rows = _query(
            FakeConnection(cursor),
            "select time_col",
            result_options=ResultOptions(time_as_string=True),
        )

        self.assertEqual(rows, [("12:30:05",)])

    def test_date_time_values_are_python_objects_by_default(self):
        cursor = FakeCursor(
            description=(
                ("DateValue", date, None, None, None, None, True),
                ("DateTimeValue", datetime, None, None, None, None, True),
            ),
            rows=[(date(2026, 5, 16), datetime(2026, 5, 16, 12, 30, 5))],
        )

        _items, rows = _query(FakeConnection(cursor), "select date_cols")

        self.assertIs(type(rows[0][0]), date)
        self.assertIs(type(rows[0][1]), datetime)

    def test_date_time_values_can_be_returned_as_iso_strings(self):
        cursor = FakeCursor(
            description=(
                ("DateValue", date, None, None, None, None, True),
                ("DateTimeValue", datetime, None, None, None, None, True),
            ),
            rows=[(date(2026, 5, 16), datetime(2026, 5, 16, 12, 30, 5))],
        )

        _items, rows = _query(
            FakeConnection(cursor),
            "select date_cols",
            result_options=ResultOptions(date_time_format="iso"),
        )

        self.assertEqual(rows, [("2026-05-16", "2026-05-16T12:30:05")])

    def test_date_time_values_can_be_returned_as_zope_datetimes(self):
        cursor = FakeCursor(
            description=(
                ("DateValue", date, None, None, None, None, True),
                ("DateTimeValue", datetime, None, None, None, None, True),
            ),
            rows=[(date(2026, 5, 16), datetime(2026, 5, 16, 12, 30, 5))],
        )

        _items, rows = _query(
            FakeConnection(cursor),
            "select date_cols",
            result_options=ResultOptions(date_time_format="zope"),
        )

        self.assertIsInstance(rows[0][0], ZopeDateTime)
        self.assertIsInstance(rows[0][1], ZopeDateTime)

    def test_oracle_scale0_float_is_left_untouched_by_default(self):
        cursor = FakeCursor(
            description=(("OracleNumber", float, None, None, 10, 0, True),),
            rows=[(42.0,)],
        )

        _items, rows = _query(FakeConnection(cursor), "select number_col")

        self.assertEqual(rows, [(42.0,)])
        self.assertIs(type(rows[0][0]), float)

    def test_oracle_scale0_float_can_be_coerced_to_integer(self):
        cursor = FakeCursor(
            description=(("OracleNumber", float, None, None, 10, 0, True),),
            rows=[(42.0,)],
        )

        _items, rows = _query(
            FakeConnection(cursor),
            "select number_col",
            result_options=ResultOptions(leave_scale0_floats_untouched=False),
        )

        self.assertEqual(rows, [(42,)])
        self.assertIs(type(rows[0][0]), int)

    def test_oracle_scale0_nonintegral_float_is_never_coerced(self):
        cursor = FakeCursor(
            description=(("OracleNumber", float, None, None, 10, 0, True),),
            rows=[(42.5,)],
        )

        _items, rows = _query(
            FakeConnection(cursor),
            "select number_col",
            result_options=ResultOptions(leave_scale0_floats_untouched=False),
        )

        self.assertEqual(rows, [(42.5,)])


if __name__ == "__main__":
    unittest.main()
