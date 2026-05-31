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

    def __init__(
        self,
        connection_string,
        pool_size=1,
        result_options=None,
        introspection_provider=None,
    ):
        self.connection_string = connection_string
        self.pool_size = normalize_pool_size(pool_size)
        self.result_options = result_options or ResultOptions()
        self.introspection_provider = (
            introspection_provider or ODBCIntrospectionProvider()
        )
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

    def tables(self, schema=None, table=None, table_type=None):
        connection = self._acquire()
        try:
            return self.introspection_provider.tables(
                connection,
                schema=schema,
                table=table,
                table_type=table_type,
            )
        finally:
            self._release(connection)

    def columns(self, table, schema=None, column=None):
        connection = self._acquire()
        try:
            return self.introspection_provider.columns(
                connection,
                table=table,
                schema=schema,
                column=column,
            )
        finally:
            self._release(connection)

    def primary_keys(self, table, schema=None):
        connection = self._acquire()
        try:
            return self.introspection_provider.primary_keys(
                connection,
                table=table,
                schema=schema,
            )
        finally:
            self._release(connection)

    def foreign_keys(self, table=None, schema=None):
        connection = self._acquire()
        try:
            return self.introspection_provider.foreign_keys(
                connection,
                table=table,
                schema=schema,
            )
        finally:
            self._release(connection)

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


class ODBCIntrospectionProvider:
    """Default ODBC catalog metadata provider."""

    def tables(self, connection, schema=None, table=None, table_type=None):
        cursor = connection.cursor()
        try:
            rows = cursor.tables(
                schema=schema,
                table=table,
                tableType=table_type,
            )
            return [_normalize_table_row(row) for row in rows]
        finally:
            cursor.close()

    def columns(self, connection, table, schema=None, column=None):
        cursor = connection.cursor()
        use_oracle_fallback = False
        try:
            rows = cursor.columns(
                schema=schema,
                table=table,
                column=column,
            )
            columns = [_normalize_column_row(row) for row in rows]
            if not columns and _is_oracle_connection(connection):
                use_oracle_fallback = True
            else:
                return columns
        except pyodbc.Error:
            if not _is_oracle_connection(connection):
                raise
            use_oracle_fallback = True
        finally:
            cursor.close()
        if use_oracle_fallback:
            return self._oracle_columns(connection, table, schema=schema, column=column)

    def _oracle_columns(self, connection, table, schema=None, column=None):
        cursor = connection.cursor()
        try:
            where = ["upper(c.table_name) = upper(?)"]
            params = [table]
            if schema:
                where.append("upper(c.owner) = upper(?)")
                params.append(schema)
            if column:
                where.append("upper(c.column_name) = upper(?)")
                params.append(column)
            sql = """
                select
                    c.owner as table_schem,
                    c.table_name,
                    c.column_name,
                    c.data_type as type_name,
                    c.data_length,
                    c.char_length,
                    c.data_precision,
                    c.data_scale,
                    c.nullable,
                    c.column_id,
                    cc.comments as remarks
                from all_tab_columns c
                left join all_col_comments cc
                    on cc.owner = c.owner
                    and cc.table_name = c.table_name
                    and cc.column_name = c.column_name
                where {where}
                order by c.owner, c.table_name, c.column_id
            """.format(where=" and ".join(where))
            rows = cursor.execute(sql, params)
            return [_normalize_oracle_column_row(row) for row in rows]
        finally:
            cursor.close()

    def primary_keys(self, connection, table, schema=None):
        cursor = connection.cursor()
        try:
            rows = cursor.primaryKeys(schema=schema, table=table)
            return [_normalize_primary_key_row(row) for row in rows]
        finally:
            cursor.close()

    def foreign_keys(self, connection, table=None, schema=None):
        cursor = connection.cursor()
        try:
            rows = cursor.foreignKeys(foreignTable=table, foreignSchema=schema)
            return [_normalize_foreign_key_row(row) for row in rows]
        finally:
            cursor.close()


def _normalize_table_row(row):
    return {
        "catalog": _row_value(row, "table_cat", 0),
        "schema": _row_value(row, "table_schem", 1),
        "name": _row_value(row, "table_name", 2),
        "type": _row_value(row, "table_type", 3),
        "remarks": _row_value(row, "remarks", 4),
    }


def _normalize_column_row(row):
    return {
        "catalog": _row_value(row, "table_cat", 0),
        "schema": _row_value(row, "table_schem", 1),
        "table": _row_value(row, "table_name", 2),
        "name": _row_value(row, "column_name", 3),
        "data_type": _row_value(row, "data_type", 4),
        "type_name": _row_value(row, "type_name", 5),
        "size": _row_value(row, "column_size", 6),
        "decimal_digits": _row_value(row, "decimal_digits", 8),
        "nullable": _row_value(row, "nullable", 10),
        "ordinal": _row_value(row, "ordinal_position", 16),
        "default": _row_value(row, "column_def", 12),
        "column_default": _row_value(row, "column_def", 12),
        "remarks": _row_value(row, "remarks", 11),
    }


def _normalize_oracle_column_row(row):
    type_name = _row_value(row, "type_name")
    precision = _row_value(row, "data_precision")
    char_length = _row_value(row, "char_length")
    data_length = _row_value(row, "data_length")
    size = precision or char_length or data_length
    return {
        "catalog": None,
        "schema": _row_value(row, "table_schem"),
        "table": _row_value(row, "table_name"),
        "name": _row_value(row, "column_name"),
        "data_type": _oracle_type_to_odbc_type(type_name),
        "type_name": type_name,
        "size": _int_or_none(size),
        "decimal_digits": _int_or_none(_row_value(row, "data_scale")),
        "nullable": 1 if _row_value(row, "nullable") == "Y" else 0,
        "ordinal": _int_or_none(_row_value(row, "column_id")),
        "default": None,
        "column_default": None,
        "remarks": _row_value(row, "remarks"),
    }


def _normalize_primary_key_row(row):
    return {
        "catalog": _row_value(row, "table_cat", 0),
        "schema": _row_value(row, "table_schem", 1),
        "table": _row_value(row, "table_name", 2),
        "column": _row_value(row, "column_name", 3),
        "key_sequence": _row_value(row, "key_seq", 4),
        "pk_name": _row_value(row, "pk_name", 5),
    }


def _normalize_foreign_key_row(row):
    return {
        "pk_schema": _row_value(row, "pktable_schem", 1),
        "pk_table": _row_value(row, "pktable_name", 2),
        "pk_column": _row_value(row, "pkcolumn_name", 3),
        "fk_schema": _row_value(row, "fktable_schem", 5),
        "fk_table": _row_value(row, "fktable_name", 6),
        "fk_column": _row_value(row, "fkcolumn_name", 7),
        "key_sequence": _row_value(row, "key_seq", 8),
        "fk_name": _row_value(row, "fk_name", 11),
        "pk_name": _row_value(row, "pk_name", 12),
        "update_rule": _row_value(row, "update_rule", 9),
        "delete_rule": _row_value(row, "delete_rule", 10),
    }


def _row_value(row, name, index=None, default=None):
    for candidate in (name, name.upper()):
        try:
            return getattr(row, candidate)
        except AttributeError:
            pass
    if isinstance(row, dict):
        for candidate in (name, name.upper()):
            if candidate in row:
                return row[candidate]
    if index is not None:
        try:
            return row[index]
        except (IndexError, KeyError, TypeError):
            pass
    return default


def _is_oracle_connection(connection):
    for info_type in (getattr(pyodbc, "SQL_DBMS_NAME", None), getattr(pyodbc, "SQL_DRIVER_NAME", None)):
        if info_type is None:
            continue
        try:
            value = connection.getinfo(info_type)
        except (AttributeError, pyodbc.Error):
            continue
        if "oracle" in str(value).lower():
            return True
    return False


def _oracle_type_to_odbc_type(type_name):
    normalized = str(type_name or "").upper()
    if normalized.startswith("TIMESTAMP"):
        return 93
    if normalized in {"CHAR", "VARCHAR2", "VARCHAR", "NCHAR", "NVARCHAR2"}:
        return 12
    if normalized in {"CLOB", "NCLOB", "LONG"}:
        return -1
    if normalized in {"NUMBER", "NUMERIC", "DECIMAL"}:
        return 2
    if normalized in {"BINARY_FLOAT", "FLOAT"}:
        return 6
    if normalized in {"BINARY_DOUBLE", "DOUBLE PRECISION"}:
        return 8
    if normalized == "DATE":
        return 93
    if normalized in {"RAW", "BLOB", "LONG RAW"}:
        return -3
    return None


def _int_or_none(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


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
