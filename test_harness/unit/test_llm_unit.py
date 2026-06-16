"""Unit tests for the litellm engine's pure helpers — no API calls.

The exec sandbox and tool-result formatter (``harness.llm.sandbox``) and the
text-tool-call fallback parser (``harness.llm.tools``) are provider-independent
and guard the loop without needing any key or network.
"""

from harness.llm.sandbox import CodeStep, PyEnv, format_tool_result
from harness.llm.tools import parse_text_tool_calls


# --------------------------------------------------------------------------- #
# exec sandbox + tool-result formatting (harness.llm.sandbox)
# --------------------------------------------------------------------------- #
def test_pyenv_persists_namespace_and_captures_stdout():
    env = PyEnv()
    env.run("x = 41")
    step = env.run("print(x + 1)")
    assert step.stdout.strip() == "42"
    assert step.error is None


def test_pyenv_captures_exception_as_error():
    step = PyEnv().run("1 / 0")
    assert step.error and "ZeroDivisionError" in step.error
    assert step.stdout == ""


def test_format_tool_result_includes_streams():
    step = CodeStep(code="...", stdout="the out", stderr="a warning", error="Traceback…")
    payload = format_tool_result(step)
    assert "the out" in payload and "[stderr]" in payload and "[exception]" in payload


def test_format_tool_result_empty_is_placeholder_and_clips():
    assert format_tool_result(CodeStep(code="")) == "(no output)"
    big = CodeStep(code="", stdout="x" * 50)
    assert len(format_tool_result(big, limit=10)) == 10


# --------------------------------------------------------------------------- #
# text-tool-call fallback (for models that emit native tool calls as text)
# --------------------------------------------------------------------------- #
def test_parse_text_tool_calls_native_format():
    text = 'sure, let me run that. call: run_python{code:<|"|>print(1)<|"|>}'
    assert parse_text_tool_calls(text) == [("run_python", "print(1)")]


def test_parse_text_tool_calls_tool_code_fence():
    assert parse_text_tool_calls("```tool_code\nprint(2)\n```") == [("run_python", "print(2)\n")]


def test_parse_text_tool_calls_none_present():
    assert parse_text_tool_calls("just prose, no tool call here") == []
