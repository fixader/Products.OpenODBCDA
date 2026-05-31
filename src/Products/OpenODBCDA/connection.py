# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Zope connection object for OpenODBCDA."""

from AccessControl.class_init import InitializeClass
from AccessControl.Permissions import change_database_connections
from AccessControl.Permissions import test_database_connections
from AccessControl.Permissions import view_management_screens
from AccessControl.SecurityInfo import ClassSecurityInfo
from App.special_dtml import DTMLFile
from DateTime.DateTime import DateTime
from Shared.DC.ZRDB.Connection import Connection

from .config import build_connection_string
from .config import mask_connection_string
from .config import parse_connection_string
from .config import truthy
from .db import OpenODBCDatabaseConnection
from .db import ResultOptions
from .db import available_odbc_drivers
from .db import normalize_pool_size
from .diagnostics import diagnostics_passed
from .diagnostics import run_connection_diagnostics
from .diagnostics import run_type_mapping_diagnostics
from ._version import __version__


class OpenODBCConnection(Connection):
    """Persistent Zope connection object used by Z SQL Methods."""

    security = ClassSecurityInfo()

    meta_type = "OpenODBC DB Connector"
    database_type = "Open ODBC"
    _isAnSQLConnection = 1
    manage_options = (
        Connection.manage_options[:3]
        + ({"label": "Diagnostics", "action": "manage_diagnostics"},)
        + Connection.manage_options[3:]
    )
    connect_on_load = False
    zmi_icon = "fas fa-database"
    driver = ""
    server = ""
    port = ""
    database = ""
    username = ""
    password = ""
    extra_options = ""
    raw_connection_string = ""
    use_raw_connection_string = True
    pool_enabled = False
    pool_size = 1
    null_as_empty_string = False
    time_as_string = False
    leave_scale0_floats_untouched = True
    date_time_format = "python"

    def __init__(
        self,
        id,
        title,
        connection_string="",
        check=None,
        driver="",
        server="",
        port="",
        database="",
        username="",
        password="",
        extra_options="",
        use_raw_connection_string=True,
        pool_enabled=False,
        pool_size=1,
        null_as_empty_string=False,
        time_as_string=False,
        leave_scale0_floats_untouched=True,
        date_time_format="python",
    ):
        self.id = str(id)
        self.title = title
        self.driver = driver
        self.server = server
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.extra_options = extra_options
        self.raw_connection_string = connection_string
        self.use_raw_connection_string = truthy(use_raw_connection_string)
        self.pool_enabled = truthy(pool_enabled)
        self.pool_size = normalize_pool_size(pool_size)
        self.null_as_empty_string = truthy(null_as_empty_string)
        self.time_as_string = truthy(time_as_string)
        self.leave_scale0_floats_untouched = truthy(leave_scale0_floats_untouched)
        self.date_time_format = normalize_date_time_format(date_time_format)
        if connection_string and not any((driver, server, database, username)):
            self.populate_from_connection_string(connection_string, overwrite=False)
        self.connection_string = self.effective_connection_string()
        if check:
            self.connect(self.connection_string)

    def factory(self):
        return OpenODBCDatabaseConnection

    def edit(
        self,
        title,
        connection_string="",
        check=1,
        driver=None,
        server=None,
        port=None,
        database=None,
        username=None,
        password=None,
        extra_options=None,
        use_raw_connection_string=None,
        clear_password=None,
        pool_enabled=None,
        pool_size=None,
        null_as_empty_string=None,
        time_as_string=None,
        leave_scale0_floats_untouched=None,
        date_time_format=None,
    ):
        self.title = title
        if driver is not None:
            self.driver = driver.strip()
        if server is not None:
            self.server = server.strip()
        if port is not None:
            self.port = str(port).strip()
        if database is not None:
            self.database = database.strip()
        if username is not None:
            self.username = username.strip()
        if clear_password:
            self.password = ""
        elif password:
            self.password = password
        if extra_options is not None:
            self.extra_options = extra_options.strip()
        if connection_string is not None:
            self.raw_connection_string = connection_string.strip()
        if use_raw_connection_string is not None:
            self.use_raw_connection_string = truthy(use_raw_connection_string)
        elif self.raw_connection_string and not self.driver:
            self.use_raw_connection_string = True
        if pool_enabled is not None:
            self.pool_enabled = truthy(pool_enabled)
        if pool_size is not None:
            self.pool_size = normalize_pool_size(pool_size)
        if null_as_empty_string is not None:
            self.null_as_empty_string = truthy(null_as_empty_string)
        if time_as_string is not None:
            self.time_as_string = truthy(time_as_string)
        if leave_scale0_floats_untouched is not None:
            self.leave_scale0_floats_untouched = truthy(
                leave_scale0_floats_untouched
            )
        if date_time_format is not None:
            self.date_time_format = normalize_date_time_format(date_time_format)

        if self.raw_connection_string and not any(
            (self.driver, self.server, self.database, self.username)
        ):
            self.populate_from_connection_string(
                self.raw_connection_string,
                overwrite=False,
                include_password=not bool(self.password),
            )

        self.connection_string = self.effective_connection_string()
        if check:
            self.connect(self.connection_string)

    security.declareProtected(view_management_screens, "manage_main")
    manage_main = DTMLFile("www/connectionStatus", globals())

    security.declareProtected(change_database_connections, "manage_properties")
    manage_properties = DTMLFile("www/editConnection", globals())

    security.declareProtected(test_database_connections, "manage_testForm")
    manage_testForm = DTMLFile("www/testConnection", globals())

    security.declareProtected(test_database_connections, "manage_diagnostics")
    manage_diagnostics = DTMLFile("www/diagnostics", globals())

    security.declareProtected(change_database_connections, "manage_edit")
    def manage_edit(
        self,
        title,
        connection_string="",
        check=None,
        driver=None,
        server=None,
        port=None,
        database=None,
        username=None,
        password=None,
        extra_options=None,
        use_raw_connection_string=None,
        clear_password=None,
        pool_enabled=None,
        pool_size=None,
        null_as_empty_string=None,
        time_as_string=None,
        leave_scale0_floats_untouched=None,
        date_time_format=None,
        REQUEST=None,
    ):
        """Edit OpenODBCDA connection settings from the ZMI."""
        self.edit(
            title,
            connection_string=connection_string,
            check=check,
            driver=driver,
            server=server,
            port=port,
            database=database,
            username=username,
            password=password,
            extra_options=extra_options,
            use_raw_connection_string=use_raw_connection_string,
            clear_password=clear_password,
            pool_enabled=pool_enabled,
            pool_size=pool_size,
            null_as_empty_string=null_as_empty_string,
            time_as_string=time_as_string,
            leave_scale0_floats_untouched=leave_scale0_floats_untouched,
            date_time_format=date_time_format,
        )
        if REQUEST is not None:
            return self.manage_main(self, REQUEST)

    security.declareProtected(change_database_connections, "manage_populate_from_connection_string")
    def manage_populate_from_connection_string(
        self,
        connection_string=None,
        overwrite=1,
        include_password=None,
        REQUEST=None,
    ):
        """Populate structured connection fields from an ODBC string."""
        source = connection_string or self.raw_connection_string or self.connection_string
        self.populate_from_connection_string(
            source,
            overwrite=truthy(overwrite),
            include_password=truthy(include_password),
        )
        self.connection_string = self.effective_connection_string()
        if REQUEST is not None:
            return self.manage_properties(self, REQUEST)

    def populate_from_connection_string(
        self,
        connection_string,
        overwrite=False,
        include_password=True,
    ):
        parsed = parse_connection_string(connection_string)
        for name in ("driver", "server", "port", "database", "username", "extra_options"):
            if overwrite or not getattr(self, name, ""):
                setattr(self, name, parsed[name])
        if include_password and (overwrite or not self.password):
            self.password = parsed["password"]

    security.declareProtected(view_management_screens, "masked_connection_string")
    def masked_connection_string(self):
        return mask_connection_string(self.effective_connection_string())

    security.declareProtected(view_management_screens, "version")
    def version(self):
        """Return the installed Products.OpenODBCDA package version."""
        return __version__

    security.declareProtected(view_management_screens, "masked_raw_connection_string")
    def masked_raw_connection_string(self):
        return mask_connection_string(self.raw_connection_string)

    def parsed_connection_config(self):
        source = self.raw_connection_string or self.connection_string
        parsed = parse_connection_string(source)
        return {
            "driver": self.driver or parsed["driver"],
            "server": self.server or parsed["server"],
            "port": self.port or parsed["port"],
            "database": self.database or parsed["database"],
            "username": self.username or parsed["username"],
            "extra_options": self.extra_options or parsed["extra_options"],
        }

    security.declareProtected(view_management_screens, "display_driver")
    def display_driver(self):
        return self.parsed_connection_config()["driver"]

    security.declareProtected(view_management_screens, "display_server")
    def display_server(self):
        return self.parsed_connection_config()["server"]

    security.declareProtected(view_management_screens, "display_port")
    def display_port(self):
        return self.parsed_connection_config()["port"]

    security.declareProtected(view_management_screens, "display_database")
    def display_database(self):
        return self.parsed_connection_config()["database"]

    security.declareProtected(view_management_screens, "display_username")
    def display_username(self):
        return self.parsed_connection_config()["username"]

    security.declareProtected(view_management_screens, "display_extra_options")
    def display_extra_options(self):
        return self.parsed_connection_config()["extra_options"]

    security.declareProtected(view_management_screens, "effective_connection_string")
    def effective_connection_string(self):
        if self.use_raw_connection_string:
            return self.raw_connection_string or self.connection_string
        return build_connection_string(
            driver=self.driver,
            server=self.server,
            port=self.port,
            database=self.database,
            username=self.username,
            password=self.password,
            extra_options=self.extra_options,
        )

    security.declareProtected(view_management_screens, "odbc_drivers")
    def odbc_drivers(self):
        return available_odbc_drivers()

    security.declareProtected(view_management_screens, "connection_info")
    def connection_info(self):
        connection = getattr(self, "_v_database_connection", None)
        if connection is None:
            return "No physical ODBC connection is open."
        return connection.info()

    security.declareProtected(view_management_screens, "effective_pool_size")
    def effective_pool_size(self):
        if not self.pool_enabled:
            return 1
        return normalize_pool_size(self.pool_size)

    security.declareProtected(view_management_screens, "result_options")
    def result_options(self):
        return ResultOptions(
            null_as_empty_string=truthy(self.null_as_empty_string),
            time_as_string=truthy(self.time_as_string),
            leave_scale0_floats_untouched=truthy(
                self.leave_scale0_floats_untouched
            ),
            date_time_format=normalize_date_time_format(self.date_time_format),
        )

    security.declareProtected(view_management_screens, "current_pool_size")
    def current_pool_size(self):
        connection = getattr(self, "_v_database_connection", None)
        if connection is None:
            return 0
        return connection.current_pool_size()

    security.declareProtected(view_management_screens, "idle_pool_size")
    def idle_pool_size(self):
        connection = getattr(self, "_v_database_connection", None)
        if connection is None:
            return 0
        return connection.idle_pool_size()

    security.declareProtected(view_management_screens, "in_use_pool_size")
    def in_use_pool_size(self):
        connection = getattr(self, "_v_database_connection", None)
        if connection is None:
            return 0
        return connection.in_use_pool_size()

    security.declareProtected(view_management_screens, "tables")
    def tables(self, schema=None, table=None, table_type=None):
        """Return normalized ODBC table catalog metadata."""
        return self._database_connection().tables(
            schema=schema,
            table=table,
            table_type=table_type,
        )

    security.declareProtected(view_management_screens, "columns")
    def columns(self, table, schema=None, column=None):
        """Return normalized ODBC column catalog metadata."""
        return self._database_connection().columns(
            table,
            schema=schema,
            column=column,
        )

    security.declareProtected(view_management_screens, "primary_keys")
    def primary_keys(self, table, schema=None):
        """Return normalized ODBC primary key catalog metadata."""
        return self._database_connection().primary_keys(table, schema=schema)

    security.declareProtected(view_management_screens, "primary_key_columns")
    def primary_key_columns(self, table, schema=None):
        """Return primary key column names for a table."""
        return self._database_connection().primary_key_columns(table, schema=schema)

    security.declareProtected(view_management_screens, "foreign_keys")
    def foreign_keys(self, table=None, schema=None):
        """Return normalized ODBC foreign key catalog metadata."""
        return self._database_connection().foreign_keys(table=table, schema=schema)

    security.declareProtected(view_management_screens, "referenced_by")
    def referenced_by(self, table, schema=None):
        """Return foreign keys in other tables that reference this table."""
        return self._database_connection().referenced_by(table, schema=schema)

    security.declareProtected(view_management_screens, "table_names")
    def table_names(self, schema=None, table=None, table_type=None):
        """Return table names from ODBC table catalog metadata."""
        return [
            item["name"]
            for item in self.tables(
                schema=schema,
                table=table,
                table_type=table_type,
            )
        ]

    security.declareProtected(view_management_screens, "column_names")
    def column_names(self, table, schema=None, column=None):
        """Return column names from ODBC column catalog metadata."""
        return [
            item["name"]
            for item in self.columns(table, schema=schema, column=column)
        ]

    security.declareProtected(test_database_connections, "type_mapping_diagnostics")
    def type_mapping_diagnostics(self):
        """Return internal OpenODBCDA type-mapping diagnostic results."""
        return run_type_mapping_diagnostics()

    security.declareProtected(test_database_connections, "connection_diagnostics")
    def connection_diagnostics(self):
        """Return smoke-test diagnostic results for the open ODBC connection."""
        connection = getattr(self, "_v_database_connection", None)
        if connection is None:
            return {"sql": "", "results": []}
        sql, results = run_connection_diagnostics(connection)
        return {"sql": sql, "results": results}

    security.declareProtected(test_database_connections, "diagnostics_passed")
    def diagnostics_passed(self, results):
        """Return true when all diagnostic result rows passed."""
        return diagnostics_passed(results)

    def connect(self, s=None):
        if s is None:
            s = self.effective_connection_string()
        self.connection_string = s
        self.manage_close_connection()
        DB = self.factory()
        self._v_database_connection = DB(
            s,
            pool_size=self.effective_pool_size(),
            result_options=self.result_options(),
        )
        self._v_connected = DateTime()
        return self

    def _database_connection(self):
        connection = getattr(self, "_v_database_connection", None)
        if connection is None:
            self.connect()
            connection = self._v_database_connection
        return connection


InitializeClass(OpenODBCConnection)


manage_addOpenODBCConnectionForm = DTMLFile("www/addConnection", globals())


def manage_addOpenODBCConnection(
    self,
    id,
    title="",
    connection_string="",
    driver="",
    server="",
    port="",
    database="",
    username="",
    password="",
    extra_options="",
    use_raw_connection_string=None,
    pool_enabled=None,
    pool_size=1,
    null_as_empty_string=False,
    time_as_string=False,
    leave_scale0_floats_untouched=True,
    date_time_format="python",
    check=None,
    REQUEST=None,
):
    """Add an OpenODBC DB connector to a Zope folder."""
    connection = OpenODBCConnection(
        id,
        title,
        connection_string,
        check=check,
        driver=driver,
        server=server,
        port=port,
        database=database,
        username=username,
        password=password,
        extra_options=extra_options,
        use_raw_connection_string=use_raw_connection_string,
        pool_enabled=pool_enabled,
        pool_size=pool_size,
        null_as_empty_string=null_as_empty_string,
        time_as_string=time_as_string,
        leave_scale0_floats_untouched=leave_scale0_floats_untouched,
        date_time_format=date_time_format,
    )
    self._setObject(id, connection)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST)


def normalize_date_time_format(value):
    value = (value or "python").strip().lower()
    if value in {"python", "iso", "zope"}:
        return value
    return "python"
