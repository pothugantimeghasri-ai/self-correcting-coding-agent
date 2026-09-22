"""
executor.py

Handles safe, isolated execution of untrusted Python code using subprocesses.

Safety Guarantees & Architecture:
- NEVER uses eval(), exec(), or os.system().
- Writes untrusted code to a isolated temporary .py file.
- Executes the code via subprocess.run() in a separate child process.
- Enforces a strict timeout (default: 5 seconds) to prevent infinite loops.
- Captures stdout, stderr, and exit return code.
- Guarantees temporary file cleanup in a try...finally block.

Note: Subprocess execution + timeout provides basic isolation and resource control,
but is not a full security sandbox (e.g., containerization/gVisor).
"""

import sys
import os
import tempfile
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    return_code: Optional[int]
    status: str  # "PASSED", "FAILED", "TIMEOUT", "EXECUTION_ERROR"
    timed_out: bool = False
    error_summary: Optional[str] = None


class CodeExecutor:
    """Executes untrusted Python code in a temporary subprocess with timeouts."""

    def __init__(self, timeout_seconds: float = 5.0, python_executable: Optional[str] = None):
        self.timeout_seconds = timeout_seconds
        self.python_executable = python_executable or sys.executable

    def execute_code(self, code: str) -> ExecutionResult:
        """
        Saves Python code to a temporary file, executes it via subprocess,
        captures output/errors, and cleans up the temporary file.

        Args:
            code: The Python code string to execute.

        Returns:
            ExecutionResult dataclass containing execution details.
        """
        if not code or not code.strip():
            return ExecutionResult(
                stdout="",
                stderr="Error: Empty or null code provided.",
                return_code=-1,
                status="FAILED",
                error_summary="Empty code string provided"
            )

        temp_file_path = None
        try:
            # Create temporary python file (delete=False so subprocess can access it on Windows)
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name

            # Execute code using subprocess.run (NEVER eval/exec/os.system)
            process = subprocess.run(
                [self.python_executable, temp_file_path],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds
            )

            stdout = process.stdout or ""
            stderr = process.stderr or ""
            return_code = process.returncode

            if return_code == 0:
                status = "PASSED"
                error_summary = None
            else:
                status = "FAILED"
                error_summary = stderr.strip().splitlines()[-1] if stderr.strip() else f"Non-zero exit code: {return_code}"

            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                return_code=return_code,
                status=status,
                timed_out=False,
                error_summary=error_summary
            )

        except subprocess.TimeoutExpired as e:
            stdout = e.stdout if isinstance(e.stdout, str) else (e.stdout.decode("utf-8") if e.stdout else "")
            stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr.decode("utf-8") if e.stderr else "")
            return ExecutionResult(
                stdout=stdout,
                stderr=stderr or f"Execution exceeded maximum timeout of {self.timeout_seconds} seconds.",
                return_code=None,
                status="TIMEOUT",
                timed_out=True,
                error_summary=f"TimeoutExpired: Exceeded {self.timeout_seconds}s limit"
            )

        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=f"System execution failure: {str(e)}",
                return_code=-1,
                status="EXECUTION_ERROR",
                error_summary=str(e)
            )

        finally:
            # Guarantee cleanup of temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass
