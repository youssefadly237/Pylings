#!/usr/bin/env python3
"""Validate that all exercises have corresponding test files.

This script ensures that every exercise file in the exercises/ directory
has a corresponding test file in the tests/ directory.
"""
import sys
from pathlib import Path
from typing import List, Tuple

PYLINGS_ROOT = Path(__file__).parent.parent
PYLINGS_PKG = PYLINGS_ROOT / "pylings"
EXERCISES_DIR = PYLINGS_PKG / "exercises"
TESTS_DIR = PYLINGS_PKG / "tests"


def find_exercises() -> List[Path]:
    """Find all exercise Python files."""
    exercises = []
    for py_file in EXERCISES_DIR.rglob("*.py"):
        if py_file.parent.name not in {"__pycache__"}:
            exercises.append(py_file)
    return sorted(exercises)


def find_missing_tests(exercises: List[Path]) -> List[Tuple[Path, Path]]:
    """Find exercises that are missing test files.
    
    Returns:
        List of tuples (exercise_path, expected_test_path)
    """
    missing = []
    
    for exercise in exercises:
        try:
            relative_to_exercises = exercise.relative_to(EXERCISES_DIR)
            parts = relative_to_exercises.parts
            
            if len(parts) >= 2:
                topic = parts[0]
                exercise_name = parts[-1]
                test_name = f"test_{exercise_name}"
                expected_test = TESTS_DIR / topic / test_name
                
                if not expected_test.exists():
                    missing.append((exercise, expected_test))
        except ValueError:
            continue
    
    return missing


def main() -> int:
    """Main validation function."""
    print("🔍 Validating test coverage for Pylings exercises...\n")
    
    exercises = find_exercises()
    print(f"Found {len(exercises)} exercise files")
    
    missing_tests = find_missing_tests(exercises)
    
    if not missing_tests:
        print("✅ All exercises have corresponding test files!")
        return 0
    
    print(f"\n❌ Found {len(missing_tests)} exercises without test files:\n")
    
    for exercise, expected_test in missing_tests:
        relative_exercise = exercise.relative_to(EXERCISES_DIR)
        relative_test = expected_test.relative_to(TESTS_DIR)
        print(f"  Exercise: exercises/{relative_exercise}")
        print(f"  Missing:  tests/{relative_test}\n")
    
    print(f"\n⚠️  Please create test files for the {len(missing_tests)} missing exercises.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
