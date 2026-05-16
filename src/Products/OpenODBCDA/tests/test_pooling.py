# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Tests for per-connector ODBC connection pooling."""

import unittest
from unittest.mock import patch

from Products.OpenODBCDA.connection import OpenODBCConnection
from Products.OpenODBCDA.db import OpenODBCDatabaseConnection
from Products.OpenODBCDA.db import normalize_pool_size


class FakeCursor:
    description = (("one", int, None, 10),)

    def execute(self, sql):
        self.sql = sql

    def fetchmany(self, max_rows):
        return [(1,)]

    def close(self):
        pass


class FakeConnection:
    closed = False

    def cursor(self):
        return FakeCursor()

    def close(self):
        self.closed = True

    def getinfo(self, code):
        return f"info-{code}"


class PoolingTests(unittest.TestCase):
    def test_pool_size_is_normalized(self):
        self.assertEqual(normalize_pool_size(None), 1)
        self.assertEqual(normalize_pool_size("bad"), 1)
        self.assertEqual(normalize_pool_size(0), 1)
        self.assertEqual(normalize_pool_size(3), 3)

    def test_database_connection_starts_with_one_physical_connection(self):
        created = []

        def connect(connection_string, autocommit=True):
            created.append(connection_string)
            return FakeConnection()

        with patch("Products.OpenODBCDA.db.pyodbc.connect", connect):
            pool = OpenODBCDatabaseConnection("dsn", pool_size=3)
            self.assertEqual(pool.current_pool_size(), 1)
            self.assertEqual(pool.idle_pool_size(), 1)
            self.assertEqual(created, ["dsn"])

    def test_query_reuses_idle_connection(self):
        created = []

        def connect(connection_string, autocommit=True):
            created.append(FakeConnection())
            return created[-1]

        with patch("Products.OpenODBCDA.db.pyodbc.connect", connect):
            pool = OpenODBCDatabaseConnection("dsn", pool_size=2)
            items, rows = pool.query("select 1")
            self.assertEqual(items[0]["type"], "i")
            self.assertEqual(rows, [(1,)])
            self.assertEqual(pool.current_pool_size(), 1)
            self.assertEqual(pool.idle_pool_size(), 1)
            self.assertEqual(len(created), 1)

    def test_pool_can_open_up_to_configured_size(self):
        created = []

        def connect(connection_string, autocommit=True):
            created.append(FakeConnection())
            return created[-1]

        with patch("Products.OpenODBCDA.db.pyodbc.connect", connect):
            pool = OpenODBCDatabaseConnection("dsn", pool_size=2)
            first = pool._acquire()
            second = pool._acquire()
            self.assertEqual(pool.current_pool_size(), 2)
            self.assertEqual(pool.in_use_pool_size(), 2)
            self.assertEqual(len(created), 2)
            pool._release(second)
            pool._release(first)

    def test_connection_object_uses_single_connection_unless_pool_enabled(self):
        connection = OpenODBCConnection("test", "Test", pool_size=5)
        self.assertEqual(connection.effective_pool_size(), 1)
        connection.pool_enabled = True
        self.assertEqual(connection.effective_pool_size(), 5)

    def test_connection_object_exposes_result_options(self):
        connection = OpenODBCConnection(
            "test",
            "Test",
            null_as_empty_string=True,
            time_as_string=True,
            leave_scale0_floats_untouched=False,
            date_time_format="zope",
        )

        options = connection.result_options()

        self.assertTrue(options.null_as_empty_string)
        self.assertTrue(options.time_as_string)
        self.assertFalse(options.leave_scale0_floats_untouched)
        self.assertEqual(options.date_time_format, "zope")


if __name__ == "__main__":
    unittest.main()
