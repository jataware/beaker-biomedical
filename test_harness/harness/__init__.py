"""Agent-skill evaluation harness.

Parses the ``tests/<service>/<category>/<test>/`` benchmark corpus, runs each
natural-language prompt through a configurable model (via one unified LiteLLM
ReAct engine, with the matching CRDC skill loaded), and grades the answer
against the machine-gradeable checks in each test's ``eval.yaml``.
"""

__all__ = ["__version__"]
__version__ = "0.1.0"
