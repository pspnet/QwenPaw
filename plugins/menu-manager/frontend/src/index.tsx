import type * as ReactNS from "react";

const PLUGIN_ID = "menu-manager";

// Immediately hide ACP menu on load
window.QwenPaw.menu?.remove("core.acp");
