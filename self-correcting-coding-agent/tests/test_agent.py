"""
tests/test_agent.py

Test suite verifying:
1. The 5 required coding tasks (Reverse String, Palindrome, Find Max, Factorial, Remove Duplicates).
2. Explicit demonstration of the self-correction loop (Failure -> Feedback -> Correction -> Success).
3. Timeout handling & execution error handling.
4. Security audit verifying zero usage of eval() or exec() in the codebase.
"""

import os
import unittest
import glob
from agent import SelfCorrectingAgent
from executor import CodeExecutor
from llm import LLMClient


import ast

class TestCodingAgent(unittest.TestCase):

    def setUp(self):
        # Use mock LLM client to ensure tests run deterministically and fast without external API keys
        self.llm_client = LLMClient(provider="mock")
        self.agent = SelfCorrectingAgent(max_attempts=3, timeout_seconds=5.0, llm_client=self.llm_client)

    def test_task_1_reverse_string(self):
        task = (
            "Write a function reverse(s) that returns the reversed string.\n"
            "Assertions:\n"
            "assert reverse('abc') == 'cba'"
        )
        result = self.agent.run(task)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts_history[-1].status, "PASSED")

    def test_task_2_check_palindrome(self):
        task = (
            "Write a function is_palindrome(s) that returns True if s is a palindrome and False otherwise.\n"
            "Assertions:\n"
            "assert is_palindrome('madam') == True\n"
            "assert is_palindrome('hello') == False"
        )
        result = self.agent.run(task)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts_history[-1].status, "PASSED")

    def test_task_3_find_maximum(self):
        task = (
            "Write a function find_max(numbers) that returns the maximum number in a list.\n"
            "Assertions:\n"
            "assert find_max([3, 7, 2, 9]) == 9"
        )
        result = self.agent.run(task)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts_history[-1].status, "PASSED")

    def test_task_4_calculate_factorial(self):
        task = (
            "Write a function factorial(n) that returns the factorial of n.\n"
            "Assertions:\n"
            "assert factorial(5) == 120"
        )
        result = self.agent.run(task)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts_history[-1].status, "PASSED")

    def test_task_5_remove_duplicates(self):
        task = (
            "Write a function remove_duplicates(items) that removes duplicates while preserving order.\n"
            "Assertions:\n"
            "assert remove_duplicates([1, 2, 2, 3, 1]) == [1, 2, 3]"
        )
        result = self.agent.run(task)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts_history[-1].status, "PASSED")

    def test_self_correction_loop(self):
        """
        Explicitly demonstrates failure -> feedback -> correction -> success.
        Attempt 1: Generates broken code with failing assertion.
        Attempt 2: Generates corrected code after receiving stderr feedback.
        """
        task_name = "Self Correction Test (Factorial with initial bug)"
        self.llm_client.register_mock_responses(
            task_keyword=task_name,
            attempt_code_list=[
                # Attempt 1: Broken code (AssertionError)
                "def factorial(n):\n    return n * 2  # Buggy implementation\n\nassert factorial(5) == 120",
                # Attempt 2: Corrected code
                "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)\n\nassert factorial(5) == 120"
            ]
        )

        result = self.agent.run(task_name)

        self.assertTrue(result.success)
        self.assertEqual(result.total_attempts, 2)
        # Attempt 1 failed with AssertionError
        self.assertEqual(result.attempts_history[0].status, "FAILED")
        self.assertIn("AssertionError", result.attempts_history[0].stderr)
        # Attempt 2 passed
        self.assertEqual(result.attempts_history[1].status, "PASSED")

    def test_timeout_handling(self):
        """Verifies that infinite loops are caught by the executor timeout mechanism."""
        infinite_loop_code = "import time\nwhile True:\n    time.sleep(0.1)"
        executor = CodeExecutor(timeout_seconds=1.0)
        res = executor.execute_code(infinite_loop_code)
        self.assertEqual(res.status, "TIMEOUT")
        self.assertTrue(res.timed_out)

    def test_syntax_error_handling(self):
        """Verifies that syntax errors are captured in stderr."""
        bad_syntax = "def foo(:\n    pass"
        executor = CodeExecutor(timeout_seconds=2.0)
        res = executor.execute_code(bad_syntax)
        self.assertEqual(res.status, "FAILED")
        self.assertIn("SyntaxError", res.stderr)

    def test_no_eval_or_exec_used(self):
        """
        Security requirement check: Ensure eval() and exec() function calls are never used
        in any python files within the project.
        """
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        py_files = glob.glob(os.path.join(project_root, "*.py")) + glob.glob(os.path.join(project_root, "tests", "*.py"))
        
        for file_path in py_files:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=file_path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            self.assertNotIn(node.func.id, ["eval", "exec"], f"Forbidden function call '{node.func.id}()' found in {file_path}")


if __name__ == "__main__":
    unittest.main()
