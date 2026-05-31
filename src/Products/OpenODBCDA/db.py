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

    def views(self, schema=None, view=None, include_definitions=False):
        connection = self._acquire()
        try:
            return self.introspection_provider.views(
                connection,
                schema=schema,
                view=view,
                include_definitions=include_definitions,
            )
        finally:
            self._release(connection)

    def view_definition(self, view, schema=None):
        connection = self._acquire()
        try:
            return self.introspection_provider.view_definition(
                connection,
                view=view,
                schema=schema,
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

    def primary_key_columns(self, table, schema=None):
        return [key["column"] for key in self.primary_keys(table, schema=schema)]

    def indexes(self, table, schema=None, unique=False, quick=True):
        connection = self._acquire()
        try:
            return self.introspection_provider.indexes(
                connection,
                table=table,
                schema=schema,
                unique=unique,
                quick=quick,
            )
        finally:
            self._release(connection)

    def row_id_columns(self, table, schema=None, nullable=True):
        connection = self._acquire()
        try:
            return self.introspection_provider.row_id_columns(
                connection,
                table=table,
                schema=schema,
                nullable=nullable,
            )
        finally:
            self._release(connection)

    def row_version_columns(self, table, schema=None, nullable=True):
        connection = self._acquire()
        try:
            return self.introspection_provider.row_version_columns(
                connection,
                table=table,
                schema=schema,
                nullable=nullable,
            )
        finally:
            self._release(connection)

    def type_info(self, data_type=None):
        connection = self._acquire()
        try:
            return self.introspection_provider.type_info(connection, data_type=data_type)
        finally:
            self._release(connection)

    def procedures(self, procedure=None, schema=None):
        connection = self._acquire()
        try:
            return self.introspection_provider.procedures(
                connection,
                procedure=procedure,
                schema=schema,
            )
        finally:
            self._release(connection)

    def procedure_columns(self, procedure, schema=None, column=None):
        connection = self._acquire()
        try:
            return self.introspection_provider.procedure_columns(
                connection,
                procedure=procedure,
                schema=schema,
                column=column,
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

    def referenced_by(self, table, schema=None):
        connection = self._acquire()
        try:
            return self.introspection_provider.referenced_by(
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

    def views(self, connection, schema=None, view=None, include_definitions=False):
        try:
            views = self.tables(
                connection,
                schema=schema,
                table=view,
                table_type="VIEW",
            )
        except Exception:
            return []
        if include_definitions:
            for item in views:
                item["definition"] = self.view_definition(
                    connection,
                    item.get("name"),
                    schema=item.get("schema") or schema,
                )
        return views

    def view_definition(self, connection, view, schema=None):
        if not view:
            return None
        dbms = _connection_dbms_name(connection)
        strategies = _view_definition_strategies(dbms, view, schema)
        for sql, params in strategies:
            cursor = connection.cursor()
            try:
                rows = cursor.execute(sql, params)
                row = rows.fetchone() if hasattr(rows, "fetchone") else None
                if row:
                    definition = _row_value(row, "definition", 0)
                    if definition:
                        return str(definition)
            except Exception:
                pass
            finally:
                cursor.close()
        return None

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

    def referenced_by(self, connection, table, schema=None):
        cursor = connection.cursor()
        try:
            rows = cursor.foreignKeys(table=table, schema=schema)
            return [_normalize_foreign_key_row(row) for row in rows]
        finally:
            cursor.close()

    def indexes(self, connection, table, schema=None, unique=False, quick=True):
        cursor = connection.cursor()
        try:
            rows = cursor.statistics(
                table=table,
                schema=schema,
                unique=unique,
                quick=quick,
            )
            return _normalize_index_rows(rows)
        except pyodbc.Error:
            return []
        finally:
            cursor.close()

    def row_id_columns(self, connection, table, schema=None, nullable=True):
        cursor = connection.cursor()
        try:
            rows = cursor.rowIdColumns(
                table=table,
                schema=schema,
                nullable=nullable,
            )
            return [_normalize_special_column_row(row) for row in rows]
        except pyodbc.Error:
            return []
        finally:
            cursor.close()

    def row_version_columns(self, connection, table, schema=None, nullable=True):
        cursor = connection.cursor()
        try:
            rows = cursor.rowVerColumns(
                table=table,
                schema=schema,
                nullable=nullable,
            )
            return [_normalize_special_column_row(row) for row in rows]
        except pyodbc.Error:
            return []
        finally:
            cursor.close()

    def type_info(self, connection, data_type=None):
        cursor = connection.cursor()
        try:
            data_type = _int_or_none(data_type)
            rows = cursor.getTypeInfo(data_type)
            return [_normalize_type_info_row(row) for row in rows]
        except (TypeError, pyodbc.Error):
            return []
        finally:
            cursor.close()

    def procedures(self, connection, procedure=None, schema=None):
        cursor = connection.cursor()
        try:
            rows = cursor.procedures(procedure=procedure, schema=schema)
            return [_normalize_procedure_row(row) for row in rows]
        except pyodbc.Error:
            return []
        finally:
            cursor.close()

    def procedure_columns(self, connection, procedure, schema=None, column=None):
        cursor = connection.cursor()
        try:
            method = getattr(cursor, "procedureColumns")
            try:
                rows = method(procedure=procedure, schema=schema, column=column)
            except TypeError:
                rows = method(procedure=procedure, schema=schema)
            columns = [_normalize_procedure_column_row(row) for row in rows]
            if column:
                wanted = str(column).lower()
                columns = [
                    item
                    for item in columns
                    if str(item.get("name") or "").lower() == wanted
                ]
            return columns
        except (AttributeError, TypeError, pyodbc.Error):
            return []
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


def _view_definition_strategies(dbms, view, schema=None):
    normalized = str(dbms or "").lower()
    strategies = []
    if "oracle" in normalized:
        where = ["upper(view_name) = upper(?)"]
        params = [view]
        if schema:
            where.append("upper(owner) = upper(?)")
            params.append(schema)
        strategies.append(
            (
                "select text as definition from all_views where "
                + " and ".join(where),
                params,
            )
        )
    elif "postgres" in normalized:
        strategies.append(_information_schema_view_query(view, schema))
    elif "sql server" in normalized or "microsoft" in normalized:
        strategies.append(_information_schema_view_query(view, schema))
    elif "mysql" in normalized or "mariadb" in normalized:
        strategies.append(_information_schema_view_query(view, schema))
    elif "sqlite" in normalized:
        strategies.append(
            (
                "select sql as definition from sqlite_master "
                "where type = 'view' and name = ?",
                [view],
            )
        )
    strategies.append(_information_schema_view_query(view, schema))
    return strategies


def _information_schema_view_query(view, schema=None):
    where = ["table_name = ?"]
    params = [view]
    if schema:
        where.append("table_schema = ?")
        params.append(schema)
    return (
        "select view_definition as definition from information_schema.views "
        "where " + " and ".join(where),
        params,
    )


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


def _normalize_index_rows(rows):
    indexes = []
    by_key = {}
    for row in rows:
        column_name = _row_value(row, "column_name", 8)
        index_name = _row_value(row, "index_name", 5)
        if not index_name and not column_name:
            continue
        key = (
            _row_value(row, "table_cat", 0),
            _row_value(row, "table_schem", 1),
            _row_value(row, "table_name", 2),
            _row_value(row, "index_qualifier", 4),
            index_name,
        )
        index = by_key.get(key)
        if index is None:
            non_unique = _row_value(row, "non_unique", 3)
            index = {
                "catalog": key[0],
                "schema": key[1],
                "table": key[2],
                "name": index_name,
                "qualifier": key[3],
                "unique": None if non_unique is None else not bool(non_unique),
                "non_unique": non_unique,
                "type": _row_value(row, "type", 6),
                "type_name": _index_type_name(_row_value(row, "type", 6)),
                "columns": [],
                "cardinality": _int_or_none(_row_value(row, "cardinality", 10)),
                "pages": _int_or_none(_row_value(row, "pages", 11)),
                "filter_condition": _row_value(row, "filter_condition", 12),
            }
            indexes.append(index)
            by_key[key] = index
        index["columns"].append(
            {
                "name": column_name,
                "ordinal": _int_or_none(_row_value(row, "ordinal_position", 7)),
                "sort": _row_value(row, "asc_or_desc", 9),
            }
        )
        for field, column_index in (
            ("cardinality", 10),
            ("pages", 11),
            ("filter_condition", 12),
        ):
            if index[field] is None:
                value = _row_value(row, field, column_index)
                if field in {"cardinality", "pages"}:
                    value = _int_or_none(value)
                index[field] = value
    for index in indexes:
        index["columns"].sort(key=lambda item: item.get("ordinal") or 0)
        index["summary"] = index_summary(index)
        index["sql_preview"] = index_sql_preview(index)
    return indexes


def _normalize_special_column_row(row):
    scope = _row_value(row, "scope", 0)
    pseudo_column = _row_value(row, "pseudo_column", 7)
    return {
        "scope": _int_or_none(scope),
        "scope_name": _special_column_scope_name(scope),
        "name": _row_value(row, "column_name", 1),
        "data_type": _int_or_none(_row_value(row, "data_type", 2)),
        "type_name": _row_value(row, "type_name", 3),
        "size": _int_or_none(_row_value(row, "column_size", 4)),
        "decimal_digits": _int_or_none(_row_value(row, "decimal_digits", 6)),
        "pseudo_column": _int_or_none(pseudo_column),
        "pseudo_column_name": _pseudo_column_name(pseudo_column),
    }


def _normalize_type_info_row(row):
    return {
        "type_name": _row_value(row, "type_name", 0),
        "data_type": _int_or_none(_row_value(row, "data_type", 1)),
        "size": _int_or_none(_row_value(row, "column_size", 2)),
        "literal_prefix": _row_value(row, "literal_prefix", 3),
        "literal_suffix": _row_value(row, "literal_suffix", 4),
        "create_params": _row_value(row, "create_params", 5),
        "nullable": _int_or_none(_row_value(row, "nullable", 6)),
        "case_sensitive": _row_value(row, "case_sensitive", 7),
        "searchable": _int_or_none(_row_value(row, "searchable", 8)),
        "unsigned": _row_value(row, "unsigned_attribute", 9),
        "fixed_precision_scale": _row_value(row, "fixed_prec_scale", 10),
        "auto_unique": _row_value(row, "auto_unique_value", 11),
        "local_type_name": _row_value(row, "local_type_name", 12),
        "minimum_scale": _int_or_none(_row_value(row, "minimum_scale", 13)),
        "maximum_scale": _int_or_none(_row_value(row, "maximum_scale", 14)),
        "sql_data_type": _int_or_none(_row_value(row, "sql_data_type", 15)),
        "sql_datetime_sub": _int_or_none(_row_value(row, "sql_datetime_sub", 16)),
        "num_prec_radix": _int_or_none(_row_value(row, "num_prec_radix", 17)),
        "interval_precision": _int_or_none(_row_value(row, "interval_precision", 18)),
    }


def _normalize_procedure_row(row):
    procedure = {
        "catalog": _row_value(row, "procedure_cat", 0),
        "schema": _row_value(row, "procedure_schem", 1),
        "name": _row_value(row, "procedure_name", 2),
        "num_input_params": _int_or_none(_row_value(row, "num_input_params", 3)),
        "num_output_params": _int_or_none(_row_value(row, "num_output_params", 4)),
        "num_result_sets": _int_or_none(_row_value(row, "num_result_sets", 5)),
        "remarks": _row_value(row, "remarks", 6),
        "procedure_type": _int_or_none(_row_value(row, "procedure_type", 7)),
    }
    procedure["procedure_type_name"] = _procedure_type_name(
        procedure["procedure_type"]
    )
    procedure["summary"] = procedure_summary(procedure)
    procedure["call_preview"] = procedure_call_preview(procedure)
    return procedure


def _normalize_procedure_column_row(row):
    column_type = _row_value(row, "column_type", 4)
    return {
        "catalog": _row_value(row, "procedure_cat", 0),
        "schema": _row_value(row, "procedure_schem", 1),
        "procedure": _row_value(row, "procedure_name", 2),
        "name": _row_value(row, "column_name", 3),
        "column_type": _int_or_none(column_type),
        "column_type_name": _procedure_column_type_name(column_type),
        "data_type": _int_or_none(_row_value(row, "data_type", 5)),
        "type_name": _row_value(row, "type_name", 6),
        "size": _int_or_none(_row_value(row, "column_size", 7)),
        "decimal_digits": _int_or_none(_row_value(row, "decimal_digits", 9)),
        "nullable": _int_or_none(_row_value(row, "nullable", 11)),
        "ordinal": _int_or_none(_row_value(row, "ordinal_position", 17)),
        "default": _row_value(row, "column_def", 13),
        "column_default": _row_value(row, "column_def", 13),
        "remarks": _row_value(row, "remarks", 12),
    }


def index_summary(index):
    try:
        unique = "UNIQUE " if index.get("unique") else ""
        name = index.get("name") or "<unnamed>"
        table = index.get("table") or "<unknown table>"
        columns = _index_column_list(index, include_sort=False)
        return f"{unique}INDEX {name} on {table}({columns})"
    except Exception:
        return "INDEX <unavailable>"


def index_sql_preview(index):
    try:
        unique = "UNIQUE " if index.get("unique") else ""
        name = _identifier(index.get("name") or "unnamed_index")
        table = _identifier(index.get("table") or "unknown_table")
        columns = _index_column_list(index, include_sort=True)
        if not columns:
            return "/* index preview unavailable: no indexed columns reported */"
        return f"CREATE {unique}INDEX {name} ON {table} ({columns})"
    except Exception:
        return "/* index preview unavailable */"


def _index_column_list(index, include_sort=False):
    parts = []
    for column in index.get("columns") or []:
        name = column.get("name")
        if not name:
            continue
        part = _identifier(name)
        sort = str(column.get("sort") or "").upper()
        if include_sort and sort in {"A", "ASC"}:
            part = f"{part} ASC"
        elif include_sort and sort in {"D", "DESC"}:
            part = f"{part} DESC"
        parts.append(part)
    return ", ".join(parts)


def _identifier(value):
    return str(value or "").strip() or "<unnamed>"


def _index_type_name(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return {
        0: "table_statistic",
        1: "clustered",
        2: "hashed",
        3: "other",
    }.get(value)


def procedure_summary(procedure):
    try:
        kind = (procedure.get("procedure_type_name") or "PROCEDURE").upper()
        name = _qualified_name(procedure.get("schema"), procedure.get("name"))
        parts = []
        for label, key in (
            ("inputs", "num_input_params"),
            ("outputs", "num_output_params"),
            ("result_sets", "num_result_sets"),
        ):
            value = procedure.get(key)
            if value is not None:
                parts.append(f"{label}={value}")
        suffix = f" ({', '.join(parts)})" if parts else ""
        return f"{kind} {name}{suffix}"
    except Exception:
        return "PROCEDURE <unavailable>"


def procedure_call_preview(procedure, columns=None):
    try:
        name = _qualified_name(procedure.get("schema"), procedure.get("name"))
        parameters = _procedure_preview_parameters(procedure, columns)
        return f"CALL {name}({parameters})"
    except Exception:
        return "/* procedure call preview unavailable */"


def _procedure_preview_parameters(procedure, columns=None):
    if columns:
        parameters = [
            column.get("name") or "?"
            for column in columns
            if column.get("column_type_name") in {"IN", "INOUT"}
        ]
        if parameters:
            return ", ".join(parameters)
    count = procedure.get("num_input_params")
    try:
        count = int(count)
    except (TypeError, ValueError):
        return "..."
    return ", ".join("?" for _ in range(max(count, 0)))


def _qualified_name(schema, name):
    name = _identifier(name or "unknown_procedure")
    if schema:
        return f"{_identifier(schema)}.{name}"
    return name


def _special_column_scope_name(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return {
        0: "current_row",
        1: "transaction",
        2: "session",
    }.get(value)


def _pseudo_column_name(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return {
        0: "unknown",
        1: "not_pseudo",
        2: "pseudo",
    }.get(value)


def _procedure_type_name(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return {
        0: "unknown",
        1: "procedure",
        2: "function",
    }.get(value)


def _procedure_column_type_name(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return {
        0: "UNKNOWN",
        1: "IN",
        2: "INOUT",
        3: "RESULT",
        4: "OUT",
        5: "RETURN",
    }.get(value)


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
    for info_type in (
        getattr(pyodbc, "SQL_DBMS_NAME", None),
        getattr(pyodbc, "SQL_DRIVER_NAME", None),
    ):
        if info_type is None:
            continue
        try:
            value = connection.getinfo(info_type)
        except (AttributeError, pyodbc.Error):
            continue
        if "oracle" in str(value).lower():
            return True
    return False


def _connection_dbms_name(connection):
    for info_type in (
        getattr(pyodbc, "SQL_DBMS_NAME", None),
        getattr(pyodbc, "SQL_DRIVER_NAME", None),
    ):
        if info_type is None:
            continue
        try:
            value = connection.getinfo(info_type)
        except (AttributeError, pyodbc.Error):
            continue
        if value:
            return str(value)
    return ""


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
    if isinstance(value, str) and not value.strip():
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
