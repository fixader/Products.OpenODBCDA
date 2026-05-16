# Changelog

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
