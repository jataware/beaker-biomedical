"""The agent's tools and a text-tool-call fallback parser.

Two tools, both declared in OpenAI function-calling format so litellm can
translate them to each provider's native schema:

* ``run_python`` — execute code in a persistent namespace (the workhorse).
* ``read_skill_file`` — load a reference/example/asset file from the current
  Agent Skill into context by its skill-relative path. This is the harness's
  *progressive-disclosure* tool: it mirrors how a real agent reads a skill's
  on-demand docs, and — unlike opening the file from Python — it is a salient,
  zero-boilerplate call (just a relative path), which open models reach for far
  more readily.

Some models (notably ``google/gemma-4-31b-it`` on its OpenRouter route) ignore
the schema and emit their *native* tool-call format as plain text;
:func:`parse_text_tool_calls` recovers those — for *either* tool — so they remain
usable. It returns ``(tool_name, args)`` pairs, where ``args`` is a dict keyed by
the argument names the model emitted (``code`` for ``run_python``, ``path`` /
optional ``skill`` for ``read_skill_file``).
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

READ_SKILL_FILE_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "read_skill_file",
        "description": (
            "Load one of the current Agent Skill's reference/example/asset files "
            "into the conversation by its skill-relative path (e.g. "
            "'references/ENDPOINTS.md'). These are the on-demand docs listed in "
            "your task; read them with this tool whenever you need detail the "
            "SKILL.md summary doesn't give. Prefer this over opening the file in "
            "Python — you only need the relative path. Returns the file's text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Skill-relative path, e.g. 'references/ENDPOINTS.md'.",
                },
                "skill": {
                    "type": "string",
                    "description": (
                        "Optional skill name. Defaults to the skill named in your "
                        "task; you normally omit it."
                    ),
                },
            },
            "required": ["path"],
        },
    },
}

# All tools advertised to the model, in priority order.
TOOLS: list[dict] = [RUN_PYTHON_TOOL, READ_SKILL_FILE_TOOL]

# Native tool-call formats some models emit as text instead of structured calls:
#   <|tool_call>call: NAME{arg:<|"|> ...value... <|"|>, arg2:<|"|>...<|"|>}<tool_call|>
#   ```tool_code\n ...code... ```   (gemma's documented python fence)
# We locate each `call: NAME{` head, then harvest every `arg:<|"|>value<|"|>`
# pair up to the next head — the sentinel pair makes this robust to values
# (e.g. Python code) that themselves contain braces.
_CALL_HEAD_RE = re.compile(r'call:\s*(?P<name>\w+)\s*\{', re.DOTALL)
_ARG_RE = re.compile(r'(?P<key>\w+)\s*:\s*<\|"\|>(?P<val>.*?)<\|"\|>', re.DOTALL)
_TOOLCODE_FENCE_RE = re.compile(r'```tool_code\s*\n(?P<code>.*?)```', re.DOTALL)


def parse_text_tool_calls(text: str) -> list[tuple[str, dict[str, str]]]:
    """Extract ``(tool_name, args)`` pairs a model emitted as text rather than via
    structured ``tool_calls``. ``args`` maps each emitted argument name to its
    value. Returns ``[]`` when none are present."""
    heads = list(_CALL_HEAD_RE.finditer(text))
    calls: list[tuple[str, dict[str, str]]] = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[m.end():end]
        args = {am.group("key"): am.group("val") for am in _ARG_RE.finditer(body)}
        calls.append((m.group("name"), args))
    if calls:
        return calls
    # gemma's documented ```tool_code fence → implicit run_python
    return [("run_python", {"code": m.group("code")})
            for m in _TOOLCODE_FENCE_RE.finditer(text)]
