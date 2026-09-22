"""
llm.py

Handles LLM code generation, prompt formatting, markdown code extraction,
and supports external API providers (Gemini / OpenAI) as well as deterministic Mock LLM fallback.
"""

import os
import re
import requests
from typing import Optional, Dict, Any


def extract_python_code(text: str) -> str:
    """
    Extracts pure Python code from LLM responses, stripping markdown code fences.
    """
    if not text:
        return ""
    
    # Try finding markdown python code block ```python ... ```
    pattern = r"```(?:python)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # If no fences, return stripped text
    return text.strip()


class LLMClient:
    """
    Client for interacting with LLM providers or Mock LLM logic for deterministic tests.
    """

    def __init__(self, provider: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize LLM client with provider preference.
        Supported providers: "gemini", "openai", "mock".
        Default detection order:
          1. GEMINI_API_KEY / GOOGLE_API_KEY -> "gemini"
          2. OPENAI_API_KEY -> "openai"
          3. Fallback -> "mock"
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        if provider:
            self.provider = provider.lower()
        elif os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            self.provider = "gemini"
        elif os.getenv("OPENAI_API_KEY"):
            self.provider = "openai"
        else:
            self.provider = "mock"

        self.model = model or ("gemini-2.5-flash" if self.provider == "gemini" else "gpt-4o-mini" if self.provider == "openai" else "mock-v1")
        
        # Dictionary for mock responses for deterministic testing and self-correction demonstrations
        self.mock_registry: Dict[str, list] = {}

    def register_mock_responses(self, task_keyword: str, attempt_code_list: list):
        """Allows test suites to register sequence of generated code per attempt."""
        self.mock_registry[task_keyword.lower()] = attempt_code_list

    def generate_initial_code(self, task: str) -> str:
        """Generates initial Python code for a given task prompt."""
        system_prompt = (
            "You are an expert Python code generator. Generate complete, correct Python code "
            "satisfying the requested task and all assertions. "
            "Return ONLY executable Python code inside ```python ``` blocks. Do not explain."
        )
        user_prompt = f"Task:\n{task}\n\nRequirements:\n- Provide complete code with any required function definitions and assertions.\n- Return ONLY valid Python code."
        
        raw_response = self._call_llm(system_prompt, user_prompt, task=task, attempt=1)
        return extract_python_code(raw_response)

    def generate_corrected_code(self, task: str, code: str, stdout: str, stderr: str, return_code: Any, attempt: int = 2) -> str:
        """
        Generates corrected Python code based on execution feedback.
        """
        system_prompt = "You are an expert Python bug-fixing assistant. Return ONLY corrected Python code."
        
        follow_up_prompt = f"""The generated Python code failed during execution.

Original task:
{task}

Generated code:
{code}

Execution output:
{stdout}

Error:
{stderr}

Return code:
{return_code}

Please identify the problem and generate a corrected version of the Python code.

Requirements:
- Return only the corrected Python code.
- Do not explain the solution.
- Make sure all required assertions pass."""

        raw_response = self._call_llm(system_prompt, follow_up_prompt, task=task, attempt=attempt)
        return extract_python_code(raw_response)

    def _call_llm(self, system_prompt: str, user_prompt: str, task: str = "", attempt: int = 1) -> str:
        """Routes execution to selected LLM provider or Mock fallback."""
        if self.provider == "mock":
            return self._mock_call(task, attempt)

        if self.provider == "gemini":
            return self._call_gemini(system_prompt, user_prompt)

        if self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt)

        return self._mock_call(task, attempt)

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Calls Gemini API via Google GenAI SDK or direct REST fallback."""
        if not self.api_key:
            return "# Error: No GEMINI_API_KEY found"

        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=f"{system_prompt}\n\n{user_prompt}"
            )
            return response.text or ""
        except ImportError:
            # Fallback to direct REST API call if sdk not installed
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}]
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Calls OpenAI API via REST fallback or openai package."""
        if not self.api_key:
            return "# Error: No OPENAI_API_KEY found"

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _mock_call(self, task: str, attempt: int) -> str:
        """Rule-based mock generator for offline tests and self-correction demos."""
        task_lower = task.lower()

        # Check registered mock responses first
        for kw, attempts in self.mock_registry.items():
            if kw in task_lower:
                idx = min(attempt - 1, len(attempts) - 1)
                return attempts[idx]

        # Standard 5 test tasks fallback rules
        if "reverse" in task_lower:
            if attempt == 1 and "fail" in task_lower:
                return "def reverse(s):\n    return s # Incorrect\n\nassert reverse('abc') == 'cba'"
            return "def reverse(s):\n    return s[::-1]\n\nassert reverse('abc') == 'cba'"

        if "palindrome" in task_lower:
            if attempt == 1 and "fail" in task_lower:
                return "def is_palindrome(s):\n    return True # Incorrect\n\nassert is_palindrome('madam') == True\nassert is_palindrome('hello') == False"
            return "def is_palindrome(s):\n    return s == s[::-1]\n\nassert is_palindrome('madam') == True\nassert is_palindrome('hello') == False"

        if "max" in task_lower:
            if attempt == 1 and "fail" in task_lower:
                return "def find_max(numbers):\n    return numbers[0] # Incorrect\n\nassert find_max([3, 7, 2, 9]) == 9"
            return "def find_max(numbers):\n    return max(numbers)\n\nassert find_max([3, 7, 2, 9]) == 9"

        if "factorial" in task_lower:
            if attempt == 1 and "fail" in task_lower:
                return "def factorial(n):\n    return n * 2 # Buggy\n\nassert factorial(5) == 120"
            return "def factorial(n):\n    if n == 0 or n == 1:\n        return 1\n    return n * factorial(n - 1)\n\nassert factorial(5) == 120"

        if "duplicate" in task_lower:
            if attempt == 1 and "fail" in task_lower:
                return "def remove_duplicates(items):\n    return items # Buggy\n\nassert remove_duplicates([1, 2, 2, 3, 1]) == [1, 2, 3]"
            return "def remove_duplicates(items):\n    res = []\n    for x in items:\n        if x not in res:\n            res.append(x)\n    return res\n\nassert remove_duplicates([1, 2, 2, 3, 1]) == [1, 2, 3]"

        return f"# Default Mock response for: {task}\nprint('Executing task solution')\nassert True"
