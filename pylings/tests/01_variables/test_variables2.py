"""Test file for variables2.py exercise."""
from types import ModuleType

from pylings.tests import import_exercise, get_variable

import pytest


@pytest.fixture(scope="module")
def variables2() -> ModuleType:
    """Import the variables2 exercise module."""
    return import_exercise("variables2", "01_variables")


def test_celsius_name(variables2: ModuleType) -> None:
    """Test that celsius_name is correctly assigned."""
    assert get_variable(variables2, "celsius_name") == "Celsius"


def test_celsius_temp(variables2: ModuleType) -> None:
    """Test that celsius_temp is correctly assigned."""
    assert get_variable(variables2, "celsius_temp") == 100.10


def test_fahrenheit_name(variables2: ModuleType) -> None:
    """Test that fahrenheit_name is correctly assigned."""
    assert get_variable(variables2, "fahrenheit_name") == "Fahrenheit"


def test_fahrenheit_temp(variables2: ModuleType) -> None:
    """Test that fahrenheit_temp is correctly calculated."""
    assert get_variable(variables2, "fahrenheit_temp") == 212.18


def test_kelvin_name(variables2: ModuleType) -> None:
    """Test that kelvin_name is correctly assigned."""
    assert get_variable(variables2, "kelvin_name") == "Kelvin"


def test_kelvin_temp(variables2: ModuleType) -> None:
    """Test that kelvin_temp is correctly calculated."""
    assert get_variable(variables2, "kelvin_temp") == 373.25


def test_print_output(variables2: ModuleType) -> None:
    """Test the output format."""
    celsius_name = get_variable(variables2, "celsius_name")
    celsius_temp = get_variable(variables2, "celsius_temp")
    fahrenheit_name = get_variable(variables2, "fahrenheit_name")
    fahrenheit_temp = get_variable(variables2, "fahrenheit_temp")
    kelvin_name = get_variable(variables2, "kelvin_name")
    kelvin_temp = get_variable(variables2, "kelvin_temp")
    
    print(f"Temperature in {celsius_name}: {celsius_temp}")
    print(f"Temperature in {fahrenheit_name}: {fahrenheit_temp}")
    print(f"Temperature in {kelvin_name}: {kelvin_temp}")
