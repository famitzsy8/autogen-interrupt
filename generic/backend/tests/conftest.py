"""Shared pytest fixtures and configuration"""

import pytest
import os
from pathlib import Path

@pytest.fixture(scope="session")
def test_data_dir():
    """Directory containing test data"""
    return Path(__file__).parent / "data"

@pytest.fixture(scope="session")
def ensure_api_key():
    """Ensure API key is available for tests that need it"""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set - skipping tests requiring API")

@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment between tests"""
    yield
    # Cleanup code here if needed
