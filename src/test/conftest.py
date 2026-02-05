"""Pytest configuration and fixtures for NOEMA Combine tests."""

import pytest  # noqa: F401

# Note: Tests use @patch decorators to mock specific module-level variables
# from data_handler.py. The patches are applied at the function level,
# so each test gets a fresh set of mocked values without needing fixture support.
