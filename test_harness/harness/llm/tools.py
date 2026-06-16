"""The agent's single tool — ``run_python`` — and a text-tool-call fallback.

The tool is declared in OpenAI function-calling format; litellm translates it to
each provider's native schema. Some models (notably ``google/gemma-4-31b-it`` on
its OpenRouter route) ignore the schema and emit their *native* tool-call format
as plain text; :func:`parse_text_tool_calls` detects and recovers those so they
remain usable.
"""

from __future__ import annotations

import re

RUN_PYTHON_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "run_python",
        "description": (
            "Execute Python 3 code in a persistent namespace and return its "
            "stdout/stderr. State persists across calls. `requests`/`json`/`urllib` "
            "are available and `cdapython` is importable. Anything you want to "
            "observe you MUST print(). Use this to query the live APIs, parse "
            "responses, and compute results."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute."}
            },
            "required": ["code"],
        },
    },
}

# Native tool-call formats some models emit as text instead of structured calls:
#   <|tool_call>call:run_python{code:<|"|> ...code... <|"|>}<tool_call|>
#   ```tool_code\n ...code... ```
_TEXT_TOOLCALL_RE = re.compile(
    r'call:\s*(?P<name>\w+)\s*\{\s*code\s*:\s*<\|"\|>(?P<code>.*?)<\|"\|>', re.DOTALL)
_TOOLCODE_FENCE_RE = re.compile(r'```tool_code\s*\n(?P<code>.*?)```', re.DOTALL)


def parse_text_tool_calls(text: str) -> list[tuple[str, str]]:
    """Extract ``(tool_name, code)`` pairs a model emitted as text rather than via
    structured ``tool_calls``. Returns ``[]`` when none are present."""
    calls = [(m.group("name"), m.group("code")) for m in _TEXT_TOOLCALL_RE.finditer(text)]
    if calls:
        return calls
    # gemma's documented ```tool_code fence → implicit run_python
    return [("run_python", m.group("code")) for m in _TOOLCODE_FENCE_RE.finditer(text)]
