# -*- coding: utf-8 -*-
"""Menu Manager Plugin -- Minimal backend, all logic is in frontend."""

import logging

from qwenpaw.plugins.api import PluginApi

logger = logging.getLogger("qwenpaw.menu_manager")


class MenuManagerPlugin:
    """Plugin entry point for menu manager."""

    def register(self, api: PluginApi) -> None:
        logger.info("Menu Manager plugin registered")


plugin = MenuManagerPlugin()
