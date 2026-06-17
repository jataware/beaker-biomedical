"""Static dashboard builder: report JSON(s) -> one self-contained index.html.

See :mod:`harness.site.build`. The build is a pure function of its inputs (the
report files plus the skills/ and tests/ trees), so it is deterministic and
unit-testable, and reruns cheaply after every harness run.
"""

from .build import build_site

__all__ = ["build_site"]
