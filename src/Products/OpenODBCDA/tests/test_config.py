# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Tests for ODBC connection string configuration."""

import unittest

from Products.OpenODBCDA.config import build_connection_string
from Products.OpenODBCDA.config import build_oracle_dbq
from Products.OpenODBCDA.config import parse_connection_string
from Products.OpenODBCDA.config import truthy


class ConnectionStringTests(unittest.TestCase):
    def test_non_oracle_structured_fields_use_database(self):
        connection_string = build_connection_string(
            driver="PostgreSQL Unicode",
            server="db.example.com",
            port="5432",
            database="mydb",
            username="myuser",
            password="secret",
        )

        self.assertEqual(
            connection_string,
            "DRIVER={PostgreSQL Unicode};SERVER=db.example.com;PORT=5432;"
            "DATABASE=mydb;UID=myuser;PWD=secret",
        )

    def test_oracle_structured_fields_use_dbq_not_database(self):
        connection_string = build_connection_string(
            driver="Oracle 19c ODBC driver",
            server="oracle.example.com",
            port="1521",
            database="orcl",
            username="myuser",
            password="secret",
        )

        self.assertEqual(
            connection_string,
            "DRIVER={Oracle 19c ODBC driver};DBQ=oracle.example.com:1521/orcl;"
            "UID=myuser;PWD=secret",
        )

    def test_oracle_database_without_server_is_tns_alias_or_full_dbq(self):
        self.assertEqual(
            build_connection_string(
                driver="Oracle 19c ODBC driver",
                database="ORCL",
                username="myuser",
                password="secret",
            ),
            "DRIVER={Oracle 19c ODBC driver};DBQ=ORCL;UID=myuser;PWD=secret",
        )
        self.assertEqual(
            build_connection_string(
                driver="Oracle 19c ODBC driver",
                database="oracle.example.com:1521/orcl",
            ),
            "DRIVER={Oracle 19c ODBC driver};DBQ=oracle.example.com:1521/orcl",
        )

    def test_oracle_dbq_parser_populates_database_field(self):
        parsed = parse_connection_string(
            "DRIVER={Oracle 19c ODBC driver};DBQ=ORCL;UID=myuser;PWD=secret"
        )

        self.assertEqual(parsed["driver"], "Oracle 19c ODBC driver")
        self.assertEqual(parsed["database"], "ORCL")
        self.assertEqual(parsed["username"], "myuser")
        self.assertEqual(parsed["password"], "secret")

    def test_build_oracle_dbq(self):
        self.assertEqual(build_oracle_dbq(database="ORCL"), "ORCL")
        self.assertEqual(
            build_oracle_dbq(server="oracle.example.com", port="1521", database="orcl"),
            "oracle.example.com:1521/orcl",
        )
        self.assertEqual(
            build_oracle_dbq(server="oracle.example.com", database="orcl"),
            "oracle.example.com/orcl",
        )

    def test_truthy_handles_hidden_field_and_checkbox_values(self):
        self.assertFalse(truthy("0"))
        self.assertTrue(truthy("1"))
        self.assertTrue(truthy(["0", "1"]))
        self.assertTrue(truthy(("0", "on")))
        self.assertFalse(truthy(["0", ""]))


if __name__ == "__main__":
    unittest.main()
