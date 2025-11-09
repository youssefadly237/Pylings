"""Test file for intro1.py exercise."""
from types import ModuleType

from pylings.tests import import_exercise

import pytest


@pytest.fixture(scope="module")
def intro1() -> ModuleType:
    """Import the intro1 exercise module."""
    return import_exercise("intro1", "00_intro")


def test_module_imports(intro1: ModuleType) -> None:
    """Test that the intro1 module imports successfully."""
    assert intro1 is not None
    assert hasattr(intro1, "main"), "intro1 module should have a main function"


def test_main_function_exists(intro1: ModuleType) -> None:
    """Test that main function is callable."""
    assert callable(intro1.main), "main should be a callable function"


def test_main_runs_without_error(intro1: ModuleType) -> None:
    """Test that main() executes without errors."""
    try:
        intro1.main()
    except Exception as e:
        pytest.fail(f"main() raised an exception: {e}")
