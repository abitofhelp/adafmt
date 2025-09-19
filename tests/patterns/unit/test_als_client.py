# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

import pytest, importlib
spec = importlib.util.find_spec("als_client") or importlib.util.find_spec("adafmt.als_client")
if not spec:
    pytest.skip("als_client module not present")
als = importlib.import_module(spec.name)
def test_als_module_imports():
    assert als is not None