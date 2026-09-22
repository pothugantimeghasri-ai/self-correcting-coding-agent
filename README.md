# Execute, Observe, Self-Correct Coding Agent

An autonomous Python coding agent that generates code, safely executes it in an isolated subprocess with strict timeouts, observes the runtime outcome (`stdout`, `stderr`, `returncode`), and iteratively self-corrects up to **3 attempts** if execution or test assertions fail.

---

## 1. Project Overview

Large Language Models (LLMs) often generate code with subtle bugs, syntax errors, or failing edge-case assertions. A simple code generator produces single-pass code without verification. 

This project implements an **Execute, Observe, Self-Correct** agent workflow:
- **Execute**: Run generated code as an untrusted script.
- **Observe**: Inspect `stdout`, `stderr`, exit codes, and timeouts.
- **Self-Correct**: Feed execution diagnostics back into the LLM prompt to generate an targeted fix.

---

## 2. Architecture

```text
coding-agent/
│
├── agent.py            # Main control loop & 3-attempt self-correction logic
├── executor.py         # Subprocess launcher, temp file management & 5s timeout
├── llm.py              # LLM client (Gemini/OpenAI APIs + Mock fallback for tests)
├── logger.py           # Structured attempt logging (Attempt #, Code, Output, Error, Status)
├── main.py             # CLI runner demonstrating the 5 test tasks & self-correction loop
├── tests/
│   └── test_agent.py   # Unit test suite verifying all 5 tasks & security constraints
├── requirements.txt    # Project dependencies
├── README.md           # Comprehensive project documentation
└── .gitignore          # Excluded cache & environment files
```

---

## 3. How the Agent Loop Works

```text
               User Task
                   ↓
        LLM Generates Python Code
                   ↓
     Save Code to Temporary .py File
                   ↓
       Execute via subprocess.run()
                   ↓
   Observe stdout / stderr / return code
                   ↓
            Did tests pass?
        ├── YES → Return Successful Result & Stop
        │
        └── NO
             ↓
        Send Error/Output Feedback to LLM
             ↓
        Generate Corrected Code
             ↓
        Retry (Maximum 3 Attempts)
```

---

## 4. Why Execution Feedback Is Important

Without execution feedback, LLMs are forced to "guess" why code failed. By supplying empirical runtime evidence (`stderr` tracebacks, `AssertionError` lines, or `TimeoutExpired` warnings), the LLM receives exact context on the broken state:
- **Syntax errors**: Points to exact line numbers and missing symbols.
- **Assertion failures**: Shows expected vs actual outcomes.
- **Runtime exceptions**: Reveals zero-division, index out of range, or type errors.

---

## 5. Security: Why `eval()` and `exec()` Are Unsafe

Using `eval()` or `exec()` executes untrusted AI-generated code directly inside the agent's main Python process memory space:
- **Shared Memory**: Untrusted code can mutate global state, overwrite built-in modules, or access local variables.
- **System Takeover**: Code could execute `import os; os.system("rm -rf /")` or read sensitive environment variables (`os.environ`).
- **Unstoppable Infinite Loops**: An infinite loop inside `exec()` freezes the entire agent process with no timeout mechanism.

> [!CAUTION]
> **Strict Safety Requirement**: `eval()` and `exec()` are **NEVER** used in this project.

---

## 6. Why Subprocess Execution Is Used

Rather than executing code inside the main Python runtime:
1. Generated code is written to a temporary `.py` file using `tempfile.NamedTemporaryFile`.
2. A separate child process is launched via `subprocess.run([sys.executable, temp_file_path], capture_output=True, text=True, timeout=5)`.
3. The child process runs in isolation; crashing or crashing memory does not crash the host agent.
4. Temporary `.py` files are unconditionally cleaned up in a `finally` block.

---

## 7. Timeout Handling

To protect against infinite loops or blocking code (e.g., `while True:` or `input()`), `subprocess.run()` enforces a default `timeout=5.0` seconds:
- If execution exceeds the limit, `subprocess.TimeoutExpired` is caught.
- Output status is marked as `TIMEOUT`.
- The feedback loop informs the LLM that execution exceeded the timeout, prompting it to optimize loop conditions or remove blocking operations.

---

## 8. Installation Steps

1. Clone or navigate to the project directory:
   ```bash
   cd self-correcting-coding-agent
   ```

2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 9. Environment Variable & API Key Setup

Create a `.env` file in the root directory (optional if using the built-in deterministic Mock provider for local testing):

```env
# For Google Gemini API:
GEMINI_API_KEY=your_gemini_api_key_here

# OR for OpenAI API:
OPENAI_API_KEY=your_openai_api_key_here
```

If no API key is set, the agent automatically falls back to the internal `Mock` LLM provider, allowing offline testing and full verification without API keys.

---

## 10. How to Run the Agent

Run the main demonstration script:

```bash
python main.py
```

Or run `agent.py` directly for a single task:

```bash
python agent.py
```

---

## 11. How to Run the Tests

Execute the unit test suite covering all 5 tasks, self-correction, timeout handling, and security checks:

```bash
python -m unittest discover -s tests
```

---

## 12. Example Execution Logs

### Successful Self-Correction Cycle (Attempt 1 Fail -> Attempt 2 Pass)

```text
========================================
ATTEMPT 1
========================================

Generated Code:
def factorial(n):
    return n * 2  # Intentionally broken code

assert factorial(5) == 120

Execution Result:
<No stdout>

Error:
Traceback (most recent call last):
  File "C:\Users\...\AppData\Local\Temp\tmp123.py", line 4, in <module>
    assert factorial(5) == 120
AssertionError

Return Code:
1

Status:
FAILED

----------------------------------------

========================================
ATTEMPT 2
========================================

Generated Code:
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

assert factorial(5) == 120

Execution Result:
Tests passed

Error:
<No stderr>

Return Code:
0

Status:
PASSED

SUCCESS: Code passed on attempt 2!
```

### Timeout Log Example

```text
========================================
ATTEMPT 1
========================================

Generated Code:
while True:
    pass

Execution Result:
<No stdout>

Error:
<Timeout occurred>

Return Code:
None

Status: TIMEOUT
Reason: Execution exceeded 5 seconds
```

---

## 13. Explanation of Self-Correction for Technical Interviews

When explaining this project in an interview:

1. **Closed-Loop Feedback System**: Analogous to control theory or human pair programming. The model isn't fire-and-forget; it observes runtime errors and adjusts.
2. **Empirical Grounding**: Prompt engineering alone cannot guarantee bug-free code. Grounding the LLM with compiler/runtime errors converts abstract reasoning into a targeted debugging task.
3. **Defense-in-Depth**: Code isolation via subprocess and timeout mechanisms prevents untrusted code from compromising host process stability.

---

## 14. Known Security Limitations

While `subprocess.run()` with timeouts prevents process memory pollution and infinite loops, it is **not a full security sandbox**:
- **File System Access**: The child process runs with the current user's system permissions and can read/write local files.
- **Network Access**: Generated code can make outbound network calls unless restricted at OS/firewall level.
- **Resource Exhaustion**: Code could attempt heavy memory allocation before timing out.

---

## 15. Future Improvements

1. **Docker Container Sandboxing**: Execute generated `.py` files inside ephemeral Docker containers (`docker run --read-only --network none --memory 128m`).
2. **gVisor / Firecracker MicroVMs**: Provide kernel-level sandbox isolation for multi-tenant production environments.
3. **AST Static Analysis**: Parse generated code using Python's `ast` module prior to execution to flag dangerous imports (`os`, `sys`, `shutil`, `socket`) or calls.
