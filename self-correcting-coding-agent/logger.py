"""
logger.py

Formats and prints execution attempt details for the coding agent.
"""

from executor import ExecutionResult


class AgentLogger:
    """Provides formatted logging for each code generation and self-correction attempt."""

    @staticmethod
    def log_attempt(attempt: int, code: str, result: ExecutionResult, timeout_seconds: float = 5.0) -> str:
        """
        Formats and prints a detailed attempt log to console, and returns the log string.
        """
        lines = []
        lines.append("========================================")
        lines.append(f"ATTEMPT {attempt}")
        lines.append("========================================\n")
        lines.append("Generated Code:")
        lines.append(code.strip() if code else "<No code generated>")
        lines.append("")

        if result.status == "TIMEOUT":
            lines.append("Execution Result:")
            lines.append(result.stdout.strip() if result.stdout else "<No stdout>")
            lines.append("")
            lines.append("Error:")
            lines.append(result.stderr.strip() if result.stderr else "<Timeout occurred>")
            lines.append("")
            lines.append("Return Code:")
            lines.append(str(result.return_code) if result.return_code is not None else "None")
            lines.append("")
            lines.append("Status: TIMEOUT")
            lines.append(f"Reason: Execution exceeded {timeout_seconds} seconds")
        else:
            lines.append("Execution Result:")
            lines.append(result.stdout.strip() if result.stdout else ("Tests passed" if result.status == "PASSED" else "<No stdout>"))
            lines.append("")
            lines.append("Error:")
            lines.append(result.stderr.strip() if result.stderr else "<No stderr>")
            lines.append("")
            lines.append("Return Code:")
            lines.append(str(result.return_code) if result.return_code is not None else "None")
            lines.append("")
            lines.append(f"Status:\n{result.status}")

        log_output = "\n".join(lines)
        print(log_output)
        print("\n" + "-" * 40 + "\n")
        return log_output
