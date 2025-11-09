"""
Provides the ExerciseManager class for managing the lifecycle of Pylings exercises.

Handles loading, checking, resetting, and running exercises, as well as tracking completion
and progress state for UI and CLI tools.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from pathlib import Path
from shutil import copy, copy2
import subprocess

import pylings
from pylings.config import ConfigManager
from pylings.constants import (BACKUP_DIR, EXERCISES_DIR, FINISHED, SOLUTIONS_DIR, TESTS_DIR)

log = logging.getLogger(__name__)

class ExerciseManager:
    """Manages the lifecycle of exercises in Pylings.

    Responsibilities include:
    - Initializing exercise metadata and tracking state.
    - Executing exercises and retrieving output.
    - Resetting exercises to their original form.
    - Moving to the next exercise.
    - Checking completion status and tracking progress.
    - Providing access to matching solutions.
    """

    def __init__(self):
        """Initializes the exercise manager and loads exercises.

        Also checks if this is the first time running the workspace.
        """
        log.debug("ExerciseManager.__init__")
        self.exercises = {}
        self.current_exercise = None
        self.current_exercise_state = ""
        self.arg_exercise = None
        self.completed_count = 0
        self.completed_flag = False
        self.config_manager = ConfigManager()
        self.watcher = None
        self.show_hint = False

        self._initialize_exercises()
        self.config_manager.check_first_time()

    def _initialize_exercises(self):
        """Loads and evaluates all exercises from the workspace into memory."""
        exercises = sorted(EXERCISES_DIR.rglob("*.py"))
        results = self._evaluate_exercises_ordered(exercises)

        for path, result in results:
            self._store_result(path, result)

        self.current_exercise = EXERCISES_DIR / self.config_manager.get_lasttime_exercise()
        self.current_exercise_state = self.exercises[self.current_exercise.name]["status"]
        self.completed_count = sum(1 for ex in self.exercises.values() if ex["status"] == "DONE")

    def _evaluate_exercises_ordered(self, exercise_paths):
        """Runs each exercise and returns results in original order.

        Args:
            exercise_paths (list[Path]): Paths to all exercises.

        Returns:
            list[tuple[Path, subprocess.CompletedProcess]]: Paths and their results in original order.
        """
        result_map = {}
        with ThreadPoolExecutor() as executor:
            future_to_path = {executor.submit(self.run_exercise, ex): ex for ex in exercise_paths}
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result()
                    result_map[path] = result
                except Exception as e:
                    log.error("Error processing exercise %s: %s", path, e)
        
        return [(path, result_map[path]) for path in exercise_paths if path in result_map]

    def _store_result(self, path, result):
        """Stores the result of an exercise run in the internal tracking dictionary.
        
        Status determination:
        - returncode == 0: Exercise passed all tests → DONE
        - returncode != 0: Exercise failed or skipped → PENDING
        """
        name = path.name
        status = "DONE" if result.returncode == 0 else "PENDING"
        
        error_output = result.stderr if result.stderr else result.stdout
        
        self.exercises[name] = {
            "path": path,
            "status": status,
            "output": self._format_output(result.stdout) if result.returncode == 0 else "",
            "error": self._format_output(error_output) if result.returncode != 0 else None,
            "hint": self.config_manager.get_hint(path),
        }

    def _update_exercise_status(self, name, result):
        """Updates the status and output of a given exercise.

        Args:
            name (str): Exercise filename.
            result (CompletedProcess): The result of executing the file.

        Returns:
            str: new status values.
        """
        new_status = "DONE" if result.returncode == 0 else "PENDING"
        
        error_output = result.stderr if result.stderr else result.stdout
        
        self.exercises[name].update({
            "status": new_status,
            "output": self._format_output(result.stdout) if result.returncode == 0 else "",
            "error": self._format_output(error_output) if result.returncode != 0 else None
        })
        return new_status

    def _get_test_path(self, exercise_path: Path) -> Path | None:
        """Get the corresponding test file path for an exercise.
        
        Args:
            exercise_path (Path): Path to the exercise file.
            
        Returns:
            Path | None: Path to the test file if it exists, None otherwise.
            
        Note:
            Returns None for backward compatibility with exercises that haven't
            been migrated to the new test system yet.
        """
        path_parts = list(exercise_path.parts)
        if "exercises" in path_parts:
            exercises_idx = path_parts.index("exercises")
            relative_parts = path_parts[exercises_idx + 1:]
        else:
            relative_parts = [exercise_path.name]
        
        if len(relative_parts) >= 2:
            topic = relative_parts[0]
            exercise_name = relative_parts[-1]
            test_name = f"test_{exercise_name}"
            test_path = TESTS_DIR / topic / test_name
            
            if test_path.exists():
                log.debug("Found test file: %s", test_path)
                return test_path
            
            log.debug("Test file not found (using direct execution): %s", test_path)
            return None
        
        log.debug("Cannot determine test path for: %s", exercise_path)
        return None

    def _run_with_tests(self, exercise_path: Path, test_path: Path, cwd: Path) -> subprocess.CompletedProcess:
        """Run exercise and validate with tests.
        
        Args:
            exercise_path: Path to the exercise file.
            test_path: Path to the test file.
            cwd: Working directory for execution.
            
        Returns:
            CompletedProcess with exercise output and test validation result.
        """
        log.debug("Running exercise with tests: %s", exercise_path)
        log.debug("Test path: %s", test_path)
        log.debug("Working directory: %s", cwd)
        try:
            test_result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_path), 
                 "-v", "--tb=line", "--no-header"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=cwd
            )
            tests_pass = test_result.returncode == 0
            log.debug("Pytest return code: %d", test_result.returncode)
            log.debug("Pytest stdout: %s", test_result.stdout[:500])
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                args=[str(exercise_path)],
                returncode=1,
                stdout="",
                stderr="Exercise timed out."
            )
        except Exception as e:
            return subprocess.CompletedProcess(
                args=[str(exercise_path)],
                returncode=1,
                stdout="",
                stderr=f"Error running tests: {e}"
            )
        
        direct_result = self._run_exercise_directly(exercise_path)
        
        if tests_pass and direct_result.returncode == 0:
            return subprocess.CompletedProcess(
                args=[str(exercise_path)],
                returncode=0,
                stdout=direct_result.stdout,
                stderr=""
            )
        
        if direct_result.returncode != 0:
            return direct_result
        
        error_msg = self._extract_test_error(test_result.stdout)
        return subprocess.CompletedProcess(
            args=[str(exercise_path)],
            returncode=1,
            stdout="",
            stderr=error_msg
        )
    
    def _extract_test_error(self, pytest_output: str) -> str:
        """Extract error message from pytest output.
        
        Parses pytest's short test summary to extract test names and error descriptions.
        Handles both test failures (FAILED) and errors (ERROR, e.g., syntax errors).
        
        Args:
            pytest_output: Raw pytest -q output.
            
        Returns:
            Formatted error message with test name and description.
        """
        lines = pytest_output.split('\n')
        errors = []
        
        for line in lines:
            if line.startswith(('FAILED ', 'ERROR ')):
                parts = line.split(' - ', 1)
                if len(parts) == 2:
                    prefix = 'FAILED ' if line.startswith('FAILED ') else 'ERROR '
                    test_path = parts[0].replace(prefix, '').strip()
                    error_desc = parts[1].strip()
                    
                    if '::' in test_path:
                        test_name = test_path.split('::')[-1]
                        errors.append(f"{test_name}: {error_desc}")
                    else:
                        errors.append(error_desc)
            
            elif line.strip().startswith('E ') and 'AssertionError:' in line:
                error_detail = line.split('AssertionError:', 1)[1].strip()
                if error_detail and not any(error_detail in e for e in errors):
                    errors.append(f"  {error_detail}")
            
            elif 'File "' in line and 'exercises/' in line and ', line ' in line:
                try:
                    start = line.index('exercises/')
                    end = line.index(', line ')
                    file_part = line[start:end]
                    line_part = line[end + 7:].split()[0].strip(',')
                    if line_part.isdigit():
                        errors.append(f"  at {file_part}:{line_part}")
                except (ValueError, IndexError):
                    pass
        
        return '\n'.join(errors) if errors else "Tests failed. Check your code matches the requirements."

    def run_exercise(self, path: Path, source: str = "workspace"):
        """Runs a Python exercise file and returns the result.

        Args:
            path (Path): Path to the exercise file.
            source (str): Where to run from: "workspace" or "package".

        Returns:
            subprocess.CompletedProcess: Contains returncode, stdout, stderr.
        """
        log.debug("ExerciseManager.run_exercise: path=%s, source=%s", path, source)

        path_parts = list(path.parts)
        if path_parts[0] == "exercises":
            path_parts = path_parts[1:]
        relative_path = Path(*path_parts)

        base_dir = Path(pylings.__file__).parent if source == "package" else Path.cwd()
        exercise_path = base_dir / "exercises" / relative_path
        test_path = self._get_test_path(exercise_path)
        
        # BACKWARD COMPATIBILITY: If no test file exists, run exercise directly (old behavior)
        if test_path is None:
            log.info("No test file found, falling back to direct execution: %s", exercise_path.name)
            return self._run_exercise_directly(exercise_path)
        
        # NEW SYSTEM: Run exercise directly first to get output, then validate with pytest
        return self._run_with_tests(exercise_path, test_path, base_dir)
    
    def _run_exercise_directly(self, exercise_path: Path) -> subprocess.CompletedProcess:
        """Run an exercise file directly (backward compatibility for exercises without tests).
        
        Args:
            exercise_path: Path to the exercise file.
            
        Returns:
            CompletedProcess with execution results.
        """
        try:
            process = subprocess.Popen(
                [sys.executable, str(exercise_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=exercise_path.parent
            )
            stdout, stderr = process.communicate(timeout=10)
            return subprocess.CompletedProcess(
                args=[str(exercise_path)],
                returncode=process.returncode,
                stdout=stdout,
                stderr=stderr
            )
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return subprocess.CompletedProcess(
                args=[str(exercise_path)],
                returncode=1,
                stdout=stdout,
                stderr="Exercise timed out."
            )
        except Exception as e:
            return subprocess.CompletedProcess(
                args=[str(exercise_path)],
                returncode=1,
                stdout="",
                stderr=str(e)
            )

    def _format_output(self, output):
        """Sanitizes output for display, especially in Rich/Textual components."""
        return output.replace("[", "\\[")

    def update_exercise_output(self):
        """Re-runs the current exercise and updates its status and progress tracking."""
        log.debug("ExerciseManager.update_exercise_output")
        if self.arg_exercise:
            self.current_exercise = self.arg_exercise
            self.arg_exercise = None

        if not self.current_exercise:
            return

        result = self.run_exercise(self.current_exercise)
        name = self.current_exercise.name
        new_status = self._update_exercise_status(name, result)
        self.current_exercise_state = new_status

        self.completed_count = sum(1 for ex in self.exercises.values() if ex["status"] == "DONE")
        log.debug(f"ExerciseManager.update_exercise_output.self.completed_count: ${self.completed_count}")
        if self.completed_count == len(self.exercises) and not self.completed_flag:
            print(FINISHED)
            self.completed_flag = True

    def check_all_exercises(self, progress_callback=None):
        """Checks all exercises for completion status.

        Args:
            progress_callback (Callable): Optional callback to update UI progress.
        """
        log.debug("ExerciseManager.check_all_exercises")
        current_exercise_path = self.current_exercise
        exercises = list(self.exercises.values())
        paths = [ex["path"] for ex in exercises]
        results = self._evaluate_exercises_ordered(paths)

        for i, (path, result) in enumerate(results):
            name = path.name
            self._update_exercise_status(name, result)
            if progress_callback:
                progress_callback(path.name, i, len(results))

        self.completed_count = sum(1 for ex in self.exercises.values() if ex["status"] == "DONE")
        log.debug(f"ExerciseManager.check_all_exercises.self.completed_count: ${self.completed_count}")
        self.current_exercise = current_exercise_path

    def next_exercise(self):
        """Moves to the next exercise in order.

        Updates current exercise state and triggers output update.
        """
        log.debug("ExerciseManager.next_exercise")
        exercises = list(self.exercises.values())
        current_index = next((i for i, ex in enumerate(exercises) if ex["path"] == self.current_exercise), None)

        if current_index is not None and current_index + 1 < len(exercises):
            new_exercise = exercises[current_index + 1]["path"]
            self.current_exercise = new_exercise
            self.show_hint = False
            self.update_exercise_output()
            self.current_exercise_state = self.exercises[self.current_exercise.name]["status"]
            self.config_manager.set_lasttime_exercise(new_exercise)
            if self.watcher:
                self.watcher.restart(str(self.current_exercise))
        else:
            print("All exercises completed!")

    def reset_exercise(self):
        """Restores the current exercise from its backup version, if available."""
        log.debug("ExerciseManager.reset_exercise")
        if not self.current_exercise:
            print("No current exercise to reset.")
            return

        backup_path = self.current_exercise.relative_to(EXERCISES_DIR)
        root_backup = BACKUP_DIR / backup_path

        if root_backup.exists():
            root_backup.parent.mkdir(parents=True, exist_ok=True)
            copy(root_backup, self.current_exercise)
            prev_status = self.exercises[self.current_exercise.name]["status"]
            self.update_exercise_output()
            if prev_status == "DONE":
                self.completed_flag = False
                self.completed_count -= 1
        else:
            print(f"No backup found for {self.current_exercise}.")

    def get_solution(self):
        """Resolves and copies the solution file for the current exercise.

        Returns:
            tuple[Path, str] | None: Local solution path and short form, or None on failure.
        """
        log.debug("ExerciseManager.get_solution")
        if not self.current_exercise:
            return None

        try:
            SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)
            relative_path = self.current_exercise.relative_to(EXERCISES_DIR)
            solution_path = SOLUTIONS_DIR / relative_path
            root_solution = Path(pylings.__file__).parent / "solutions" / relative_path

            if root_solution.exists():
                solution_path.parent.mkdir(parents=True, exist_ok=True)
                copy2(root_solution, solution_path)
                local_path = self.config_manager.get_local_solution_path(solution_path)
                return solution_path, local_path

            return None
        except Exception as e:
            log.error(f"Error resolving solution path: {e}")
            return None

    def get_exercise_path(self, path: Path, source: str = "workspace") -> Path:
        """Returns the absolute exercise path, resolving relative to workspace or package.

        Args:
            path (Path): A path that may or may not include 'exercises/' prefix.
            source (str): 'workspace' or 'package'.

        Returns:
            Path: Resolved absolute path to the exercise.

        Raises:
            FileNotFoundError: If the resolved file doesn't exist.
        """
        log.debug("ExerciseManager.get_exercise_path: path=%s, source=%s", path, source)
        try:
            # Convert to absolute path first
            abs_path = path.resolve() if not path.is_absolute() else path
            
            # Handle special case of "." (current directory)
            if str(path) == ".":
                log.error("Cannot use '.' as exercise path. Please specify a valid exercise file.")
                raise ValueError("Cannot use '.' as exercise path. Please specify a valid exercise file.")
            
            path_parts = list(abs_path.parts)
            
            # Handle empty path
            if not path_parts:
                log.error("Empty path provided")
                raise ValueError("Empty path provided")
            
            # Extract relative path from exercises directory
            if "exercises" in path_parts:
                exercises_idx = path_parts.index("exercises")
                rel_parts = path_parts[exercises_idx + 1:]
            else:
                # Assume it's already a relative path
                rel_parts = list(path.parts)
            
            if not rel_parts:
                log.error("Cannot determine exercise path from: %s", path)
                raise ValueError(f"Cannot determine exercise path from: {path}")

            rel_path = Path(*rel_parts)

            if source == "workspace":
                root = Path.cwd() / "exercises" / rel_path
                log.debug("ExerciseManager.get_exercise_path: root=%s", root)
            else:
                root = Path(pylings.__file__).parent / "exercises" / rel_path
                log.debug("ExerciseManager.get_exercise_path: root=%s", root)
            
            if not root.exists():
                log.error("ExerciseManager.get_exercise_path.fileNotFound: %s", path)
                raise FileNotFoundError(f"Exercise file not found: {path}")

            return root
        except Exception as e:
            log.error("get_exercise_path error: %s", e)
            raise


    def run_and_print(self, path: Path, source: str = "workspace", type: str = "d"):
        """Runs or shows a solution for a specified path in CLI mode.

        Args:
            path (Path): Path to the exercise or solution.
            source (str): Context ("workspace" or "package").
            type (str): Mode - "d" for dry-run, "s" for solution.
        """
        if type == "d":
            path = self.get_exercise_path(path, source)
            result = self.run_exercise(path, source)
        elif type == "s":
            result = self.print_root_solution(path, source)

        output = result.stdout if result.returncode == 0 else result.stderr
        print(output)
        if result.returncode != 0:
            raise RuntimeError(f"Exercise execution failed with return code {result.returncode}")


    def print_root_solution(self, path: Path, source: str = "package"):
        """Runs a solution file for a given exercise from the specified context.

        Args:
            path (Path): Path to the solution.
            source (str): "workspace" or "package"

        Returns:
            CompletedProcess: Execution result
        """
        log.debug(f"ExerciseManager.print_root_solution: path={path}, source={source}")


        path_parts = list(path.parts)
        if path_parts[0] == "exercises":
            path_parts[0] = "solutions"
        elif "solutions" not in path_parts:
            path_parts.insert(0, "solutions")

        if source == "workspace":
            root = Path.cwd().joinpath(*path_parts)
        else:
            root = Path(pylings.__file__).parent.joinpath(*path_parts)

        if not root.exists():
            log.error(f"Solution file not found: {root}")
            
            #raise FileNotFoundError(f"Solution not found: {path}")
            exit (1)
        return self.run_exercise(root, source)

    def reset_exercise_by_path(self, path: Path):
        """Reset a specific exercise given its path.

        Args:
            path (Path): Path to the exercise file to reset.
        """
        log.debug("ExerciseManager.reset_exercise_by_path: %s", path)
        path = path.resolve()
        exercises_dir = EXERCISES_DIR.resolve()

        if not path.exists():
            print(f"Exercise path not found: {path}")
            raise FileNotFoundError(f"Exercise path not found: {path}")

        if exercises_dir not in path.parents:
            print("Path must be under exercises/")
            raise ValueError("Path must be under exercises/")

        try:
            rel_path = path.relative_to(exercises_dir)
            log.debug("ExerciseManager.reset_exercise_by_path.rel_path: %s", rel_path)
        except ValueError as e:
            print("Path must be under exercises/")
            raise ValueError("Path must be under exercises/") from e

        backup_path = BACKUP_DIR / rel_path
        log.debug("ExerciseManager.reset_exercise_by_path.backup_path: %s", backup_path)
        if not backup_path.exists():
            print(f"No backup found for {rel_path}")
            raise FileNotFoundError(f"No backup found for {rel_path}")

        copy(backup_path, path)
        print(f"Reset exercise: {rel_path}")


    def toggle_hint(self):
        """Toggles whether the hint for the current exercise should be displayed."""
        log.debug("ExerciseManager.toggle_hint")
        self.show_hint = not self.show_hint
# End-of-file (EOF)
