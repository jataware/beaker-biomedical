"""Agent-skill evaluation harness.

Parses the authoritative ``queries_md/*_test.md`` benchmark files, runs each
natural-language prompt through a configurable agent backend (plain Anthropic
API, or the archytas ReAct wrapper) with the matching CRDC skill loaded, and
grades the agent's answer against the machine-gradeable ``Checks`` blocks.
"""

__all__ = ["__version__"]
__version__ = "0.1.0"
