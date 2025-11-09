"""Test file for variables1.py exercise."""
from types import ModuleType

from pylings.tests import import_exercise, get_variable

import pytest


@pytest.fixture(scope="module")
def variables1() -> ModuleType:
    """Import the variables1 exercise module."""
    return import_exercise("variables1", "01_variables")


def test_my_os_type(variables1: ModuleType) -> None:
    """Test that MY_OS is a string."""
    my_os = get_variable(variables1, "MY_OS")
    assert isinstance(my_os, str), f"Expected str, but got {type(my_os).__name__}"


def test_number_type(variables1: ModuleType) -> None:
    """Test that NUMBER is an integer."""
    number = get_variable(variables1, "NUMBER")
    assert isinstance(number, int), f"Expected int, but got {type(number).__name__}"


def test_fractional_type(variables1: ModuleType) -> None:
    """Test that FRACTIONAL is a float."""
    fractional = get_variable(variables1, "FRACTIONAL")
    assert isinstance(fractional, float), f"Expected float, but got {type(fractional).__name__}"


def test_is_learning_python_type(variables1: ModuleType) -> None:
    """Test that IS_LEARNING_PYTHON is a boolean."""
    is_learning = get_variable(variables1, "IS_LEARNING_PYTHON")
    assert isinstance(is_learning, bool), f"Expected bool, but got {type(is_learning).__name__}"


def test_is_learning_python_value(variables1: ModuleType) -> None:
    """Test that IS_LEARNING_PYTHON is True."""
    is_learning = get_variable(variables1, "IS_LEARNING_PYTHON")
    assert is_learning is True, f"Expected True, but got {is_learning}"


def test_number_incremented(variables1: ModuleType) -> None:
    """Test that NUMBER_INCREMENTED is NUMBER + 1."""
    number = get_variable(variables1, "NUMBER")
    number_incremented = get_variable(variables1, "NUMBER_INCREMENTED")
    assert number_incremented == number + 1, f"Expected {number + 1}, but got {number_incremented}"


def test_print_output(variables1: ModuleType) -> None:
    """Test the output format."""
    my_os = get_variable(variables1, "MY_OS")
    number = get_variable(variables1, "NUMBER")
    fractional = get_variable(variables1, "FRACTIONAL")
    is_learning = get_variable(variables1, "IS_LEARNING_PYTHON")
    number_incremented = get_variable(variables1, "NUMBER_INCREMENTED")
    
    print(f"My Operating System is: {my_os}")
    print(f"This is a whole NUMBER: {number}")
    print(f"This is a FRACTIONAL NUMBER: {fractional}")
    print(f"Am I learning Python? {is_learning}")
    print(f"The NUMBER has been increased: {number_incremented}")
