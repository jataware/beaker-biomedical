# SPDX-FileCopyrightText: 2026-present Satchel Baldwin <satchelbaldwin@gmail.com>
#
# SPDX-License-Identifier: MIT
from typing import Dict, Any, Optional, TYPE_CHECKING

from beaker_notebook.lib import BeakerContext
from beaker_notebook.lib.utils import action

from .agent import BeakerBiomedicalAgent

if TYPE_CHECKING:
    from beaker_notebook.kernel import BeakerKernel


class BeakerBiomedicalContext(BeakerContext):
    """
    This is the context class.
    """

    AGENT_CLS = BeakerBiomedicalAgent
    SLUG = "beaker-biomedical"

    compatible_subkernels = ["python3"]

    def __init__(self, beaker_kernel: "BeakerKernel", config: Optional[Dict[str, Any]] = None):
        super().__init__(beaker_kernel, config=config)

    async def setup(self, context_info=None, parent_header=None):
        # Custom setup can be done here
        pass
