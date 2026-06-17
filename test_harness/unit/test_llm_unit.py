"""Unit tests for the litellm engine's pure helpers — no API calls.

The exec sandbox and tool-result formatter (``harness.llm.sandbox``), the
text-tool-call fallback parser (``harness.llm.tools``), and the progressive-
disclosure resource reader (``harness.skills.read_skill_resource``, which backs
the ``read_skill_file`` tool) are provider-independent and guard the loop without
needing any key or network.
"""

from harness.config import HarnessConfig, SERVICE_TO_SKILL
from harness.llm.sandbox import RESOURCE_CHAR_CAP, CodeStep, PyEnv, format_tool_result
from harness.llm.tools import parse_text_tool_calls
from harness.skills import read_skill_resource


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
    assert parse_text_tool_calls(text) == [("run_python", {"code": "print(1)"})]


def test_parse_text_tool_calls_read_skill_file():
    # gemma reaches the progressive-disclosure tool through the same text fallback
    text = 'let me check. call: read_skill_file{path:<|"|>references/ENDPOINTS.md<|"|>}'
    assert parse_text_tool_calls(text) == [("read_skill_file", {"path": "references/ENDPOINTS.md"})]


def test_parse_text_tool_calls_tool_code_fence():
    assert parse_text_tool_calls("```tool_code\nprint(2)\n```") == [("run_python", {"code": "print(2)\n"})]


def test_parse_text_tool_calls_none_present():
    assert parse_text_tool_calls("just prose, no tool call here") == []


# --------------------------------------------------------------------------- #
# progressive-disclosure resource loading (harness.skills.read_skill_resource)
# --------------------------------------------------------------------------- #
def _fake_skill(tmp_path):
    """A throwaway skills/ tree with the cda skill, for hermetic resource tests."""
    skill = tmp_path / SERVICE_TO_SKILL["cda"]
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# skill")
    (skill / "references" / "ENDPOINTS.md").write_text("ENDPOINT DOC")
    return HarnessConfig(model="claude-sonnet-4-6", skills_dir=tmp_path)


def test_read_skill_resource_happy(tmp_path):
    step = read_skill_resource("cda", "references/ENDPOINTS.md", _fake_skill(tmp_path))
    assert step.ok and step.kind == "skill_file"
    assert step.path == "references/ENDPOINTS.md"        # posix relative key
    assert step.content == "ENDPOINT DOC"
    assert step.skill == SERVICE_TO_SKILL["cda"]


def test_read_skill_resource_rejects_traversal(tmp_path):
    cfg = _fake_skill(tmp_path)
    (tmp_path / "secret.txt").write_text("nope")
    step = read_skill_resource("cda", "../secret.txt", cfg)
    assert step.ok is False and "outside" in (step.error or "")


def test_read_skill_resource_missing_lists_available(tmp_path):
    step = read_skill_resource("cda", "references/NOPE.md", _fake_skill(tmp_path))
    assert step.ok is False
    assert "references/ENDPOINTS.md" in (step.error or "")  # recovery hint


def test_read_skill_resource_truncates(tmp_path):
    cfg = _fake_skill(tmp_path)
    big = "x" * (RESOURCE_CHAR_CAP + 500)
    (cfg.skills_dir / SERVICE_TO_SKILL["cda"] / "references" / "BIG.md").write_text(big)
    step = read_skill_resource("cda", "references/BIG.md", cfg)
    assert step.ok and step.truncated and step.n_chars == RESOURCE_CHAR_CAP + 500
    assert "truncated" in step.content


def test_read_skill_resource_rejects_other_skill(tmp_path):
    step = read_skill_resource("cda", "references/ENDPOINTS.md", _fake_skill(tmp_path),
                               skill="genomics-data-commons")
    assert step.ok is False and "bound to skill" in (step.error or "")


def test_read_skill_resource_real_tree_loads():
    # guards that the real cda skill stays readable through the tool
    step = read_skill_resource("cda", "references/DISCOVERY.md")
    assert step.ok and step.content.strip()
