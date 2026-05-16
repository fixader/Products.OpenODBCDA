# Copyright (c) 2026 Rune Ketil Fredriksen and contributors.
# SPDX-License-Identifier: MIT
# The MIT license permits use, copying, distribution, and modification,
# provided that copyright and permission notices are included.
# See LICENSE and NOTICE for details.
# Developed in collaboration with ChatGPT/Codex.
"""Tests for ZRDB result type mapping."""

import unittest

from Products.OpenODBCDA.diagnostics import run_type_mapping_diagnostics
from Products.OpenODBCDA.diagnostics import diagnostics_passed


class ZRDBTypeTests(unittest.TestCase):
    def test_type_mapping_diagnostics_pass(self):
        results = run_type_mapping_diagnostics()
        self.assertTrue(diagnostics_passed(results), results)


if __name__ == "__main__":
    unittest.main()
