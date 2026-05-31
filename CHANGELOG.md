# Changelog

## 0.1.4 - Referenced-by introspection

### Added

- Added `referenced_by(table, schema=None)` for incoming foreign key metadata:
  the tables and columns that reference the selected table.
- Added `primary_key_columns(table, schema=None)` as a small convenience helper
  for callers that only need the primary key column names.
- Documented the difference between `foreign_keys()` and `referenced_by()` for
  master/detail and child-table wizard use cases.
- Added unit tests for `foreign_keys()`, `primary_keys()`,
  `primary_key_columns()`, and `referenced_by()` metadata behavior.

## 0.1.3 - ODBC catalog introspection

### Added

- Added a small public introspection API for ODBC catalog metadata:
  `tables()`, `columns()`, `primary_keys()`, and `foreign_keys()`.
- Added simple convenience aliases `table_names()` and `column_names()` for
  wizard-style callers that only need names.
- Added `version()` on the Zope connector object and show the adapter version
  in the ZMI Status tab.
- Catalog rows are normalized into plain Python dictionaries instead of
  exposing raw pyodbc row objects.
- Added an internal default introspection provider based on pyodbc catalog
  methods, leaving room for later driver-specific providers without adding an
  ORM or SQL dialect layer.
- Added an Oracle column metadata fallback for Oracle ODBC installations where
  table and primary key catalog calls work but `SQLColumns` fails.
- Added unit tests for metadata normalization, catalog parameter forwarding,
  and cursor cleanup on both success and failure.
- Documented the introspection surface and driver support expectations in the
  README.

## 0.1.2 - Lost connection recovery

### Added

- ODBC connections that fail with a clear communication-link/lost-connection
  error are now discarded automatically. Read-only style SQL is reopened and
  retried once, helping Zope recover when a database server restarts or
  terminates a backend session while an idle connector still holds the old ODBC
  handle.

## 0.1.1 - Oracle connection string fix

### Fixed

- Structured Oracle connections now build `DBQ=...` instead of
  `DATABASE=...`.
- Oracle structured fields can now use either a TNS alias/full DBQ value in
  the database field, or Server/Port plus a service name.
- ZMI checkbox values sent as hidden-field plus checkbox pairs are now handled
  correctly, so `Use raw connection string exactly as entered` stays enabled
  after saving.

## 0.1.0 - Initial public testing release

Products.OpenODBCDA is an open ODBC Database Adapter for Zope 5 and Zope 6.

### Tested environments

- Zope 6.1 on Python 3.14.4, Ubuntu Server 26.04 LTS.
- Zope 5.8.3 on Python 3.8.10, Ubuntu Server 20.04 LTS.

### Tested ODBC targets

- SQLite 3 through the SQLite3 ODBC driver.
- PostgreSQL through the PostgreSQL Unicode ODBC driver.
- MariaDB through the MariaDB Unicode ODBC driver.
- Oracle 11g through the Oracle 19c ODBC driver.
- Microsoft SQL Server through ODBC Driver 18 for SQL Server.
- Older Microsoft SQL Server installations through FreeTDS.

### Added

- ZMI-addable `OpenODBC DB Connector`.
- ZRDB and Z SQL Methods compatibility.
- Raw and structured ODBC connection string configuration.
- ZMI Status, Properties, Test, and Diagnostics tabs.
- Per-connector connection pooling.
- Compatibility result options for legacy Zope applications.
- Date/time formatting options.
- `max_rows=0` support for unlimited result fetching.
- Product-local unit tests.
- Modern `pyproject.toml` packaging plus legacy `setup.py` support for buildout installations.
- Release artifacts for source distribution, wheel, and Python 3.8 egg based installations.

### Notes

- SQL dialects are passed through unchanged to the selected database.
- ODBC drivers must be installed and registered on the Zope host.
- Large result sets are materialized in memory by ZRDB and Z SQL Methods.
- This is an initial public testing release; validate in staging before production use.
