"""LLM judge for the *semantic* checks (``behavior`` and ``count_at_least``).

These are not string/number matches: ``behavior`` asserts something about the
*method* the agent used (which endpoint, which filter slot, which
interpretation), decidable from the code/tool trace; ``count_at_least`` asserts
the answer enumerates at least N distinct items. The judge is a strict
Anthropic call returning JSON ``{"pass": bool, "reason": str}``. It is
deliberately conservative: if the evidence isn't present, it fails the check.
"""

from __future__ import annotations

import json
import re

import anthropic

from .config import HarnessConfig
from .parsing import Check, Query

_JUDGE_SYSTEM = (
    "You are a strict, literal grader for an automated test harness. You decide "
    "whether ONE assertion about an AI agent's run is satisfied, using only the "
    "agent's final answer and its code/tool trace as evidence. Be conservative: "
    "if the evidence does not clearly support the assertion, it FAILS. Judge only "
    "the stated assertion — not overall answer quality. Respond with a single "
    'JSON object: {"pass": true|false, "reason": "<= 30 words"}. No other text.'
)

_BEHAVIOR_TMPL = """\
ASSERTION (about the METHOD the agent used):
  {spec}

This is a `behavior` check: decide it from the agent's CODE / TOOL TRACE (the
endpoints called, request bodies, filter slots, fields read, interpretations
made). The final answer is secondary context.

TASK GIVEN TO THE AGENT:
{prompt}

AGENT RUN (final answer + code/tool trace):
{transcript}

Does the agent's run satisfy the assertion? Return the JSON verdict.
"""

_COUNT_TMPL = """\
ASSERTION (about enumeration cardinality):
  {spec}

This is a `count_at_least` check of the form `<name> >= N`. Decide whether the
agent's FINAL ANSWER actually enumerates/returns at least N distinct items of
the named kind (not merely claims a count — the distinct items should be
present, or a count of that many be reported from real data).

TASK GIVEN TO THE AGENT:
{prompt}

AGENT FINAL ANSWER:
{answer}

Does the answer satisfy the assertion? Return the JSON verdict.
"""


class LLMJudge:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.resolved_key())

    def __call__(self, check: Check, query: Query, answer: str, transcript: str):
        if check.type == "behavior":
            content = _BEHAVIOR_TMPL.format(
                spec=check.spec, prompt=query.prompt, transcript=transcript[:18000]
            )
        elif check.type == "count_at_least":
            content = _COUNT_TMPL.format(
                spec=check.spec, prompt=query.prompt, answer=answer[:12000]
            )
        else:  # pragma: no cover - only semantic types reach here
            return None, f"judge does not handle {check.type}"

        resp = self.client.messages.create(
            model=self.config.model,
            max_tokens=300,
            temperature=0.0,
            system=_JUDGE_SYSTEM,
            messages=[{"role": "user", "content": content}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        verdict = _extract_json(text)
        if verdict is None or "pass" not in verdict:
            return None, f"unparseable judge output: {text[:120]!r}"
        return bool(verdict["pass"]), str(verdict.get("reason", ""))[:200]


def _extract_json(text: str):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
