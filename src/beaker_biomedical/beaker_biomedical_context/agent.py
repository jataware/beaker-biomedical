# SPDX-FileCopyrightText: 2026-present Satchel Baldwin <satchelbaldwin@gmail.com>
#
# SPDX-License-Identifier: MIT
from typing import TYPE_CHECKING

from archytas.tool_utils import tool
from beaker_notebook.lib import BeakerAgent

if TYPE_CHECKING:
    from beaker_notebook.kernel import BeakerKernel


class BeakerBiomedicalAgent(BeakerAgent):
    """
    You are a biomedical research assistant whose goal is to help users perform biomedical research.

    """
    # The class docstring is provided to the LLM to set the expectations for the agent and how it should


    # async def setup(self, context_info: dict[str, any], )

