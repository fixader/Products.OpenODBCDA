<!--
Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
SPDX-License-Identifier: MIT
The MIT license permits use, copying, distribution, and modification,
provided that copyright and permission notices are included.
See LICENSE and NOTICE for details.
Developed in collaboration with ChatGPT/Codex.
-->
# Products.OpenODBCDA for Zope 5 and Zope 6

An open ODBC Database Adapter for Zope 5 and Zope 6.

Products.OpenODBCDA adds an `OpenODBC DB Connector` object to the Zope
Management Interface (ZMI). The connection can then be used by Z SQL Methods
from `Products.ZSQLMethods`.

## Installation

Products.OpenODBCDA is intended to install like a normal Python package once it
has been published.

For Zope 6 or other pip-based installations:

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

Until the package is published to PyPI, install from a local checkout or from
the GitHub repository after it has been made public. See
[INSTALL_ZOPE.md](INSTALL_ZOPE.md) for detailed installation instructions,
ODBC driver setup, and tested database examples.

## Tested Targets

The main lab environment has been tested on:

- Ubuntu Server 26.04 LTS
- Python 3.14.4
- Zope 6.1
- Products.ZSQLMethods 5.1
- pyodbc 5.3.0

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
compatibility source filename such as `Products.OpenODBCDA-0.1.1.tar.gz`.

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
