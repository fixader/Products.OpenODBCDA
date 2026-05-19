# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Connection configuration helpers for OpenODBCDA."""

SENSITIVE_KEYS = {"pwd", "password"}
STRUCTURED_KEYS = {
    "driver": "driver",
    "server": "server",
    "address": "server",
    "port": "port",
    "database": "database",
    "dbq": "database",
    "uid": "username",
    "user": "username",
    "username": "username",
    "pwd": "password",
    "password": "password",
}


def build_connection_string(
    driver="",
    server="",
    port="",
    database="",
    username="",
    password="",
    extra_options="",
):
    """Build an ODBC connection string from structured settings."""
    parts = []
    if driver:
        parts.append(("DRIVER", _brace_driver(driver)))
    if is_oracle_driver(driver):
        dbq = build_oracle_dbq(server=server, port=port, database=database)
        if dbq:
            parts.append(("DBQ", dbq))
    else:
        if server:
            parts.append(("SERVER", server))
        if port:
            parts.append(("PORT", port))
        if database:
            parts.append(("DATABASE", database))
    if username:
        parts.append(("UID", username))
    if password:
        parts.append(("PWD", password))

    connection_string = ";".join(f"{key}={value}" for key, value in parts)
    extra_options = normalize_extra_options(extra_options)
    if extra_options:
        if connection_string:
            connection_string = f"{connection_string};{extra_options}"
        else:
            connection_string = extra_options
    return connection_string


def mask_connection_string(connection_string):
    """Mask password-like keys in an ODBC connection string."""
    parts = []
    for part in connection_string.split(";"):
        if "=" not in part:
            parts.append(part)
            continue
        key, value = part.split("=", 1)
        if key.strip().lower() in SENSITIVE_KEYS and value:
            parts.append(f"{key}=********")
        else:
            parts.append(part)
    return ";".join(parts)


def parse_connection_string(connection_string):
    """Parse common ODBC connection string keys into structured settings."""
    parsed = {
        "driver": "",
        "server": "",
        "port": "",
        "database": "",
        "username": "",
        "password": "",
        "extra_options": "",
    }
    extra = []
    for part in split_connection_string(connection_string):
        if "=" not in part:
            if part:
                extra.append(part)
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = _unbrace(value.strip())
        target = STRUCTURED_KEYS.get(key.lower())
        if target:
            parsed[target] = value
        else:
            extra.append(f"{key}={value}")
    parsed["extra_options"] = ";".join(extra)
    return parsed


def split_connection_string(connection_string):
    """Split ODBC connection strings while respecting braces."""
    parts = []
    current = []
    brace_depth = 0
    for char in connection_string:
        if char == "{":
            brace_depth += 1
        elif char == "}" and brace_depth:
            brace_depth -= 1
        if char == ";" and not brace_depth:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        parts.append("".join(current).strip())
    return parts


def normalize_extra_options(extra_options):
    """Normalize free-form connection string fragments."""
    lines = []
    for line in extra_options.replace("\r", "\n").split("\n"):
        line = line.strip().strip(";")
        if line:
            lines.append(line)
    return ";".join(lines)


def is_oracle_driver(driver):
    """Return true when the selected ODBC driver looks like Oracle."""
    return "oracle" in (driver or "").lower()


def build_oracle_dbq(server="", port="", database=""):
    """Build Oracle's DBQ value from structured fields.

    Oracle ODBC uses DBQ rather than SERVER/DATABASE. With no server, the
    database field is treated as a TNS alias or a full host:port/service value.
    With a server, database is treated as the service name.
    """
    server = (server or "").strip()
    port = str(port or "").strip()
    database = (database or "").strip()
    if not server:
        return database
    host = server
    if port:
        host = f"{host}:{port}"
    if database:
        return f"{host}/{database}"
    return host


def truthy(value):
    if isinstance(value, (list, tuple)):
        return any(truthy(item) for item in value)
    return str(value).lower() in {"1", "true", "yes", "on"}


def _brace_driver(driver):
    driver = driver.strip()
    if driver.startswith("{") and driver.endswith("}"):
        return driver
    return f"{{{driver}}}"


def _unbrace(value):
    if value.startswith("{") and value.endswith("}"):
        return value[1:-1]
    return value
