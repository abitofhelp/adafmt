# =============================================================================
# adafmt - Ada Language Formatter
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Michael Gardner, A Bit of Help, Inc.
# See LICENSE file in the project root.
# =============================================================================

import pytest, importlib
spec = importlib.util.find_spec("file_discovery") or importlib.util.find_spec("adafmt.file_discovery")
if not spec:
    pytest.skip("file_discovery module not present")
fd = importlib.import_module(spec.name)
def test_discovery_module_imports():
    assert fd is not None