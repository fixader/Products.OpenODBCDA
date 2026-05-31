# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Tests for ODBC catalog metadata introspection."""

import unittest
from unittest.mock import patch

from Products.OpenODBCDA.connection import OpenODBCConnection
from Products.OpenODBCDA.db import ODBCIntrospectionProvider
from Products.OpenODBCDA.db import OpenODBCDatabaseConnection
from Products.OpenODBCDA.db import pyodbc
from Products.OpenODBCDA._version import __version__


class CatalogRow:
    def __init__(self, *values, **attrs):
        self.values = values
        for name, value in attrs.items():
            setattr(self, name, value)

    def __getitem__(self, index):
        return self.values[index]


class CatalogCursor:
    def __init__(self):
        self.closed = False
        self.calls = []
        self.raise_on_tables = False

    def tables(self, **kwargs):
        self.calls.append(("tables", kwargs))
        if self.raise_on_tables:
            raise RuntimeError("catalog failure")
        return [
            CatalogRow(
                "cat",
                "public",
                "customers",
                "TABLE",
                "customer table",
            )
        ]

    def columns(self, **kwargs):
        self.calls.append(("columns", kwargs))
        return [
            CatalogRow(
                "cat",
                "public",
                "customers",
                "id",
                4,
                "integer",
                10,
                None,
                0,
                10,
                0,
                "identifier",
                "nextval",
                None,
                None,
                None,
                1,
            )
        ]

    def primaryKeys(self, **kwargs):
        self.calls.append(("primaryKeys", kwargs))
        return [CatalogRow("cat", "public", "customers", "id", 1, "customers_pkey")]

    def foreignKeys(self, **kwargs):
        self.calls.append(("foreignKeys", kwargs))
        return [
            CatalogRow(
                "cat",
                "public",
                "customers",
                "id",
                "cat",
                "public",
                "orders",
                "customer_id",
                1,
                3,
                0,
                "orders_customer_id_fkey",
                "customers_pkey",
            )
        ]

    def close(self):
        self.closed = True


class CatalogConnection:
    def __init__(self, cursor=None):
        self.cursor_obj = cursor or CatalogCursor()
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def close(self):
        self.closed = True


class OracleColumnsFailingCursor(CatalogCursor):
    def columns(self, **kwargs):
        self.calls.append(("columns", kwargs))
        raise pyodbc.Error("oracle SQLColumns failure")


class OracleColumnsEmptyCursor(CatalogCursor):
    def columns(self, **kwargs):
        self.calls.append(("columns", kwargs))
        return []


class OracleFallbackCursor(CatalogCursor):
    def __init__(self):
        super().__init__()
        self.executed_sql = None
        self.executed_params = None

    def execute(self, sql, params):
        self.executed_sql = sql
        self.executed_params = params
        return [
            CatalogRow(
                table_schem="SOFTFLEXI",
                table_name="CUSTOMERS",
                column_name="ID",
                type_name="NUMBER",
                data_length=22,
                char_length=None,
                data_precision=10,
                data_scale=0,
                nullable="N",
                column_id=1,
                remarks="identifier",
            )
        ]


class OracleCatalogConnection:
    def __init__(self, catalog_cursor=None):
        self.catalog_cursor = catalog_cursor or OracleColumnsFailingCursor()
        self.fallback_cursor = OracleFallbackCursor()
        self.cursor_count = 0

    def cursor(self):
        self.cursor_count += 1
        if self.cursor_count == 1:
            return self.catalog_cursor
        return self.fallback_cursor

    def getinfo(self, info_type):
        return "Oracle"


class IntrospectionProviderTests(unittest.TestCase):
    def test_tables_normalizes_rows_and_passes_parameters(self):
        cursor = CatalogCursor()
        provider = ODBCIntrospectionProvider()

        result = provider.tables(
            CatalogConnection(cursor),
            schema="public",
            table="customers",
            table_type="TABLE",
        )

        self.assertEqual(
            result,
            [
                {
                    "catalog": "cat",
                    "schema": "public",
                    "name": "customers",
                    "type": "TABLE",
                    "remarks": "customer table",
                }
            ],
        )
        self.assertEqual(
            cursor.calls,
            [
                (
                    "tables",
                    {
                        "schema": "public",
                        "table": "customers",
                        "tableType": "TABLE",
                    },
                )
            ],
        )
        self.assertTrue(cursor.closed)

    def test_columns_normalizes_rows_and_passes_parameters(self):
        cursor = CatalogCursor()
        provider = ODBCIntrospectionProvider()

        result = provider.columns(
            CatalogConnection(cursor),
            table="customers",
            schema="public",
            column="id",
        )

        self.assertEqual(result[0]["catalog"], "cat")
        self.assertEqual(result[0]["schema"], "public")
        self.assertEqual(result[0]["table"], "customers")
        self.assertEqual(result[0]["name"], "id")
        self.assertEqual(result[0]["data_type"], 4)
        self.assertEqual(result[0]["type_name"], "integer")
        self.assertEqual(result[0]["size"], 10)
        self.assertEqual(result[0]["decimal_digits"], 0)
        self.assertEqual(result[0]["nullable"], 0)
        self.assertEqual(result[0]["ordinal"], 1)
        self.assertEqual(result[0]["default"], "nextval")
        self.assertEqual(result[0]["column_default"], "nextval")
        self.assertEqual(result[0]["remarks"], "identifier")
        self.assertEqual(
            cursor.calls,
            [
                (
                    "columns",
                    {"schema": "public", "table": "customers", "column": "id"},
                )
            ],
        )
        self.assertTrue(cursor.closed)

    def test_primary_keys_normalizes_rows_and_passes_parameters(self):
        cursor = CatalogCursor()
        provider = ODBCIntrospectionProvider()

        result = provider.primary_keys(
            CatalogConnection(cursor),
            table="customers",
            schema="public",
        )

        self.assertEqual(
            result,
            [
                {
                    "catalog": "cat",
                    "schema": "public",
                    "table": "customers",
                    "column": "id",
                    "key_sequence": 1,
                    "pk_name": "customers_pkey",
                }
            ],
        )
        self.assertEqual(
            cursor.calls,
            [("primaryKeys", {"schema": "public", "table": "customers"})],
        )
        self.assertTrue(cursor.closed)

    def test_foreign_keys_normalizes_rows_and_passes_parameters(self):
        cursor = CatalogCursor()
        provider = ODBCIntrospectionProvider()

        result = provider.foreign_keys(
            CatalogConnection(cursor),
            table="orders",
            schema="public",
        )

        self.assertEqual(
            result,
            [
                {
                    "pk_schema": "public",
                    "pk_table": "customers",
                    "pk_column": "id",
                    "fk_schema": "public",
                    "fk_table": "orders",
                    "fk_column": "customer_id",
                    "key_sequence": 1,
                    "fk_name": "orders_customer_id_fkey",
                    "pk_name": "customers_pkey",
                    "update_rule": 3,
                    "delete_rule": 0,
                }
            ],
        )
        self.assertEqual(
            cursor.calls,
            [("foreignKeys", {"foreignTable": "orders", "foreignSchema": "public"})],
        )
        self.assertTrue(cursor.closed)

    def test_referenced_by_normalizes_rows_and_passes_parameters(self):
        cursor = CatalogCursor()
        provider = ODBCIntrospectionProvider()

        result = provider.referenced_by(
            CatalogConnection(cursor),
            table="customers",
            schema="public",
        )

        self.assertEqual(result[0]["fk_table"], "orders")
        self.assertEqual(result[0]["fk_column"], "customer_id")
        self.assertEqual(result[0]["pk_table"], "customers")
        self.assertEqual(result[0]["pk_column"], "id")
        self.assertEqual(
            cursor.calls,
            [("foreignKeys", {"table": "customers", "schema": "public"})],
        )
        self.assertTrue(cursor.closed)

    def test_cursor_is_closed_when_catalog_call_fails(self):
        cursor = CatalogCursor()
        cursor.raise_on_tables = True
        provider = ODBCIntrospectionProvider()

        with self.assertRaises(RuntimeError):
            provider.tables(CatalogConnection(cursor))

        self.assertTrue(cursor.closed)

    def test_oracle_columns_fallback_normalizes_rows_when_sqlcolumns_fails(self):
        connection = OracleCatalogConnection()
        provider = ODBCIntrospectionProvider()

        result = provider.columns(connection, "CUSTOMERS", schema="SOFTFLEXI")

        self.assertTrue(connection.catalog_cursor.closed)
        self.assertTrue(connection.fallback_cursor.closed)
        self.assertEqual(connection.fallback_cursor.executed_params, ["CUSTOMERS", "SOFTFLEXI"])
        self.assertEqual(
            result,
            [
                {
                    "catalog": None,
                    "schema": "SOFTFLEXI",
                    "table": "CUSTOMERS",
                    "name": "ID",
                    "data_type": 2,
                    "type_name": "NUMBER",
                    "size": 10,
                    "decimal_digits": 0,
                    "nullable": 0,
                    "ordinal": 1,
                    "default": None,
                    "column_default": None,
                    "remarks": "identifier",
                }
            ],
        )

    def test_oracle_columns_fallback_runs_when_sqlcolumns_returns_no_rows(self):
        connection = OracleCatalogConnection(catalog_cursor=OracleColumnsEmptyCursor())
        provider = ODBCIntrospectionProvider()

        result = provider.columns(connection, "customers", schema="LAVAART")

        self.assertTrue(connection.catalog_cursor.closed)
        self.assertTrue(connection.fallback_cursor.closed)
        self.assertEqual(connection.fallback_cursor.executed_params, ["customers", "LAVAART"])
        self.assertEqual(result[0]["name"], "ID")


class DatabaseConnectionIntrospectionTests(unittest.TestCase):
    def test_zope_connection_exposes_adapter_version(self):
        connection = OpenODBCConnection("test", "Test", "dsn")

        self.assertEqual(connection.version(), __version__)

    def test_database_connection_exposes_catalog_methods(self):
        cursor = CatalogCursor()

        with patch(
            "Products.OpenODBCDA.db.pyodbc.connect",
            return_value=CatalogConnection(cursor),
        ):
            connection = OpenODBCDatabaseConnection("dsn")
            self.assertEqual(connection.tables()[0]["name"], "customers")
            self.assertEqual(
                connection.primary_key_columns("customers"),
                ["id"],
            )
            self.assertEqual(
                connection.referenced_by("customers")[0]["fk_table"],
                "orders",
            )

    def test_zope_connection_exposes_simple_name_aliases(self):
        cursor = CatalogCursor()

        with patch(
            "Products.OpenODBCDA.db.pyodbc.connect",
            return_value=CatalogConnection(cursor),
        ):
            connection = OpenODBCConnection("test", "Test", "dsn")
            self.assertEqual(connection.table_names(), ["customers"])
            self.assertEqual(connection.column_names("customers"), ["id"])
            self.assertEqual(connection.primary_key_columns("customers"), ["id"])
            self.assertEqual(
                connection.referenced_by("customers")[0]["fk_table"],
                "orders",
            )


if __name__ == "__main__":
    unittest.main()
