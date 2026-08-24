<!--
Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
SPDX-License-Identifier: MIT
The MIT license permits use, copying, distribution, and modification,
provided that copyright and permission notices are included.
See LICENSE and NOTICE for details.
Developed in collaboration with ChatGPT/Codex.
-->
# Products.OpenODBCDA for Zope 5, Zope 6 and Plone

An open ODBC Database Adapter for Zope 5, Zope 6 and Plone.

## Production Status

Products.OpenODBCDA is production-stable software. It is used daily across
three production servers without known adapter errors. One deployment serves
158 customer sites under sustained heavy load, with each site using its own
database connection.

Unlike the previous connector used in that deployment, Products.OpenODBCDA
does not impose a built-in adapter-wide 50-connection cap. Practical limits
still depend on the Zope deployment, operating system, ODBC driver, database
server, connection-pool settings, and available resources.

Products.OpenODBCDA adds an `OpenODBC DB Connector` object to the Zope
Management Interface (ZMI). The connection can then be used by Z SQL Methods
from `Products.ZSQLMethods`.

## Installation

Products.OpenODBCDA is published on PyPI and installs like a normal Python
package.

For Zope 6, Plone 6, or other pip-based installations:

```bash
python -m pip install Products.OpenODBCDA
```

For Zope 5 installations managed by `zc.buildout`, add the package to the Zope
instance eggs:

```ini
[Instance]
eggs =
    Products.OpenODBCDA
    pyodbc
```

Then run:

```bash
bin/buildout
bin/Instance restart
```

See [INSTALL_ZOPE.md](INSTALL_ZOPE.md) for detailed installation instructions,
ODBC driver setup, and tested database examples.

## Tested Targets

The main lab environment has been tested on:

- Ubuntu Server 26.04 LTS
- Python 3.14.4
- Zope 6.1
- Products.ZSQLMethods 5.1
- pyodbc 5.3.0

Additional verification has been done on:

- Python 3.13.15
- Zope 6.2
- Plone 6.2.1 with Classic UI on Python 3.14.4, using a ZMI-created
  `OpenODBC DB Connector` and `Z SQL Method` against PostgreSQL through ODBC

Products.OpenODBCDA is a Zope database adapter and does not depend on Plone
internals. Plone installations running on a supported Zope/Python platform are
expected to work in the same way, but Plone 6.2.1 Classic UI is the Plone
target explicitly verified so far.

The package has also been verified in an existing buildout-based Zope 5
installation:

- Ubuntu Server 20.04 LTS
- Python 3.8.10
- Zope 5.8.3
- Products.ZSQLMethods 3.15
- pyodbc 5.2.0
- PostgreSQL through `PostgreSQL Unicode`, including a 217087 row unlimited
  Z SQL Method test

The repository includes both `pyproject.toml` for modern editable installs and
`setup.py` for older `zc.buildout` `develop =` installs.

Tested ODBC targets include:

- SQLite 3 through `SQLite3`
- PostgreSQL through `PostgreSQL Unicode`
- MariaDB through `MariaDB Unicode`
- Oracle 11g through `Oracle 19c ODBC driver`
- Microsoft SQL Server 2022 through `ODBC Driver 18 for SQL Server`
- older Microsoft SQL Server through `FreeTDS`

Products.OpenODBCDA provides:

- register as an addable Zope product
- store an ODBC connection string
- connect through `pyodbc`
- provide a ZRDB-compatible `query()` method
- run `select 1` from the ZMI and Z SQL Methods
- map common ODBC result types to ZRDB metadata for numbers, dates, times,
  text, and null-capable columns
- expose normalized ODBC catalog metadata for table, column, primary key, and
  foreign key introspection
- optionally use a per-connector connection pool without a global adapter-level
  pool count limit

## Using The Adapter

1. Install Zope, `Products.ZSQLMethods`, pyodbc, and the ODBC driver for the
   database you need.
2. Restart Zope so the driver is visible to the running process.
3. In the ZMI, add `OpenODBC DB Connector`.
4. Use either the structured fields or a raw ODBC connection string.
5. Open the connection and run a small test query from the connection's Test tab.
6. Add a Z SQL Method and select the OpenODBCDA connection.

The connection object's Status tab lists the ODBC drivers reported by pyodbc.
If the driver is not listed there, fix the driver installation before debugging
the Zope object.

## Zope 5 Buildout

For released packages from PyPI, a Zope 5 buildout can use the normal egg name:

```ini
[Instance]
eggs =
    Products.OpenODBCDA
    pyodbc
```

For development before a PyPI release, keep a checkout inside the buildout,
register it as a develop package, and include both `Products.OpenODBCDA` and
`pyodbc` in the Zope instance eggs.

Example `buildout.cfg` fragment:

```ini
[buildout]
develop =
    src/Products.OpenODBCDA

[Instance]
eggs =
    Products.OpenODBCDA
    pyodbc
```

Then rerun buildout and restart the instance:

```bash
bin/buildout
bin/Instance restart
```

`setup.py` is intentionally kept in the repository for this use case. Without
it, older buildout develop installs may not recognize the package correctly.

## Release Artifacts

The project is packaged with both modern Python metadata (`pyproject.toml`) and
a compatibility `setup.py`.

Expected release artifacts are:

- source distribution (`.tar.gz`)
- wheel (`.whl`)
- optional legacy Python-version-specific egg (`.egg`) for older
  buildout-oriented Zope 5 environments

The preferred long-term installation path is PyPI. GitHub Releases can also
attach the built artifacts so administrators can download a specific version
directly.

Maintainer release steps are documented in
[MAINTAINER_RELEASE.md](MAINTAINER_RELEASE.md).

For local/offline Zope 5 buildout installs, prefer the source distribution over
a prebuilt egg. Buildout can build an egg for the Python version used by that
Zope installation. A prebuilt `.egg` is convenient only when it matches the
target Python version. For old `find-links` based buildouts, use the
compatibility source filename such as `Products.OpenODBCDA-0.1.2.tar.gz`.

Some older buildout/easy_install combinations may still fail when building from
a source distribution in `find-links`. In that case, use a prebuilt `.egg` that
matches the target Python version, or install from PyPI when available.

## SQL Dialects

OpenODBCDA sends SQL to the ODBC driver unchanged. It does not translate SQL
syntax between database engines.

Z SQL Methods should therefore use SQL supported by the selected target
database. For example, Oracle-specific SQL such as `NVL`, `SYSDATE`, `ROWNUM`,
or `DUAL` must be changed by the application author when moving the query to a
different database such as Microsoft SQL Server, PostgreSQL, MariaDB, or SQLite.

## ODBC Catalog Introspection

OpenODBCDA exposes a small ODBC catalog metadata surface for Zope products,
ZMI helpers, and wizard-style tools. This is not an ORM, not a SQL dialect
translator, and not a table abstraction layer. It is a thin normalized wrapper
around the ODBC catalog methods provided by pyodbc.

Available methods on an `OpenODBC DB Connector` are:

```python
connection.version()
connection.tables(schema=None, table=None, table_type=None)
connection.columns(table, schema=None, column=None)
connection.views(schema=None, view=None, include_definitions=False)
connection.view_definition(view, schema=None)
connection.primary_keys(table, schema=None)
connection.primary_key_columns(table, schema=None)
connection.indexes(table, schema=None, unique=False, quick=True)
connection.index_summary(index)
connection.index_sql_preview(index)
connection.row_id_columns(table, schema=None, nullable=True)
connection.row_version_columns(table, schema=None, nullable=True)
connection.type_info(data_type=None)
connection.procedures(procedure=None, schema=None)
connection.procedure_columns(procedure, schema=None, column=None)
connection.procedure_summary(procedure)
connection.procedure_call_preview(procedure, columns=None)
connection.foreign_keys(table=None, schema=None)
connection.referenced_by(table, schema=None)
```

`connection.version()` returns the installed Products.OpenODBCDA adapter
version. The same value is also shown in the connector's ZMI Status tab.

The methods return lists of plain Python dictionaries rather than raw pyodbc
rows. There are also two small convenience aliases:

```python
connection.table_names(schema=None, table=None, table_type=None)
connection.column_names(table, schema=None, column=None)
```

Example use from product code or a Zope Python Script:

```python
db = context.my_odbc_connection
schema = "MY_SCHEMA"

tables = db.tables(schema=schema, table_type="TABLE")
table_by_name = {
    table["name"].upper(): table
    for table in tables
}

for table in tables:
    print(table["schema"], table["name"], table["type"])

views = db.views(schema=schema)
for view in views:
    print(view["schema"], view["name"], view["type"])

if "CUSTOMERS" not in table_by_name:
    raise ValueError("CUSTOMERS was not found in schema %r" % schema)

table_name = table_by_name["CUSTOMERS"]["name"]

columns = db.columns(table_name, schema=schema)
for column in columns:
    print(column["ordinal"], column["name"], column["type_name"], column["nullable"])

primary_key_columns = db.primary_key_columns(table_name, schema=schema)
print("primary key columns: " + str(primary_key_columns))

indexes = db.indexes(table_name, schema=schema)
if len(indexes) > 0:
    for index in indexes:
        print(index["summary"])
        print(index["sql_preview"])
else:
    print("No indexes")

row_id_columns = db.row_id_columns(table_name, schema=schema)
if len(row_id_columns) > 0:
    print("best row id columns: " + str([column["name"] for column in row_id_columns]))
else:
    print("No best row id columns reported")

row_version_columns = db.row_version_columns(table_name, schema=schema)
if len(row_version_columns) > 0:
    print(
        "row version columns: "
        + str([column["name"] for column in row_version_columns])
    )
else:
    print("No row version columns reported")

foreign_keys = db.foreign_keys(table_name, schema=schema)
if len(foreign_keys) > 0:
    for key in foreign_keys:
        print(
            key["fk_table"],
            key["fk_column"],
            "->",
            key["pk_table"],
            key["pk_column"],
        )
else:
    print("No foreign keys")

referenced_by = db.referenced_by(table_name, schema=schema)
if len(referenced_by) > 0:
    for key in referenced_by:
        print(
            key["fk_table"],
            key["fk_column"],
            "references",
            key["pk_table"],
            key["pk_column"],
        )
else:
    print("No tables reference " + table_name)
```

For simple wizards, the name aliases are often enough:

```python
schema = "MY_SCHEMA"

for table_name in db.table_names(schema=schema, table_type="TABLE"):
    column_names = db.column_names(table_name, schema=schema)
    print(table_name, column_names)
```

The dictionary keys returned by OpenODBCDA are normalized, so callers can work
with a stable shape across databases. The actual metadata content still comes
from the selected ODBC driver and database. For example, schema names,
identifier casing, type names, remarks, and key metadata can differ between
SQLite, PostgreSQL, MariaDB/MySQL, Oracle, SQL Server, and FreeTDS.
Set `schema` to the schema name reported by your database and ODBC driver; for
example, PostgreSQL commonly uses `public`, while Oracle commonly reports
unquoted owner/schema names in uppercase.

Internally these call the ODBC catalog APIs:

- `cursor.tables(...)`
- `cursor.columns(...)`
- `cursor.primaryKeys(...)`
- `cursor.foreignKeys(...)`
- `cursor.statistics(...)`
- `cursor.rowIdColumns(...)`
- `cursor.rowVerColumns(...)`
- `cursor.getTypeInfo(...)`
- `cursor.procedures(...)`
- `cursor.procedureColumns(...)`

`foreign_keys(table, schema)` returns foreign keys owned by `table`: what this
table points to. `referenced_by(table, schema)` returns foreign keys in other
tables that point to `table`, which is useful for master/detail wizards and
"show child tables" style navigation.

`views(schema, view)` lists views using ODBC table metadata with
`table_type="VIEW"`. `view_definition(view, schema)` makes a best-effort,
read-only attempt to fetch the view SQL text from common database metadata
tables, such as `information_schema.views`, Oracle `all_views`, or SQLite
`sqlite_master`. `views(..., include_definitions=True)` includes that same
best-effort definition field for each view. View definitions are not a
portable ODBC catalog feature, so OpenODBCDA returns `None` or an empty list
when a driver or database cannot provide them. For the exact view text, use
the database's native tools and documentation.

`indexes(table, schema)` returns read-only ODBC index metadata, including
index names, uniqueness, indexed columns, sort direction where reported by the
driver, and optional statistics such as cardinality, pages, and filter
condition. Each returned index also includes `summary` and `sql_preview`
strings. `index_summary(index)` is a human-readable description.
`index_sql_preview(index)` is a generic ANSI-style preview for reading and
migration assistance only. It is not guaranteed to be executable on the source
or target database. Database-specific features such as clustered indexes,
tablespaces, operator classes, expression indexes, included columns, bitmap
indexes, partial indexes, storage parameters, and quoting rules are not
reconstructed. Use this preview as a starting point, then adapt it with your
database documentation, migration tooling, or local code assistant.

`row_id_columns(table, schema)` uses ODBC special-column metadata to ask the
driver for the best columns to identify a row when a formal primary key is not
available. `row_version_columns(table, schema)` asks for columns that change
when the row changes, where the driver can report such metadata. Some drivers
return no rows for one or both calls; OpenODBCDA returns an empty list in that
case.

`type_info(data_type)` reports the data types supported by the ODBC driver.
`procedures(procedure, schema)` reports stored procedures and functions where
the driver exposes them. `procedure_columns(procedure, schema, column)` reports
procedure parameters, return values, and result columns where the driver can
describe them. Many drivers only report parameters, and some report incomplete
or no result-column metadata.

Procedure summaries and call previews are intentionally conservative.
`procedure_summary(procedure)` returns a human-readable description.
`procedure_call_preview(procedure, columns)` returns a generic SQL-style call
preview for reading and migration assistance only. It is not guaranteed to be
valid for the source or target database. Stored procedure syntax, named
parameters, return values, packages, overloaded procedures, multiple result
sets, and output-parameter handling are database-specific. When OpenODBCDA
cannot make a useful preview, it returns an explicit "preview unavailable"
message instead of raising an error. Use database documentation, database-native
tools, migration tooling, or a local code assistant for the exact dialect.

The default implementation is intentionally small and lives behind an internal
introspection provider. Normal installations use the default pyodbc/ODBC
provider. The provider boundary is there as a practical extension point: if a
rare or old ODBC driver returns unusual catalog rows, incomplete key metadata,
or driver-specific values that need cleanup, a later version can add a small
driver-specific provider without changing the public Zope API or adding an ORM
or SQL dialect layer.

Oracle is the first practical example of this boundary. Some Oracle ODBC
installations can expose tables and primary keys through the standard ODBC
catalog calls while failing on `SQLColumns`. OpenODBCDA therefore keeps the
standard `cursor.columns(...)` call as the first attempt, but can fall back to
Oracle catalog views for column metadata when that specific catalog call fails.

ODBC catalog support varies between drivers. Table and column metadata is
usually available, while primary key and foreign key metadata can be incomplete
or missing on older drivers, lightweight drivers, file-based databases, or
databases where permissions hide catalog information.

The introspection surface has been designed for tested targets including
SQLite, PostgreSQL, MariaDB/MySQL, Oracle, Microsoft SQL Server, and SQL Server
through FreeTDS. Wizard products should still provide a manual fallback when
metadata is missing or incomplete.

OpenODBCDA still sends application SQL unchanged. Introspection helps discover
tables and columns; it does not make SQL portable between databases.

## Connection Examples

The examples below are intentionally generic. Replace host names, database
names, users, and passwords with values from your own environment.

### SQLite 3

SQLite uses a local database file. It does not use server, port, username, or
password fields.

Use a raw connection string:

```text
DRIVER={SQLite3};DATABASE=/path/to/database.db
```

Example test query:

```sql
select 1 as One
```

### PostgreSQL

PostgreSQL works well with structured fields:

```text
Driver: PostgreSQL Unicode
Server: db.example.com
Port: 5432
Database: mydb
User: myuser
Password: <password>
```

Equivalent raw connection string:

```text
DRIVER={PostgreSQL Unicode};SERVER=db.example.com;PORT=5432;DATABASE=mydb;UID=myuser;PWD=<password>
```

### MariaDB

MariaDB needs the MariaDB ODBC driver. SQLite's driver cannot connect to
MariaDB.

Structured fields:

```text
Driver: MariaDB Unicode
Server: mariadb.example.com
Port: 3306
Database: mydb
User: myuser
Password: <password>
```

Equivalent raw connection string:

```text
DRIVER={MariaDB Unicode};SERVER=mariadb.example.com;PORT=3306;DATABASE=mydb;UID=myuser;PWD=<password>
```

### Oracle

Oracle ODBC commonly uses `DBQ`, either as a TNS alias or as
`host:port/service`.

Raw connection string with a TNS alias:

```text
DRIVER={Oracle 19c ODBC driver};DBQ=ORCL;UID=myuser;PWD=<password>
```

Raw connection string without a TNS alias:

```text
DRIVER={Oracle 19c ODBC driver};DBQ=myoracleserver.mydomain.com:1521/orcl;UID=myuser;PWD=<password>
```

Structured Oracle fields also build `DBQ` automatically when the selected
driver name contains `Oracle`.

For a TNS alias, leave Server and Port empty:

```text
Driver: Oracle 19c ODBC driver
Database / service / DBQ: ORCL
User: myuser
Password: <password>
```

For a direct host/service connection:

```text
Driver: Oracle 19c ODBC driver
Server: myoracleserver.mydomain.com
Port: 1521
Database / service / DBQ: orcl
User: myuser
Password: <password>
```

If DNS is not available from the Zope server, use an IP address instead of the
host name.

Oracle is also where old Zope installations are most likely to depend on legacy
result formatting. See `Compatibility Result Options` on the connection's
Properties tab if old Z SQL Methods expect NULL values as empty strings or
scale 0 numeric values in a particular Python shape.

### Microsoft SQL Server

For modern SQL Server versions, use Microsoft's ODBC Driver 18.

The driver commonly expects the port as part of `SERVER`, separated by a comma:

```text
DRIVER={ODBC Driver 18 for SQL Server};SERVER=sqlserver.example.com,1433;DATABASE=mydb;UID=myuser;PWD=<password>;TrustServerCertificate=yes
```

`TrustServerCertificate=yes` is often useful for internal servers with private
certificates. If an old SQL Server fails with an SSL provider error such as
`unsupported protocol`, try FreeTDS instead or update the server TLS setup.

### Older SQL Server With FreeTDS

FreeTDS can connect to some older SQL Server installations that modern Microsoft
ODBC Driver 18 rejects because of old TLS/protocol behavior.

Use a raw connection string and tune `TDS_Version` for the target server:

```text
DRIVER={FreeTDS};SERVER=sqlserver.example.com;PORT=1433;DATABASE=mydb;UID=myuser;PWD=<password>;TDS_Version=7.0
```

In the lab, SQL Server 2022 worked with newer TDS versions, while an older SQL
Server target required `TDS_Version=7.0`.

## BLOB And CLOB Examples

The examples below are intentionally small and practical. They are not a
complete explanation of large object handling for each database. Use the
documentation for the database and ODBC driver you are working with as the
authoritative reference.

OpenODBCDA sends SQL through to the ODBC driver unchanged. That means binary
values used in `INSERT` statements must be written with the syntax expected by
the target database.

### SQLite 3 BLOB

```sql
CREATE TABLE openodbcda_lob_test (
    id INTEGER PRIMARY KEY,
    text_col TEXT,
    blob_col BLOB
);

INSERT INTO openodbcda_lob_test (id, text_col, blob_col)
VALUES (1, 'text value', X'000102FFFEFD');

SELECT id, text_col, blob_col
FROM openodbcda_lob_test;
```

### PostgreSQL `bytea`

```sql
CREATE TABLE openodbcda_lob_test (
    id integer PRIMARY KEY,
    text_col text,
    blob_col bytea
);

INSERT INTO openodbcda_lob_test (id, text_col, blob_col)
VALUES (1, 'text value', decode('000102fffefd', 'hex'));

SELECT id, text_col, blob_col
FROM openodbcda_lob_test;
```

### MariaDB `LONGTEXT` And `LONGBLOB`

```sql
CREATE TABLE openodbcda_lob_test (
    id INT PRIMARY KEY,
    text_col LONGTEXT,
    blob_col LONGBLOB
);

INSERT INTO openodbcda_lob_test (id, text_col, blob_col)
VALUES (1, 'text value', UNHEX('000102FFFEFD'));

SELECT id, text_col, blob_col
FROM openodbcda_lob_test;
```

### Microsoft SQL Server `NVARCHAR(MAX)` And `VARBINARY(MAX)`

```sql
CREATE TABLE dbo.openodbcda_lob_test (
    id INT PRIMARY KEY,
    text_col NVARCHAR(MAX),
    blob_col VARBINARY(MAX)
);

INSERT INTO dbo.openodbcda_lob_test (id, text_col, blob_col)
VALUES (
    1,
    N'text value',
    CONVERT(VARBINARY(MAX), '000102FFFEFD', 2)
);

SELECT id, text_col, blob_col
FROM dbo.openodbcda_lob_test;
```

### Oracle CLOB And BLOB

```sql
CREATE TABLE openodbcda_lob_test (
    id NUMBER PRIMARY KEY,
    text_col CLOB,
    blob_col BLOB
);

INSERT INTO openodbcda_lob_test (id, text_col, blob_col)
VALUES (
    1,
    TO_CLOB('text value'),
    TO_BLOB(HEXTORAW('000102FFFEFD'))
);

SELECT id, text_col, blob_col
FROM openodbcda_lob_test;
```

## Diagnostics And Pooling

Tests live inside the product package:

```powershell
python -m unittest discover -s src\Products\OpenODBCDA\tests -v
```

Connection objects also expose a `Diagnostics` tab in the ZMI. It runs internal
type-mapping checks and, when the connection is open, a small ODBC smoke test
through the active driver.

Connection pooling is configured per Zope connection object. The default is a
single physical connection. Larger pools should be used sparingly because many
Zope folders with their own connector objects can otherwise create many
database sessions.

If an idle ODBC handle has been killed by the database server, OpenODBCDA
discards that physical connection. For read-only style SQL, it opens a fresh
connection and retries once. This is mainly meant to cover database restarts or
administrator-terminated sessions, such as PostgreSQL `08S01`
communication-link failures. Write statements are not automatically retried,
because the database may have completed the write before the connection failed.

Z SQL Method `Maximum rows to retrieve` is honored by the adapter. Set it to
`0` only when you deliberately want no row limit; large results are materialized
in memory by ZRDB.

## Compatibility Result Options

Each OpenODBCDA connection can apply a small set of result-row transformations
after pyodbc has fetched rows:

- `Date/time result format`: keeps Python date/time objects by default, or
  converts date/datetime values to Zope `DateTime` objects or ISO strings.
- `Fetch TIME columns as strings`: converts Python `datetime.time` values to
  strings such as `12:30:05`.
- `Fetch NULL values as empty strings`: converts `None` values to `""`.
- `Leave scale 0 floats untouched`: keeps integral float values such as `42.0`
  as floats when ODBC column metadata says scale is `0`. This is enabled by
  default. When disabled, integral scale 0 floats are converted to Python
  integers.

These options are meant for compatibility with older Zope applications that
were written against older database adapters. New code should normally keep
NULL values as `None`.

This project is an independent open source implementation for Zope 5 and Zope
6. The codebase is written for Products.OpenODBCDA and is intended to be
distributed under the MIT License.
