# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Small pyodbc-backed DB-API wrapper for ZRDB."""

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from threading import Condition

import pyodbc
from DateTime.DateTime import DateTime as ZopeDateTime

from .types import zrdb_type_for_column


@dataclass(frozen=True)
class ResultOptions:
    """Compatibility options applied to DB-API result rows."""

    null_as_empty_string: bool = False
    time_as_string: bool = False
    leave_scale0_floats_untouched: bool = True
    date_time_format: str = "python"


class OpenODBCDatabaseConnection:
    """ODBC connection pool used by the persistent Zope object."""

    def __init__(self, connection_string, pool_size=1, result_options=None):
        self.connection_string = connection_string
        self.pool_size = normalize_pool_size(pool_size)
        self.result_options = result_options or ResultOptions()
        self._condition = Condition()
        self._idle = []
        self._opened = 0
        self._closed = False
        self._idle.append(self._connect())
        self._opened = 1

    def close(self):
        with self._condition:
            self._closed = True
            connections = self._idle
            self._idle = []
            self._condition.notify_all()
        for connection in connections:
            _close_connection(connection)

    def info(self):
        connection = self._acquire()
        try:
            return _connection_info(connection)
        finally:
            self._release(connection)

    def dbms_name(self):
        connection = self._acquire()
        try:
            return connection.getinfo(pyodbc.SQL_DBMS_NAME)
        except pyodbc.Error:
            return ""
        finally:
            self._release(connection)

    def query(self, sql, max_rows=999999):
        for attempt in range(2):
            connection = self._acquire()
            discard = False
            try:
                return _query(
                    connection,
                    sql,
                    max_rows=max_rows,
                    result_options=self.result_options,
                )
            except pyodbc.Error as exc:
                discard = _is_connection_lost_error(exc)
                if discard and attempt == 0 and _is_retryable_sql(sql):
                    continue
                raise
            finally:
                self._release(connection, discard=discard)

    def current_pool_size(self):
        with self._condition:
            return self._opened

    def idle_pool_size(self):
        with self._condition:
            return len(self._idle)

    def in_use_pool_size(self):
        with self._condition:
            return self._opened - len(self._idle)

    def _connect(self):
        return pyodbc.connect(self.connection_string, autocommit=True)

    def _acquire(self):
        with self._condition:
            while True:
                if self._closed:
                    raise RuntimeError("ODBC connection pool is closed")
                if self._idle:
                    return self._idle.pop()
                if self._opened < self.pool_size:
                    self._opened += 1
                    break
                self._condition.wait()
        try:
            return self._connect()
        except Exception:
            with self._condition:
                self._opened -= 1
                self._condition.notify()
            raise

    def _release(self, connection, discard=False):
        with self._condition:
            if self._closed or discard:
                self._opened -= 1
                close_connection = True
            else:
                self._idle.append(connection)
                close_connection = False
            self._condition.notify()
        if close_connection:
            _close_connection(connection)


def normalize_pool_size(pool_size):
    try:
        pool_size = int(pool_size)
    except (TypeError, ValueError):
        pool_size = 1
    return max(pool_size, 1)


def _connection_info(connection):
    parts = []
    for label, code in (
        ("DBMS", pyodbc.SQL_DBMS_NAME),
        ("DBMS version", pyodbc.SQL_DBMS_VER),
        ("Driver", pyodbc.SQL_DRIVER_NAME),
        ("Driver version", pyodbc.SQL_DRIVER_VER),
    ):
        try:
            value = connection.getinfo(code)
        except pyodbc.Error:
            value = "unknown"
        parts.append(f"{label}: {value}")
    return "; ".join(parts)


def _query(connection, sql, max_rows=999999, result_options=None):
    result_options = result_options or ResultOptions()
    cursor = connection.cursor()
    try:
        cursor.execute(sql)
        if cursor.description is None:
            return [], []

        rows = [
            _format_row(row, cursor.description, result_options)
            for row in _fetch_rows(cursor, max_rows)
        ]
        column_values = list(zip(*rows)) if rows else []
        items = [
            {
                "name": _column_name(column, index),
                "type": zrdb_type_for_column(
                    column,
                    column_values[index] if index < len(column_values) else (),
                ),
                "width": _column_width(column),
            }
            for index, column in enumerate(cursor.description)
        ]
        return items, [tuple(row) for row in rows]
    finally:
        cursor.close()


def _close_connection(connection):
    try:
        connection.close()
    except pyodbc.Error:
        pass


def _is_connection_lost_error(exc):
    text = " ".join(str(arg) for arg in getattr(exc, "args", ()) or (exc,))
    text_lower = text.lower()
    lost_phrases = (
        "08s01",
        "communication link failure",
        "connection lost",
        "connection is closed",
        "connection object is gone",
        "server closed the connection",
        "terminating connection due to administrator command",
        "sqlserverconnection terminated",
    )
    return any(phrase in text_lower for phrase in lost_phrases)


def _is_retryable_sql(sql):
    first_word = _first_sql_word(sql)
    return first_word in {"select", "with", "show", "explain", "values"}


def _first_sql_word(sql):
    sql = str(sql or "").lstrip()
    while True:
        if sql.startswith("--"):
            _, separator, sql = sql.partition("\n")
            if not separator:
                return ""
            sql = sql.lstrip()
            continue
        if sql.startswith("/*"):
            _, separator, sql = sql.partition("*/")
            if not separator:
                return ""
            sql = sql.lstrip()
            continue
        break
    return sql.split(None, 1)[0].lower() if sql else ""


def _fetch_rows(cursor, max_rows):
    try:
        max_rows = int(max_rows)
    except (TypeError, ValueError):
        max_rows = 999999
    if max_rows <= 0:
        return cursor.fetchall()
    return cursor.fetchmany(max_rows)


def _column_width(column):
    for value in (column[2], column[3]):
        if isinstance(value, int) and value > 0:
            return value
    return 30


def _column_name(column, index):
    name = column[0]
    if name:
        return name
    return f"Column{index + 1}"


def _format_row(row, description, result_options):
    return tuple(
        _format_value(value, description[index], result_options)
        for index, value in enumerate(row)
    )


def _format_value(value, column, result_options):
    if value is None and result_options.null_as_empty_string:
        return ""
    if isinstance(value, time) and result_options.time_as_string:
        return value.isoformat()
    if isinstance(value, (date, datetime)):
        return _format_date_time_value(value, result_options.date_time_format)
    if (
        isinstance(value, float)
        and not result_options.leave_scale0_floats_untouched
        and _column_scale(column) == 0
        and value.is_integer()
    ):
        return int(value)
    return value


def _column_scale(column):
    if len(column) > 5 and isinstance(column[5], int):
        return column[5]
    return None


def _format_date_time_value(value, date_time_format):
    if date_time_format == "iso":
        return value.isoformat()
    if date_time_format == "zope":
        if isinstance(value, datetime):
            return ZopeDateTime(value)
        return ZopeDateTime(datetime.combine(value, time.min))
    return value


def available_odbc_drivers():
    return pyodbc.drivers()
