#!/usr/bin/env python3
"""Convenience entrypoint for the harness CLI.

Equivalent to ``python -m harness.cli``. Run from the ``test_harness`` dir:

    python run.py list
    python run.py run --query gdc:Q1 --backend both
"""

import sys

from harness.cli import main

if __name__ == "__main__":
    sys.exit(main())
