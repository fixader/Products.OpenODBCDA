# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Product registration for Products.OpenODBCDA."""

from ._version import __version__
from .connection import OpenODBCConnection
from .connection import manage_addOpenODBCConnection
from .connection import manage_addOpenODBCConnectionForm


def initialize(context):
    context.registerClass(
        OpenODBCConnection,
        permission="Add OpenODBC DB Connectors",
        constructors=(
            manage_addOpenODBCConnectionForm,
            manage_addOpenODBCConnection,
        ),
    )
