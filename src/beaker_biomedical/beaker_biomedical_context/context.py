# SPDX-FileCopyrightText: 2026-present Satchel Baldwin <satchelbaldwin@gmail.com>
#
# SPDX-License-Identifier: MIT
from typing import Dict, Any, TYPE_CHECKING

from beaker_kernel.lib import BeakerContext
from beaker_kernel.lib.utils import action

from .agent import BeakerBiomedicalAgent

if TYPE_CHECKING:
    from beaker_kernel.kernel import BeakerKernel


class BeakerBiomedicalContext(BeakerContext):
    """
    This is the context class.
    """

    compatible_subkernels = ["python3"]
    SLUG = "beaker-biomedical"

    def __init__(self, beaker_kernel: "BeakerKernel", config: Dict[str, Any]):
        super().__init__(beaker_kernel, BeakerBiomedicalAgent, config)

    async def setup(self, context_info=None, parent_header=None):
        # Custom setup can be done here
        pass
