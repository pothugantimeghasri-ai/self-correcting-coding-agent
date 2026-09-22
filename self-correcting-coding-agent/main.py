"""
main.py

Demonstration runner for the Execute, Observe, Self-Correct coding agent.
Runs the 5 required tasks and demonstrates the self-correction loop in action.
"""

from agent import SelfCorrectingAgent
from llm import LLMClient


def run_demo():
    print("==========================================================")
    print("   EXECUTE, OBSERVE, SELF-CORRECT CODING AGENT DEMO       ")
    print("==========================================================\n")

    llm_client = LLMClient(provider="mock")
    agent = SelfCorrectingAgent(max_attempts=3, timeout_seconds=5.0, llm_client=llm_client)

    tasks = [
        ("Task 1: Reverse a string", "Write a Python function reverse(s) that reverses a string.\nassert reverse('abc') == 'cba'"),
        ("Task 2: Check palindrome", "Write a Python function is_palindrome(s) that returns True if s is a palindrome and False otherwise.\nassert is_palindrome('madam') == True\nassert is_palindrome('hello') == False"),
        ("Task 3: Find maximum number", "Write a Python function find_max(numbers) that returns the max number.\nassert find_max([3, 7, 2, 9]) == 9"),
        ("Task 4: Calculate factorial", "Write a Python function factorial(n) that calculates factorial of n.\nassert factorial(5) == 120"),
        ("Task 5: Remove duplicates from a list", "Write a Python function remove_duplicates(items) that removes duplicates while preserving order.\nassert remove_duplicates([1, 2, 2, 3, 1]) == [1, 2, 3]"),
    ]

    for title, prompt in tasks:
        print(f"\n>>> Running {title} ...")
        result = agent.run(prompt)
        print(f"Result for '{title}': {'SUCCESS' if result.success else 'FAILED'} (Attempts: {result.total_attempts})")

    # Demonstrate explicit self-correction loop with intentional initial failure
    print("\n" + "=" * 58)
    print("   DEMONSTRATING INTENTIONAL FAILURE & SELF-CORRECTION LOOP ")
    print("=" * 58)

    buggy_task_title = "Task 6: Self-Correction Demo (Buggy initial output)"
    buggy_task_prompt = "Write a function factorial(n) with self-correction demo.\nassert factorial(5) == 120"
    
    llm_client.register_mock_responses(
        task_keyword=buggy_task_prompt,
        attempt_code_list=[
            # Attempt 1: Intentionally broken code (Fails assertion)
            "def factorial(n):\n    return n * 2  # Intentionally broken code\n\nassert factorial(5) == 120",
            # Attempt 2: Corrected code (Passes assertion)
            "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n\nassert factorial(5) == 120"
        ]
    )

    demo_result = agent.run(buggy_task_prompt)
    print(f"Self-Correction Demo Result: {'SUCCESS' if demo_result.success else 'FAILED'} in {demo_result.total_attempts} attempts.")


if __name__ == "__main__":
    run_demo()
