"""Test-process setup shared by the suite."""
from __future__ import annotations

import tempfile
from pathlib import Path


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest-temp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)

# Some managed Windows environments deny SQLite access in the system %TEMP%.
# Keep disposable test databases inside the writable workspace instead.
tempfile.tempdir = str(TEST_TEMP_ROOT)
