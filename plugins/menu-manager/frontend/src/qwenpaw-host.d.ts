interface QwenPawHost {
  React: typeof import("react");
  antd: typeof import("antd");
  antdIcons: typeof import("@ant-design/icons");
  getApiUrl: (path: string) => string;
  getApiToken: () => string;
}

interface QwenPawMenuItem {
  id: string;
  location?: string;
  parentId?: string;
  label?: string | (() => string);
  icon?: any;
  isGroup?: boolean;
  route?: string;
  order?: number;
}

interface QwenPawMenu {
  add: (pluginId: string, item: QwenPawMenuItem | QwenPawMenuItem[]) => { dispose: () => void };
  replace: (pluginId: string, targetId: string, item: QwenPawMenuItem) => { dispose: () => void };
  remove: (targetId: string) => void;
  snapshot: (location?: string) => QwenPawMenuItem[];
}

interface QwenPawRoute {
  add: (pluginId: string, route: any) => { dispose: () => void };
}

interface Window {
  QwenPaw: {
    host: QwenPawHost;
    menu?: QwenPawMenu;
    route?: QwenPawRoute;
  };
}
