<!--
Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
SPDX-License-Identifier: MIT
The MIT license permits use, copying, distribution, and modification,
provided that copyright and permission notices are included.
See LICENSE and NOTICE for details.
Developed in collaboration with ChatGPT/Codex.
-->
# Installing Products.OpenODBCDA on Zope 5 and Zope 6

These instructions describe the environments that have actually been tested for
the current development prototype. The broad driver lab is on Zope 6.1, and a
PostgreSQL-only compatibility install has also been verified on Zope 5.8.3.

## Tested Environment

Products.OpenODBCDA has been tested in the lab with:

- Operating system: Ubuntu Server 26.04 LTS
- Python: 3.14.4
- Zope: 6.1
- Products.ZSQLMethods: 5.1
- pyodbc: 5.3.0
- unixODBC: Ubuntu package
- SQLite ODBC driver: Ubuntu `libsqliteodbc` package
- PostgreSQL ODBC driver: Ubuntu `odbc-postgresql` package
- MariaDB ODBC driver: Ubuntu `odbc-mariadb` package, MariaDB Connector/ODBC 3.2.6
- Local MariaDB test target: MariaDB Server 11.8.6
- Oracle ODBC driver: Oracle Instant Client 19.30 Basic + ODBC
- Microsoft ODBC Driver 18 for SQL Server: 18.6.2.1
- FreeTDS ODBC driver: Ubuntu `tdsodbc` package, FreeTDS 1.5.5
- Local SQL Server test target: SQL Server 2022 Developer container

The working main lab Zope instance runs on:

```text
Zope 6.1
Python 3.14.4
Products.ZSQLMethods 5.1
pyodbc 5.3.0
```

An existing Zope 5 installation has also been verified with:

```text
Ubuntu Server 20.04 LTS
Zope 5.8.3
Python 3.8.10
Products.ZSQLMethods 3.15
pyodbc 5.2.0
PostgreSQL Unicode ODBC driver
```

That Zope 5 test used PostgreSQL only. The wider SQLite, PostgreSQL, MariaDB,
Oracle, Microsoft SQL Server, and FreeTDS driver matrix was tested on the Zope
6.1 lab.

Zope 5.14.2 was also tried on Python 3.14.4, but the WSGI instance did not
start cleanly in this lab.

The package metadata allows Python 3.8 and `Products.ZSQLMethods` 3.15 or
newer. The repository also includes a `setup.py` specifically so older
`zc.buildout` `develop =` installs can recognize the package.

## Required Zope Packages

`Products.OpenODBCDA` provides the database connection object. Zope's Z SQL
Method objects are provided by `Products.ZSQLMethods`.

For Zope 6 or other pip-based installations, the intended released install is:

```bash
python -m pip install Products.OpenODBCDA
```

The package depends on `Products.ZSQLMethods` and `pyodbc`, so pip will install
those Python packages if needed. The operating system ODBC driver for your
database must still be installed separately.

For the tested Zope 6.1 lab environment, the base Zope packages were installed
explicitly:

```bash
python -m pip install "Zope==6.1" "Products.ZSQLMethods==5.1" "pyodbc==5.3.0"
```

Without `Products.ZSQLMethods`, OpenODBCDA can still create and open an ODBC
connection object, but you will not have the normal ZMI Z SQL Method machinery
for running SQL methods through that connection.

For Zope 5 installations managed by `zc.buildout`, use the package as a normal
egg once it is published:

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

If installing from a local checkout before the package is published, use the
development buildout instructions later in this document.

If you have downloaded a source distribution artifact instead, place it in a
local directory and point buildout at that directory. Buildout will build an egg
for the Python version used by the Zope installation:

```ini
[buildout]
find-links =
    /home/zope/downloads

[Instance]
eggs =
    Products.OpenODBCDA
    pyodbc
```

The `pyodbc` package and the operating system ODBC driver still need to be
available for the target Python/Zope environment.

## Tested ODBC Drivers

The lab currently has these unixODBC drivers registered and visible from
`pyodbc.drivers()` inside the Zope virtual environment:

```text
SQLite
SQLite3
PostgreSQL ANSI
PostgreSQL Unicode
MariaDB Unicode
Oracle 19c ODBC driver
ODBC Driver 18 for SQL Server
FreeTDS
```

Registration notes:

- PostgreSQL, SQLite, and MariaDB were registered automatically by Ubuntu
  packages.
- Microsoft SQL Server was registered automatically by the `msodbcsql18`
  package.
- FreeTDS was registered automatically by the `tdsodbc` package.
- Oracle required running Oracle's `odbc_update_ini.sh` after unpacking Instant
  Client Basic and Instant Client ODBC into the same directory.

Always verify driver visibility both through unixODBC and through the Python
environment used by Zope:

```bash
odbcinst -q -d

python - <<'PY'
import pyodbc
print(pyodbc.drivers())
PY
```

## Install System Packages

On Ubuntu Server:

```bash
sudo apt update
sudo apt install -y \
  python3 \
  python3-venv \
  python3-dev \
  build-essential \
  unixodbc \
  unixodbc-dev \
  odbcinst \
  odbc-postgresql
```

For SQLite ODBC testing, also install:

```bash
sudo apt install -y libsqliteodbc sqlite3
```

For other databases, install the matching ODBC driver before creating the Zope
connection object. For example, Microsoft SQL Server and Oracle require their
own vendor ODBC drivers.

## SQLite ODBC Driver

SQLite is the smallest useful ODBC target for proving that unixODBC, pyodbc,
Zope, and OpenODBCDA are wired together correctly.

Install the driver and SQLite command-line tool:

```bash
sudo apt update
sudo apt install -y libsqliteodbc sqlite3
```

The Ubuntu package registers the drivers automatically with unixODBC.

Expected driver names:

```text
[SQLite]
[SQLite3]
```

Create a tiny test database:

```bash
sqlite3 /tmp/openodbc-sqlite.db \
  "create table if not exists sanity (id integer primary key, name text);
   insert or ignore into sanity (id, name) values (1, 'sqlite-ok');"
```

Reference OpenODBCDA connection string:

```text
DRIVER=SQLite3;DATABASE=/tmp/openodbc-sqlite.db
```

Verify with:

```sql
select id, name from sanity order by id
```

## MariaDB ODBC Driver

MariaDB uses its own ODBC driver. SQLite's ODBC driver cannot connect to a
MariaDB server.

Install a local MariaDB test server, command-line client, and ODBC driver:

```bash
sudo apt update
sudo apt install -y mariadb-server mariadb-client odbc-mariadb
sudo systemctl enable --now mariadb
```

The Ubuntu `odbc-mariadb` package registers the driver automatically.

Expected driver name:

```text
[MariaDB Unicode]
```

Create a small test database and user:

```bash
sudo mariadb <<'SQL'
CREATE DATABASE IF NOT EXISTS openodbc_mariadb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'openodbc'@'localhost' IDENTIFIED BY 'openodbc';
CREATE USER IF NOT EXISTS 'openodbc'@'127.0.0.1' IDENTIFIED BY 'openodbc';
GRANT ALL PRIVILEGES ON openodbc_mariadb.* TO 'openodbc'@'localhost';
GRANT ALL PRIVILEGES ON openodbc_mariadb.* TO 'openodbc'@'127.0.0.1';
FLUSH PRIVILEGES;

USE openodbc_mariadb;
CREATE TABLE IF NOT EXISTS sanity (
  id INT NOT NULL PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO sanity (id, name, amount)
VALUES (1, 'mariadb-ok', 84.25)
ON DUPLICATE KEY UPDATE name = VALUES(name), amount = VALUES(amount);
SQL
```

Reference OpenODBCDA connection string:

```text
DRIVER={MariaDB Unicode};SERVER=127.0.0.1;PORT=3306;DATABASE=openodbc_mariadb;UID=openodbc;PWD=openodbc
```

The lab leaves a reference connector in the Zope root:

```text
mariadb_local_odbc
```

It has been verified with:

```sql
select id, name, amount from sanity order by id
```

## Microsoft SQL Server ODBC Driver

For modern Microsoft SQL Server targets, install Microsoft's ODBC Driver 18 on
the Zope server.

Microsoft's package repository did not have a dedicated Ubuntu 26.04 repository
at the time this lab was built, so the lab used the nearest Microsoft Ubuntu
repository that installed cleanly:

```bash
sudo apt update
sudo apt install -y curl ca-certificates gnupg unixodbc unixodbc-dev apt-transport-https

curl -fsSLO https://packages.microsoft.com/config/ubuntu/25.10/packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
rm -f packages-microsoft-prod.deb

sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql18 mssql-tools18
```

Verify that unixODBC and pyodbc can see the driver:

```bash
odbcinst -q -d
python - <<'PY'
import pyodbc
print(pyodbc.drivers())
PY
```

Expected driver name:

```text
[ODBC Driver 18 for SQL Server]
```

Example OpenODBCDA connection string:

```text
DRIVER={ODBC Driver 18 for SQL Server};SERVER=sqlserver.example.com,1433;DATABASE=mydb;UID=<user>;PWD=<password>;TrustServerCertificate=yes
```

Microsoft ODBC Driver 18 enables encryption by default. For internal lab
servers with self-signed or private certificates, `TrustServerCertificate=yes`
is often enough. If the server is old and only supports obsolete TLS protocols,
the Microsoft driver may fail with an SSL provider error such as
`unsupported protocol`. In that case, use FreeTDS for the old server or update
the SQL Server TLS/certificate configuration.

### Local SQL Server Reference Target

The lab also runs a local SQL Server 2022 Developer container as a known-good
MSSQL target. This is useful for proving that OpenODBCDA, pyodbc, unixODBC, and
the Microsoft driver work independently of any old external server.

Install Docker:

```bash
sudo apt install -y docker.io
sudo systemctl enable --now docker
```

Start SQL Server 2022 on host port `11433`:

```bash
sudo docker run \
  -e ACCEPT_EULA=Y \
  -e MSSQL_SA_PASSWORD='<strong-lab-password>' \
  -e MSSQL_PID=Developer \
  -p 11433:1433 \
  --name openodbcda-sql2022 \
  --hostname openodbcda-sql2022 \
  -d mcr.microsoft.com/mssql/server:2022-latest
```

Wait for the server to start, then test with `sqlcmd`:

```bash
/opt/mssql-tools18/bin/sqlcmd \
  -S 127.0.0.1,11433 \
  -U sa \
  -P '<strong-lab-password>' \
  -C \
  -Q "select @@version"
```

Create a small test database:

```bash
/opt/mssql-tools18/bin/sqlcmd -S 127.0.0.1,11433 -U sa -P '<strong-lab-password>' -C -Q \
  "IF DB_ID('openodbc_mssql') IS NULL CREATE DATABASE openodbc_mssql"

/opt/mssql-tools18/bin/sqlcmd -S 127.0.0.1,11433 -U sa -P '<strong-lab-password>' -C -d openodbc_mssql -Q \
  "CREATE TABLE dbo.sanity (id int NOT NULL PRIMARY KEY, name nvarchar(50) NOT NULL, amount decimal(10,2) NOT NULL);
   INSERT INTO dbo.sanity (id, name, amount) VALUES (1, N'mssql-local-ok', 42.50);
   SELECT id, name, amount FROM dbo.sanity ORDER BY id;"
```

Reference OpenODBCDA connection string:

```text
DRIVER={ODBC Driver 18 for SQL Server};SERVER=127.0.0.1,11433;DATABASE=openodbc_mssql;UID=sa;PWD=<strong-lab-password>;TrustServerCertificate=yes
```

The lab leaves a reference connector in the Zope root:

```text
mssql_local_odbc
```

It has been verified with:

```sql
select id, name, amount from dbo.sanity order by id
```

## FreeTDS for Older SQL Server Targets

FreeTDS can be useful when Microsoft ODBC Driver 18 refuses to connect to an old
SQL Server because of obsolete TLS or protocol behavior.

Install the FreeTDS ODBC driver:

```bash
sudo apt update
sudo apt install -y freetds-bin freetds-common tdsodbc
```

Verify that unixODBC sees it:

```bash
odbcinst -q -d
```

Expected driver name:

```text
[FreeTDS]
```

Example OpenODBCDA connection string:

```text
DRIVER={FreeTDS};SERVER=sqlserver.example.com;PORT=1433;DATABASE=mydb;UID=<user>;PWD=<password>;TDS_Version=7.0
```

The `TDS_Version` value is server-dependent. In the lab:

- FreeTDS worked against the local SQL Server 2022 container with
  `TDS_Version=7.4`, `7.3`, and `7.2`.
- An older SQL Server 2008 target failed with `7.4`, `7.3`, `7.2`, and `7.1`,
  but worked with `TDS_Version=7.0`.

Reference OpenODBCDA connector left in the Zope root for the local container:

```text
mssql_local_freetds
```

The lab also verified an older SQL Server 2008 target with a separate FreeTDS
connector using `TDS_Version=7.0`. A simple smoke test worked:

```sql
select 1
```

Some drivers return an empty column name for expressions such as `select 1`.
OpenODBCDA maps empty column names to stable fallback names like `Column1`, so
Zope's result renderer can display the query instead of raising an error.

## Oracle ODBC Driver

To connect to an Oracle database from Products.OpenODBCDA, the Zope server must
have an Oracle-capable ODBC client driver installed locally. It does not matter
whether the Oracle database server itself is a full Oracle installation; ODBC
still loads a client-side driver in the process where Zope is running.

Oracle documents the Instant Client ODBC package as the standalone Oracle ODBC
client package for Linux and UNIX. Oracle also documents that Instant Client
ODBC 19c can connect to Oracle Database 11.2 or later.

For an Oracle 11g test target, install:

- Oracle Instant Client Basic or Basic Light
- Oracle Instant Client ODBC
- unixODBC

On Ubuntu, install the operating system prerequisites first:

```bash
sudo apt update
sudo apt install -y unixodbc unixodbc-dev odbcinst unzip libaio1t64
```

Download the Linux x86-64 Instant Client packages from Oracle, then place them
on the Zope server. For example, using 19c packages:

```text
instantclient-basic-linux.x64-19_*.zip
instantclient-odbc-linux.x64-19_*.zip
```

Unpack both packages into the same `/opt/oracle` location:

```bash
sudo mkdir -p /opt/oracle
sudo unzip instantclient-basic-linux.x64-19_*.zip -d /opt/oracle
sudo unzip instantclient-odbc-linux.x64-19_*.zip -d /opt/oracle
```

Find the extracted Instant Client directory:

```bash
ls -d /opt/oracle/instantclient_*
```

Assume it is `/opt/oracle/instantclient_19_XX` in the examples below.

Register the shared libraries with the dynamic linker:

```bash
echo /opt/oracle/instantclient_19_XX | sudo tee /etc/ld.so.conf.d/oracle-instantclient.conf
sudo ldconfig
```

On Ubuntu 26.04, Oracle Instant Client 19c may look for `libaio.so.1` while the
distribution package provides `libaio.so.1t64`. This shows up as a missing
dependency when checking the Oracle ODBC driver:

```bash
ldd /opt/oracle/instantclient_19_XX/libsqora.so.19.1 | grep libaio
```

If the output says `libaio.so.1 => not found`, add a compatibility symlink and
refresh the linker cache:

```bash
sudo ln -sf /usr/lib/x86_64-linux-gnu/libaio.so.1t64 /usr/lib/x86_64-linux-gnu/libaio.so.1
sudo ldconfig
```

Then verify that the same `ldd` check resolves `libaio.so.1`.

Verify that the Oracle ODBC shared library can find all dependencies:

```bash
ldd /opt/oracle/instantclient_19_XX/libsqora.so.19.1 | grep 'not found'
```

The command should print nothing.

Register the Oracle ODBC driver with unixODBC. Oracle's ODBC package includes
`odbc_update_ini.sh` for this:

```bash
cd /opt/oracle/instantclient_19_XX
sudo ./odbc_update_ini.sh / /opt/oracle/instantclient_19_XX "Oracle 19c ODBC driver"
```

Verify that unixODBC sees the driver:

```bash
odbcinst -q -d
```

Expected driver name after the example registration:

```text
[Oracle 19c ODBC driver]
```

Example Oracle target:

```text
TNS alias: ORCL
Host: myoracleserver.mydomain.com
Port: 1521
Service name: orcl
```

If DNS/VPN routing is available from the Zope server, the OpenODBCDA connection
string can use the service directly:

```text
DRIVER={Oracle 19c ODBC driver};DBQ=myoracleserver.mydomain.com:1521/orcl;UID=<user>;PWD=<password>
```

If DNS is not available but the VPN route is, use the IP address:

```text
DRIVER={Oracle 19c ODBC driver};DBQ=192.0.2.23:1521/orcl;UID=<user>;PWD=<password>
```

Structured OpenODBCDA fields also work for Oracle. When the selected driver
name contains `Oracle`, structured mode builds `DBQ` rather than `DATABASE`.

For a TNS alias, leave Server and Port empty:

```text
Driver: Oracle 19c ODBC driver
Database / service / DBQ: ORCL
User: <user>
Password: <password>
```

For a direct host/service connection:

```text
Driver: Oracle 19c ODBC driver
Server: myoracleserver.mydomain.com
Port: 1521
Database / service / DBQ: orcl
User: <user>
Password: <password>
```

If you prefer using a TNS alias, create a `tnsnames.ora` file on the Zope
server:

```bash
sudo mkdir -p /opt/oracle/network/admin
sudo tee /opt/oracle/network/admin/tnsnames.ora >/dev/null <<'EOF'
ORCL =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = TCP)(HOST = myoracleserver.mydomain.com)(PORT = 1521))
    (CONNECT_DATA =
      (SERVER = DEDICATED)
      (SERVICE_NAME = orcl)
    )
  )
EOF
```

Set `TNS_ADMIN` in the environment that starts Zope:

```bash
export TNS_ADMIN=/opt/oracle/network/admin
```

Then use:

```text
DRIVER={Oracle 19c ODBC driver};DBQ=ORCL;UID=<user>;PWD=<password>
```

Before testing from Zope, verify network access from the Zope server:

```bash
nc -vz myoracleserver.mydomain.com 1521
```

Then verify the ODBC connection with `isql` or a small `pyodbc` script before
creating the OpenODBCDA connection object.

For older Zope applications originally written against older Oracle adapters,
check the connection object's `Compatibility Result Options` on the Properties
tab. OpenODBCDA can optionally:

- keep Python date/time objects, or return date/datetime values as Zope
  `DateTime` objects or ISO strings
- fetch TIME values as strings
- fetch NULL values as empty strings
- leave scale 0 floats untouched, or convert integral scale 0 floats to Python
  integers when that option is disabled

## Create a Zope 6.1 Virtual Environment

```bash
mkdir -p ~/openodbcda-lab
cd ~/openodbcda-lab

python3 -m venv venv-zope61
. venv-zope61/bin/activate

python -m pip install --upgrade pip wheel setuptools
python -m pip install "Zope==6.1" "Products.ZSQLMethods==5.1" "pyodbc==5.3.0"
```

## Install Products.OpenODBCDA

After the package has been published to PyPI, install it with pip:

```bash
python -m pip install Products.OpenODBCDA
```

During development, or before the first PyPI release, install from a local
checkout:

```bash
cd ~/openodbcda-lab
git clone https://github.com/fixader/Products.OpenODBCDA.git
cd Products.OpenODBCDA
. ../venv-zope61/bin/activate
python -m pip install -e .
```

If the GitHub repository is public, pip can also install directly from a tagged
release:

```bash
python -m pip install "Products.OpenODBCDA @ git+https://github.com/fixader/Products.OpenODBCDA.git@0.1.2"
```

## Install In A Zope 5 Buildout

After a PyPI release, an older buildout-managed Zope 5 instance can install the
package as a normal egg:

```ini
[Instance]
eggs =
    Products.OpenODBCDA
    pyodbc
```

Run buildout and restart:

```bash
cd /home/zope/Zope
bin/buildout
bin/Instance restart
```

For development before the package is published, keep the checkout inside the
buildout and register it as a develop package. The repository contains a
`setup.py` for this exact compatibility path.

Example layout:

```text
/home/zope/Zope/
  buildout.cfg
  src/
    Products.OpenODBCDA/
```

Example `buildout.cfg` changes:

```ini
[buildout]
develop =
    src/Products.OpenODBCDA

[Instance]
eggs =
    Products.OpenODBCDA
    pyodbc
```

Then run:

```bash
cd /home/zope/Zope
bin/buildout
bin/Instance restart
```

On the verified Zope 5.8.3/Python 3.8.10 system, this made `OpenODBC DB
Connector` available in the ZMI add list. A PostgreSQL connector using
`PostgreSQL Unicode` was opened and tested with:

```sql
select 1 as one
```

and:

```sql
select current_date as d, current_time as t, current_timestamp as ts
```

### Install A Downloaded Source Distribution In Zope 5

For older Zope 5 installations without direct PyPI access, copy the source
distribution to a directory readable by the buildout, for example:

```text
/home/zope/downloads/Products.OpenODBCDA-0.1.2.tar.gz
```

Older buildout/easy_install based environments may not recognize the normalized
PyPI source filename when using `find-links`. If your downloaded file is named
`products_openodbcda-0.1.2.tar.gz`, rename it to
`Products.OpenODBCDA-0.1.2.tar.gz` in the local `find-links` directory.

Then use:

```ini
[buildout]
find-links =
    /home/zope/downloads

[Instance]
eggs =
    Products.OpenODBCDA
    pyodbc
```

Run:

```bash
bin/buildout
bin/Instance restart
```

This lets buildout create an egg matching the Python version used by that Zope
installation. On older buildout/easy_install combinations, local source
distributions in `find-links` may fail during egg installation even though the
package itself is valid. If that happens, use a prebuilt egg matching the target
Python version, or install from PyPI when available.

### Install A Downloaded Egg In Zope 5

A prebuilt `.egg` can also be used, but eggs are Python-version-specific. Use
this only when the egg tag matches the target Python version, for example a
`py3.8` egg with a Python 3.8 based Zope 5 installation.

```text
/home/zope/downloads/Products.OpenODBCDA-0.1.2-py3.8.egg
```

The buildout `find-links` configuration is the same as for a source
distribution.

## Create a Zope Instance

```bash
cd ~/openodbcda-lab
. venv-zope61/bin/activate

mkwsgiinstance -d instance-zope61
```

Follow the prompts and create an initial Zope manager user.

Start Zope:

```bash
runwsgi -v instance-zope61/etc/zope.ini
```

Open the ZMI in a browser:

```text
http://server-name-or-ip:8080/manage
```

## Verify ODBC Drivers

List available ODBC drivers:

```bash
odbcinst -q -d
```

For the tested PostgreSQL setup, this included:

```text
[PostgreSQL ANSI]
[PostgreSQL Unicode]
```

Products.OpenODBCDA also shows available `pyodbc` drivers on the connection
Status tab in the ZMI.

## Add an OpenODBC DB Connector in ZMI

In the ZMI:

1. Open the folder where the connection object should live.
2. Select `OpenODBC DB Connector` from the add list.
3. Fill in structured fields or use a raw ODBC connection string.
4. Keep connection pooling disabled unless the same connector will serve many
   simultaneous users.
5. Save the object.
6. Open the connection.
7. Use the `Test` tab to run a query.
8. Use the `Diagnostics` tab to run internal and connection smoke tests.

For Z SQL Methods, the Advanced tab's `Maximum rows to retrieve` setting is
passed to the adapter. A value of `0` means no row limit. Use that deliberately:
large results are fetched into memory before Zope renders the result page or
hands the result to application code.

Example PostgreSQL connection string:

```text
DRIVER={PostgreSQL Unicode};SERVER=127.0.0.1;PORT=5432;DATABASE=openodbc_test;UID=openodbc;PWD=openodbc
```

Example test query:

```sql
select 1 as one
```

## Z SQL Methods

Products.OpenODBCDA registers as a ZRDB-compatible SQL connection. Z SQL Methods
should be able to select the OpenODBCDA connection object in the normal database
connection dropdown.

The lab verified:

- ZMI connection test query
- Z SQL Method using the OpenODBCDA connection
- PostgreSQL via ODBC
- external PostgreSQL via ODBC
- result type mapping diagnostics
- per-connector pooling diagnostics

## Connection Pooling

Connection pooling is configured per OpenODBCDA connection object.

The default is a single physical ODBC connection. This is usually the right
choice when many Zope folders each contain their own connector object.

There is no global OpenODBCDA limit for the maximum number of pools. Connection
pooling is scoped to each Zope connection object.

Only increase pool size when one connector is expected to serve many concurrent
requests. If an installation uses many connector objects with their own pools,
monitor the total number of physical database sessions.

## Run Product Tests

From the package checkout:

```bash
python -m unittest discover -s src/Products/OpenODBCDA/tests -v
```

Expected result in the tested lab:

```text
Ran 6 tests
OK
```
