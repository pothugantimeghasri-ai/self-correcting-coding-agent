"""
agent.py

Main agent loop for the Execute, Observe, Self-Correct coding agent.

Workflow:
1. User Task -> LLM generates Python code.
2. Save code to temporary .py file.
3. Execute using subprocess.run().
4. Observe stdout / stderr / return code / timeout.
5. Did tests pass?
   ├── YES → Return successful result immediately
   └── NO  → Send error/result back to LLM → Generate corrected code → Retry (Max 3 attempts).
"""

from dataclasses import dataclass, field
from typing import List, Optional
from executor import CodeExecutor, ExecutionResult
from llm import LLMClient
from logger import AgentLogger


@dataclass
class AgentResult:
    task: str
    success: bool
    final_code: str
    total_attempts: int
    attempts_history: List[ExecutionResult] = field(default_factory=list)


class SelfCorrectingAgent:
    """
    Main agent class that coordinates code generation, safe subprocess execution,
    logging, and iterative self-correction.
    """

    def __init__(self, max_attempts: int = 3, timeout_seconds: float = 5.0, llm_client: Optional[LLMClient] = None):
        self.max_attempts = max_attempts
        self.timeout_seconds = timeout_seconds
        self.executor = CodeExecutor(timeout_seconds=timeout_seconds)
        self.llm = llm_client or LLMClient()

    def run(self, task: str) -> AgentResult:
        """
        Executes the main agent loop for a user task.

        Args:
            task: The natural language programming task description with required assertions.

        Returns:
            AgentResult object with final status and execution details.
        """
        print(f"\n========================================")
        print(f"STARTING AGENT TASK: {task}")
        print(f"========================================\n")

        history: List[ExecutionResult] = []
        current_code = ""

        for attempt in range(1, self.max_attempts + 1):
            if attempt == 1:
                # Step 1: Initial code generation
                current_code = self.llm.generate_initial_code(task)
            else:
                # Step 6: Follow-up code correction based on previous execution feedback
                last_result = history[-1]
                current_code = self.llm.generate_corrected_code(
                    task=task,
                    code=current_code,
                    stdout=last_result.stdout,
                    stderr=last_result.stderr,
                    return_code=last_result.return_code if last_result.return_code is not None else -1,
                    attempt=attempt
                )

            # Step 2 & 3: Save to temp file & Execute via subprocess.run()
            result = self.executor.execute_code(current_code)
            history.append(result)

            # Step 9: Clearly log every attempt
            AgentLogger.log_attempt(
                attempt=attempt,
                code=current_code,
                result=result,
                timeout_seconds=self.timeout_seconds
            )

            # Step 8: Stop immediately when the code passes
            if result.status == "PASSED":
                print(f"SUCCESS: Code passed on attempt {attempt}!\n")
                return AgentResult(
                    task=task,
                    success=True,
                    final_code=current_code,
                    total_attempts=attempt,
                    attempts_history=history
                )

        print(f"FAILED: Maximum attempts ({self.max_attempts}) reached without passing assertions.\n")
        return AgentResult(
            task=task,
            success=False,
            final_code=current_code,
            total_attempts=self.max_attempts,
            attempts_history=history
        )


if __name__ == "__main__":
    # Example standalone CLI run
    agent = SelfCorrectingAgent(max_attempts=3)
    sample_task = (
        "Write a Python function reverse(s) that reverses a string.\n"
        "Assertions:\n"
        "assert reverse('abc') == 'cba'"
    )
    result = agent.run(sample_task)
    print(f"Final Outcome: {'PASSED' if result.success else 'FAILED'} in {result.total_attempts} attempts.")
