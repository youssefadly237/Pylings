"""Test infrastructure for Pylings exercises."""
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def import_exercise(exercise_name: str, topic: str) -> ModuleType:
    """Import an exercise module dynamically using importlib.
    
    Args:
        exercise_name: Name of the exercise file (without .py extension).
        topic: Topic directory name (e.g., '01_variables').
        
    Returns:
        The imported module.
        
    Raises:
        ImportError: If the module cannot be imported.
        FileNotFoundError: If the exercise file doesn't exist.
    """
    possible_paths = [
        Path.cwd() / "exercises" / topic / f"{exercise_name}.py",
        Path.cwd() / "pylings" / "exercises" / topic / f"{exercise_name}.py",
        Path.cwd().parent / "exercises" / topic / f"{exercise_name}.py",
    ]
    
    for exercise_path in possible_paths:
        if exercise_path.exists():
            break
    else:
        raise FileNotFoundError(
            f"Exercise file not found. Tried:\n" +
            "\n".join(f"  - {p}" for p in possible_paths)
        )
    
    spec = importlib.util.spec_from_file_location(
        f"exercise_{topic}_{exercise_name}",
        exercise_path
    )
    
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {exercise_path}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def get_variable(module: ModuleType, name: str) -> Any:
    """Get a variable from a module.
    
    Args:
        module: The module to get the variable from.
        name: Name of the variable.
        
    Returns:
        The variable value.
        
    Raises:
        AttributeError: If the variable doesn't exist.
    """
    if not hasattr(module, name):
        raise AttributeError(f"Module has no attribute '{name}'")
    return getattr(module, name)
