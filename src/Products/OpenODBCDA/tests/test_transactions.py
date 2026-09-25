# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Tests for explicit OpenODBCDA transaction support."""

import unittest
from threading import Barrier
from threading import Lock
from threading import Thread
from unittest.mock import patch
from unittest.mock import Mock

import pyodbc
import transaction

from Products.OpenODBCDA.connection import OpenODBCConnection
from Products.OpenODBCDA.db import NoActiveTransactionError
from Products.OpenODBCDA.db import OpenODBCDatabaseConnection
from Products.OpenODBCDA.db import OpenODBCTransactionError
from Products.OpenODBCDA.db import TransactionAlreadyActiveError
from Products.OpenODBCDA.db import TransactionFailedError
from Products.OpenODBCDA.db import TransactionsNotSupportedError


class FakeCursor:
    description = (("one", int, None, 10),)

    def __init__(self, connection, error=None):
        self.connection = connection
        self.error = error
        self.closed = False

    def execute(self, sql):
        self.connection.executed.append(sql)
        if self.error is not None:
            raise self.error

    def fetchmany(self, max_rows):
        return [(1,)]

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, capability=2, query_error=None):
        self.autocommit = True
        self.capability = capability
        self.query_error = query_error
        self.executed = []
        self.commit_count = 0
        self.rollback_count = 0
        self.closed = False

    def cursor(self):
        return FakeCursor(self, error=self.query_error)

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1

    def close(self):
        self.closed = True

    def getinfo(self, code):
        if code == pyodbc.SQL_TXN_CAPABLE:
            return self.capability
        return "test"


class TransactionTests(unittest.TestCase):
    def setUp(self):
        transaction.abort()

    def tearDown(self):
        transaction.abort()

    def make_pool(self, connection):
        patcher = patch(
            "Products.OpenODBCDA.db.pyodbc.connect",
            return_value=connection,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return OpenODBCDatabaseConnection("dsn", pool_size=1)

    def test_default_queries_remain_autocommit(self):
        connection = FakeConnection()
        pool = self.make_pool(connection)

        _items, rows = pool.query("select 1")

        self.assertEqual(rows, [(1,)])
        self.assertTrue(connection.autocommit)
        self.assertEqual(connection.commit_count, 0)
        self.assertEqual(connection.rollback_count, 0)

    def test_transaction_pins_connection_until_zope_commit(self):
        connection = FakeConnection()
        pool = self.make_pool(connection)

        pool.begin_transaction()
        pool.query("insert one")
        pool.query("insert two")
        pool.commit_transaction()

        self.assertFalse(connection.autocommit)
        self.assertEqual(connection.executed, ["insert one", "insert two"])
        self.assertEqual(connection.commit_count, 0)
        self.assertEqual(pool.active_transaction_count(), 1)
        self.assertEqual(pool.idle_pool_size(), 0)

        transaction.commit()

        self.assertEqual(connection.commit_count, 1)
        self.assertTrue(connection.autocommit)
        self.assertEqual(pool.active_transaction_count(), 0)
        self.assertEqual(pool.idle_pool_size(), 1)

    def test_explicit_rollback_is_immediate(self):
        connection = FakeConnection()
        pool = self.make_pool(connection)

        pool.begin_transaction()
        pool.query("insert one")
        pool.rollback_transaction()

        self.assertEqual(connection.rollback_count, 1)
        self.assertTrue(connection.autocommit)
        self.assertEqual(pool.active_transaction_count(), 0)
        self.assertEqual(pool.idle_pool_size(), 1)

    def test_zope_abort_rolls_back_commit_requested_transaction(self):
        connection = FakeConnection()
        pool = self.make_pool(connection)

        pool.begin_transaction()
        pool.query("insert one")
        pool.commit_transaction()
        transaction.abort()

        self.assertEqual(connection.commit_count, 0)
        self.assertEqual(connection.rollback_count, 1)
        self.assertTrue(connection.autocommit)
        self.assertEqual(pool.active_transaction_count(), 0)

    def test_forgotten_completion_fails_and_rolls_back(self):
        connection = FakeConnection()
        pool = self.make_pool(connection)

        pool.begin_transaction()
        pool.query("insert one")

        with self.assertRaises(OpenODBCTransactionError):
            transaction.commit()

        self.assertEqual(connection.commit_count, 0)
        self.assertEqual(connection.rollback_count, 1)
        self.assertEqual(pool.active_transaction_count(), 0)

    def test_query_error_marks_transaction_failed_and_prevents_commit(self):
        connection = FakeConnection(query_error=pyodbc.Error("42000", "bad SQL"))
        pool = self.make_pool(connection)

        pool.begin_transaction()
        with self.assertRaises(pyodbc.Error):
            pool.query("bad SQL")
        with self.assertRaises(TransactionFailedError):
            pool.commit_transaction()

        self.assertEqual(connection.commit_count, 0)
        self.assertEqual(connection.rollback_count, 1)
        self.assertEqual(pool.active_transaction_count(), 0)

    def test_lost_connection_is_not_retried_inside_transaction(self):
        error = pyodbc.Error("08S01", "connection lost")
        connection = FakeConnection(query_error=error)
        pool = self.make_pool(connection)

        pool.begin_transaction()
        with self.assertRaises(pyodbc.Error):
            pool.query("select 1")
        with self.assertRaises(TransactionFailedError):
            pool.commit_transaction()

        self.assertEqual(connection.executed, ["select 1"])
        self.assertTrue(connection.closed)
        self.assertEqual(pool.current_pool_size(), 0)

    def test_driver_can_report_transactions_unsupported(self):
        connection = FakeConnection(capability=0)
        pool = self.make_pool(connection)

        self.assertEqual(
            pool.transaction_capability(),
            {"supported": False, "code": 0, "name": "none"},
        )
        with self.assertRaises(TransactionsNotSupportedError):
            pool.begin_transaction()

        self.assertTrue(connection.autocommit)
        self.assertEqual(pool.active_transaction_count(), 0)
        self.assertEqual(pool.idle_pool_size(), 1)

    def test_nested_transaction_is_rejected(self):
        pool = self.make_pool(FakeConnection())

        pool.begin_transaction()
        with self.assertRaises(TransactionAlreadyActiveError):
            pool.begin_transaction()

    def test_concurrent_zope_transactions_use_separate_connections(self):
        connections = []
        connections_lock = Lock()

        def connect(connection_string, autocommit=True):
            connection = FakeConnection()
            with connections_lock:
                connections.append(connection)
            return connection

        errors = []
        started = Barrier(2)
        with patch("Products.OpenODBCDA.db.pyodbc.connect", connect):
            pool = OpenODBCDatabaseConnection("dsn", pool_size=2)

            def worker(sql):
                try:
                    transaction.abort()
                    pool.begin_transaction()
                    pool.query(sql)
                    started.wait()
                    pool.commit_transaction()
                    transaction.commit()
                except Exception as exc:
                    errors.append(exc)
                    transaction.abort()

            threads = [
                Thread(target=worker, args=("insert request_one",)),
                Thread(target=worker, args=("insert request_two",)),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(len(connections), 2)
        self.assertEqual(
            sorted(connection.executed for connection in connections),
            [["insert request_one"], ["insert request_two"]],
        )
        self.assertTrue(
            all(connection.commit_count == 1 for connection in connections)
        )
        self.assertEqual(pool.active_transaction_count(), 0)
        self.assertEqual(pool.idle_pool_size(), 2)

    def test_commit_and_rollback_require_active_transaction(self):
        pool = self.make_pool(FakeConnection())

        with self.assertRaises(NoActiveTransactionError):
            pool.commit_transaction()
        with self.assertRaises(NoActiveTransactionError):
            pool.rollback_transaction()

    def test_zope_connector_delegates_transaction_methods(self):
        database = Mock()
        connector = OpenODBCConnection("test", "Test")
        connector._v_database_connection = database

        connector.begin_transaction()
        connector.commit_transaction()
        connector.rollback_transaction()

        database.begin_transaction.assert_called_once_with()
        database.commit_transaction.assert_called_once_with()
        database.rollback_transaction.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
